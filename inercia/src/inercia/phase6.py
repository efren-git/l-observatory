"""Phase 6 — pre-registered core parameter study.

The grid and the split are fixed before the run:

* 12 one-factor-at-a-time variants around the published 74/26, 10%-vol,
  monthly, 1/3/6/12 trend, 2-month carry-lag base;
* selection period 2005-01-01 .. 2018-12-31;
* holdout 2019-01-01 .. the latest date;
* choose the variant with the highest selection-period Sharpe, then report its
  holdout result without changing it;
* DSR with 115 trials (103 prior + 12 here).

This is a retrospective, pre-registered split, not a blind forward test. The
analyst has seen the data; the discipline is that the grid and the selection
rule are fixed before looking at the holdout table.
"""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import OUT
from .data import prices
from .engines import carry_returns, trend_returns
from .stats import bootstrap_sharpe, deflated_sharpe, perf, sharpe_daily

SELECTION = ("2005-01-01", "2018-12-31")
HOLDOUT_START = "2019-01-01"
TRIALS_PRIOR = 103
TRIALS_PHASE6 = 12
TRIALS_ALL = TRIALS_PRIOR + TRIALS_PHASE6

# The pre-registered grid. One factor changes at a time from "base".
VARIANTS = {
    "base": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=2,
                 rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "vol_08": dict(lookbacks=(1, 3, 6, 12), target_vol=0.08, lag=2,
                   rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "vol_12": dict(lookbacks=(1, 3, 6, 12), target_vol=0.12, lag=2,
                   rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "lb_3_6_12": dict(lookbacks=(3, 6, 12), target_vol=0.10, lag=2,
                      rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "lb_1_3_6": dict(lookbacks=(1, 3, 6), target_vol=0.10, lag=2,
                     rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "lb_6_12": dict(lookbacks=(6, 12), target_vol=0.10, lag=2,
                    rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "lag_1": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=1,
                  rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "lag_3": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=3,
                  rebalance="ME", use_xs=True, weights=(0.74, 0.26)),
    "quarterly": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=2,
                      rebalance="QE", use_xs=True, weights=(0.74, 0.26)),
    "no_xs": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=2,
                  rebalance="ME", use_xs=False, weights=(0.74, 0.26)),
    "book_80_20": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=2,
                       rebalance="ME", use_xs=True, weights=(0.80, 0.20)),
    "book_60_40": dict(lookbacks=(1, 3, 6, 12), target_vol=0.10, lag=2,
                       rebalance="ME", use_xs=True, weights=(0.60, 0.40)),
}


def fixed_book(df: pd.DataFrame, weights: tuple[float, float]) -> pd.Series:
    return df["trend"] * weights[0] + df["carry"] * weights[1]


def _slice(s: pd.Series, start: str, end: str) -> pd.Series:
    return s[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]


def run_variant(px: pd.DataFrame, p: dict, cost_bps: float = 5.0) -> pd.Series:
    trend, _ = trend_returns(
        px, use_xs=p["use_xs"], rebalance=p["rebalance"],
        cost_bps=cost_bps, lookbacks=p["lookbacks"], target_vol=p["target_vol"],
    )
    carry, _, _ = carry_returns(
        lag_months=p["lag"], rebalance=p["rebalance"],
        cost_bps=cost_bps, target_vol=p["target_vol"],
    )
    df = pd.DataFrame({"trend": trend, "carry": carry}).dropna()
    return fixed_book(df, p["weights"])


def _stats(book: pd.Series) -> dict:
    return {
        "full": perf(book),
        "selection": perf(_slice(book, *SELECTION)),
        "holdout": perf(_slice(book, HOLDOUT_START, "2100-01-01")),
    }


def _dsr(book: pd.Series, n_trials: int = TRIALS_ALL) -> dict:
    s = book.dropna()
    sr = sharpe_daily(s)
    return deflated_sharpe(
        sr, n_trials, len(s), skew=float(s.skew()), kurt=float(s.kurtosis() + 3)
    )


def cost_stress(px: pd.DataFrame, p: dict) -> dict:
    out = {}
    for bps in (5, 10, 25):
        book = run_variant(px, p, cost_bps=bps)
        out[str(bps)] = {
            "full": perf(book),
            "holdout": perf(_slice(book, HOLDOUT_START, "2100-01-01")),
        }
    return out


def run() -> dict:
    px = prices()
    table = {}
    books = {}
    for name, p in VARIANTS.items():
        book = run_variant(px, p)
        books[name] = book
        table[name] = {
            "params": {
                "lookbacks": list(p["lookbacks"]),
                "target_vol": p["target_vol"],
                "carry_lag_months": p["lag"],
                "rebalance": p["rebalance"],
                "use_xs": p["use_xs"],
                "book_weights": list(p["weights"]),
            },
            **_stats(book),
        }

    # Pre-registered selection rule: highest selection-period Sharpe.
    valid = {k: v for k, v in table.items()
             if v["selection"].get("Sharpe") is not None}
    best_name = max(valid, key=lambda k: valid[k]["selection"]["Sharpe"])
    best = valid[best_name]
    best_book = books[best_name]
    holdout_book = _slice(best_book, HOLDOUT_START, "2100-01-01")

    holdout_rank = sorted(
        [(k, v["holdout"].get("Sharpe", -9)) for k, v in valid.items()],
        key=lambda kv: kv[1], reverse=True,
    )
    rank = next((i + 1 for i, (k, _) in enumerate(holdout_rank) if k == best_name), None)

    out = {
        "selection_rule": "highest Sharpe on 2005-01-01..2018-12-31",
        "selection_period": list(SELECTION),
        "holdout_start": HOLDOUT_START,
        "trials": {"prior": TRIALS_PRIOR, "phase6": TRIALS_PHASE6,
                   "all": TRIALS_ALL},
        "variants": table,
        "best_selection": {
            "name": best_name,
            "params": best["params"],
            "selection": best["selection"],
            "holdout": best["holdout"],
            "full": best["full"],
            "holdout_rank_among_variants": rank,
        },
        "full_dsr": _dsr(best_book),
        "holdout_dsr": _dsr(holdout_book),
        "full_bootstrap": bootstrap_sharpe(best_book, n_boot=2000, block=21),
        "holdout_bootstrap": bootstrap_sharpe(holdout_book, n_boot=2000, block=21),
        "cost_stress_best": cost_stress(px, VARIANTS[best_name]),
        "note": "retrospective, pre-registered split; not a blind forward test. "
                "The grid and selection rule were fixed before the holdout table.",
    }
    with open(OUT / "phase6_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    # Chart: selection vs holdout Sharpe, sorted by selection.
    names = sorted(valid, key=lambda k: valid[k]["selection"]["Sharpe"], reverse=True)
    fig, ax = plt.subplots(figsize=(11, 5))
    x = np.arange(len(names))
    ax.bar(x - 0.2, [valid[k]["selection"]["Sharpe"] for k in names], 0.4,
           label="selection 2005-2018")
    ax.bar(x + 0.2, [valid[k]["holdout"]["Sharpe"] for k in names], 0.4,
           label="holdout 2019+")
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha="right")
    ax.axhline(0, color="grey", lw=0.7)
    ax.set_ylabel("Sharpe")
    ax.set_title("Phase 6 — pre-registered core parameter study")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "13_phase6.png", dpi=110)
    plt.close(fig)
    return out
