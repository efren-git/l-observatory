"""Phase 4 — robustness and out-of-sample checks for the Phase 3 book.

This is not a new strategy. It asks whether the Phase 3 overlay survives:

* contiguous subperiods (pre-specified folds);
* a post-hoc 24-month holdout;
* VRP cost stress at 5/10/25 bps per month;
* combined-book turnover stress at 5/10/25 bps;
* overlay-size sensitivity (20/30/40%);
* a combinatorial block sample-split (path stability, not parameter fitting).

The Phase 3 parameters are fixed. Nothing here is tuned; every table is a
robustness check, and the trial count is reported with the result.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import OUT
from .phase3 import (
    CART_SRC, COST_BPS, _monthly_benchmarks, equal_targets, invvol_targets,
    load_sleeves, rebalanced_returns,
)
from .stats import bootstrap_sharpe, deflated_sharpe, perf_m

FOLDS = [
    ("2009-11", "2013-12"),
    ("2014-01", "2018-12"),
    ("2019-01", "2023-12"),
    ("2024-01", "2026-10"),
]
TRIALS_PRIOR = 26 + 23 + 12  # inercia + cartograf + Phase 3
TRIALS_PHASE4 = 6           # folds, holdout, two cost stresses, sensitivity, CPCV
TRIALS_ALL = TRIALS_PRIOR + TRIALS_PHASE4


def _overlay(book: pd.Series, bench: pd.Series, frac: float,
             cost_bps: float = COST_BPS) -> pd.Series:
    mix = pd.DataFrame({"bench": bench.reindex(book.index),
                        "book": book.reindex(book.index)}).dropna()
    tgt = pd.DataFrame({"bench": 1.0 - frac, "book": frac}, index=mix.index)
    return rebalanced_returns(mix, tgt, cost_bps=cost_bps)


def _books(df: pd.DataFrame, live: pd.DataFrame,
           cost_bps: float = COST_BPS) -> dict[str, pd.Series]:
    out = {
        "equal": rebalanced_returns(df, equal_targets(df, live), cost_bps=cost_bps),
        "invvol": rebalanced_returns(df, invvol_targets(df, live), cost_bps=cost_bps),
    }
    cols3 = [c for c in df.columns if c != "bab"]
    if len(cols3) == df.shape[1] - 1:
        out["equal_no_bab"] = rebalanced_returns(
            df[cols3], equal_targets(df[cols3], live[cols3]), cost_bps=cost_bps
        )
        out["invvol_no_bab"] = rebalanced_returns(
            df[cols3], invvol_targets(df[cols3], live[cols3]), cost_bps=cost_bps
        )
    return out


def _slice(s: pd.Series, start: str, end: str) -> pd.Series:
    return s[(s.index >= pd.Period(start, "M")) & (s.index <= pd.Period(end, "M"))]


def fold_table(series: dict[str, pd.Series], rf: pd.Series) -> dict:
    out = {}
    for name, s in series.items():
        out[name] = {}
        for a, b in FOLDS:
            part = _slice(s, a, b)
            out[name][f"{a}..{b}"] = perf_m(part, rf_monthly=rf)
    return out


def rolling_sharpe(s: pd.Series, window: int = 36) -> dict:
    s = s.dropna()
    mu = s.rolling(window).mean()
    sd = s.rolling(window).std()
    rs = (mu / sd * np.sqrt(12.0)).dropna()
    if not len(rs):
        return {}
    return {
        "window": window,
        "min": round(float(rs.min()), 3),
        "median": round(float(rs.median()), 3),
        "max": round(float(rs.max()), 3),
        "latest": round(float(rs.iloc[-1]), 3),
        "pct_negative": round(float((rs < 0).mean()), 3),
    }


def block_cpcv(s: pd.Series, n_blocks: int = 6, k: int = 2,
               purge: int = 1) -> dict:
    """Combinatorial block sample-split.

    The Phase 3 strategy has no fitted parameters, so this is a path-stability
    check, not a parameter-selection procedure. Each split holds out k blocks,
    purges one month at each boundary, concatenates the held-out months and
    computes the Sharpe. Report the distribution, not a single number.
    """
    s = s.dropna()
    n = len(s)
    if n < n_blocks * 6:
        return {}
    edges = np.linspace(0, n, n_blocks + 1, dtype=int)
    blocks = [s.iloc[edges[i]:edges[i + 1]] for i in range(n_blocks)]
    sharpes = []
    for combo in itertools.combinations(range(n_blocks), k):
        parts = []
        for idx in combo:
            b = blocks[idx]
            if purge and len(b) > 2 * purge:
                b = b.iloc[purge:len(b) - purge]
            parts.append(b)
        test = pd.concat(parts).dropna()
        if len(test) >= 12 and test.std() > 0:
            sharpes.append(float(test.mean() / test.std() * np.sqrt(12.0)))
    if not sharpes:
        return {}
    a = np.asarray(sharpes)
    return {
        "n_splits": int(len(a)),
        "n_blocks": n_blocks,
        "k_test": k,
        "purge": purge,
        "mean": round(float(a.mean()), 3),
        "median": round(float(np.median(a)), 3),
        "min": round(float(a.min()), 3),
        "max": round(float(a.max()), 3),
        "pct_positive": round(float((a > 0).mean()), 3),
    }


def _on_b_mask() -> pd.Series:
    """Months where the gated VRP sleeve was on (scale > 0 and contango)."""
    if str(CART_SRC) not in sys.path:
        sys.path.insert(0, str(CART_SRC))
    from cartograf.sleeves import vrp_monthly
    v = vrp_monthly()
    on = (v["scale"] > 0) & v["contango"]
    on.index = on.index.to_period("M")
    return on


def vrp_cost_stress(df: pd.DataFrame, live: pd.DataFrame, bench: pd.Series,
                    rf: pd.Series) -> dict:
    on = _on_b_mask()
    out = {}
    for bps in (5, 10, 25):
        df2 = df.copy()
        extra = (bps - 5) / 1e4 * on.reindex(df2.index).fillna(False).astype(float)
        df2["vrp"] = df2["vrp"] - extra
        books = _books(df2, live)
        out[str(bps)] = {
            "vrp_sleeve": perf_m(df2["vrp"]),
            "equal_30": perf_m(_overlay(books["equal"], bench, 0.3), rf_monthly=rf),
            "invvol_30": perf_m(_overlay(books["invvol"], bench, 0.3), rf_monthly=rf),
        }
    return out


def book_cost_stress(df: pd.DataFrame, live: pd.DataFrame, bench: pd.Series,
                     rf: pd.Series) -> dict:
    out = {}
    for bps in (5, 10, 25):
        books = _books(df, live, cost_bps=bps)
        out[str(bps)] = {
            "equal_30": perf_m(_overlay(books["equal"], bench, 0.3, cost_bps=bps),
                               rf_monthly=rf),
            "invvol_30": perf_m(_overlay(books["invvol"], bench, 0.3, cost_bps=bps),
                                rf_monthly=rf),
        }
    return out


def overlay_sensitivity(df: pd.DataFrame, live: pd.DataFrame,
                        bench: pd.Series, rf: pd.Series) -> dict:
    books = _books(df, live)
    out = {}
    for name in ("equal", "invvol", "equal_no_bab", "invvol_no_bab"):
        if name not in books:
            continue
        for frac in (0.2, 0.3, 0.4):
            out[f"{name}_{int(frac * 100)}"] = perf_m(
                _overlay(books[name], bench, frac), rf_monthly=rf
            )
    return out


def holdout(df: pd.DataFrame, live: pd.DataFrame, bench: pd.Series,
            rf: pd.Series, start: str = "2024-11") -> dict:
    books = _books(df, live)
    out = {}
    for name in ("equal", "invvol"):
        s = _slice(_overlay(books[name], bench, 0.3), start, "2026-10")
        out[f"{name}_30"] = perf_m(s, rf_monthly=rf)
    return out


def run() -> dict:
    spy, bench, rf = _monthly_benchmarks()
    df, live, label = load_sleeves("B")
    books = _books(df, live)
    overlays = {
        "equal_30": _overlay(books["equal"], bench, 0.3),
        "invvol_30": _overlay(books["invvol"], bench, 0.3),
        "equal_no_bab_30": _overlay(books["equal_no_bab"], bench, 0.3),
        "invvol_no_bab_30": _overlay(books["invvol_no_bab"], bench, 0.3),
    }
    claims = {}
    for name, s in overlays.items():
        s = s.dropna()
        sr = float(s.mean() / s.std()) if s.std() > 0 else 0.0
        claims[name] = {
            "stats": perf_m(s, rf_monthly=rf),
            "bootstrap": bootstrap_sharpe(s, n_boot=2000, block=6, periods=12),
            "block_cpcv": block_cpcv(s),
            "rolling_sharpe_36m": rolling_sharpe(s),
        }
    out = {
        "window": [str(df.index[0]), str(df.index[-1])],
        "label": label,
        "trials": {"prior": TRIALS_PRIOR, "phase4": TRIALS_PHASE4,
                   "all": TRIALS_ALL},
        "folds": fold_table(overlays, rf),
        "holdout_2024_11_plus": holdout(df, live, bench, rf),
        "vrp_cost_stress": vrp_cost_stress(df, live, bench, rf),
        "book_cost_stress": book_cost_stress(df, live, bench, rf),
        "overlay_sensitivity": overlay_sensitivity(df, live, bench, rf),
        "claims": claims,
        "note": "Phase 4 holds the Phase 3 parameters fixed; it is a robustness "
                "check, not a new search. The holdout is post-hoc, not blind.",
    }
    with open(OUT / "phase4_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    # Chart: rolling 36-month Sharpe of the two pre-specified overlays.
    fig, ax = plt.subplots(figsize=(11, 5))
    for name in ("equal_30", "invvol_30"):
        s = overlays[name].dropna()
        rs = (s.rolling(36).mean() / s.rolling(36).std() * np.sqrt(12.0)).dropna()
        ax.plot(rs.index.to_timestamp(), rs.values, label=name, lw=1.7)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_title("Phase 4 — rolling 36-month Sharpe, Window B")
    ax.set_ylabel("Sharpe")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "11_phase4.png", dpi=110)
    plt.close(fig)
    return out
