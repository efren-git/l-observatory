"""Phase 5 — a pairs/stat-arb sleeve and a paper-trading snapshot.

The question is whether a simple pairs strategy can improve or hedge the Phase 3
book. KO/PEP is the user's example; V/MA is the only pair in a fixed industry
list that passes a full-sample cointegration screen. Neither result is a
validated alpha claim.

The paper-trading snapshot is a ledger, not an order router. It records the
model's current target (Phase 3 allocation + pair signals) so forward
performance can be compared with the backtest. No live orders are placed.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import OUT
from .phase3 import (
    _monthly_benchmarks, equal_targets, load_sleeves, rebalanced_returns,
)
from .pairs import current_signal, pair_backtest, summary
from .stats import bootstrap_sharpe, deflated_sharpe, perf_m

PAIRS = [("KO", "PEP"), ("XOM", "CVX"), ("V", "MA"), ("GS", "MS"),
         ("UPS", "FDX"), ("HD", "LOW"), ("PG", "CL"), ("JNJ", "PFE")]
TRIALS_PRIOR = 67
TRIALS_PAIR_SCREEN = len(PAIRS)
TRIALS_GRID = 24
TRIALS_HEDGE = 4
TRIALS_ALL = TRIALS_PRIOR + TRIALS_PAIR_SCREEN + TRIALS_GRID + TRIALS_HEDGE


def pair_screen() -> dict:
    out = {}
    for a, b in PAIRS:
        s = summary(a, b)
        out[f"{a}/{b}"] = {
            "stats": s["stats"],
            "bootstrap": s["bootstrap"],
            "cointegration": s["cointegration"],
            "half_life_days": s["half_life_days"],
            "diagnostics": s["diagnostics"],
        }
    return out


def parameter_grid() -> dict:
    out = {}
    for a, b in (("V", "MA"), ("KO", "PEP")):
        rows = []
        for entry in (1.5, 2.0, 2.5):
            for zw in (60, 120):
                for ex in (0.5, 1.0):
                    net, diag, _ = pair_backtest(a, b, entry=entry,
                                                  z_window=zw, exit=ex)
                    st = perf_m((1 + net).resample("ME").prod() - 1)
                    rows.append({
                        "entry": entry, "z_window": zw, "exit": ex,
                        "sharpe": st.get("Sharpe"), "cagr": st.get("CAGR"),
                        "maxdd": st.get("MaxDD"),
                        "turnover": diag.get("annual_turnover"),
                    })
        rows = sorted(rows, key=lambda r: (r["sharpe"] is None, -(r["sharpe"] or -9)))
        out[f"{a}/{b}"] = {"best": rows[0], "worst": rows[-1], "all": rows}
    return out


def _phase3_overlay():
    spy, bench, rf = _monthly_benchmarks()
    df, live, label = load_sleeves("B")
    book = rebalanced_returns(df, equal_targets(df, live))
    mix = pd.DataFrame({"bench": bench.reindex(book.index),
                        "book": book.reindex(book.index)}).dropna()
    tgt = pd.DataFrame({"bench": 0.7, "book": 0.3}, index=mix.index)
    return rebalanced_returns(mix, tgt), bench, rf


def _pair_monthly(a, b):
    net, diag, _ = pair_backtest(a, b)
    m = (1 + net).resample("ME").prod() - 1
    m.index = m.index.to_period("M")
    return m, diag


def hedge_blend() -> dict:
    overlay, bench, rf = _phase3_overlay()
    out = {}
    for a, b in (("V", "MA"), ("KO", "PEP")):
        pm, diag = _pair_monthly(a, b)
        common = overlay.index.intersection(pm.index)
        o, p = overlay.reindex(common), pm.reindex(common)
        out[f"{a}/{b}"] = {
            "pair_monthly": perf_m(p),
            "corr_to_overlay": round(float(o.corr(p)), 3),
            "pair_diagnostics": diag,
            "blends": {},
        }
        for w in (0.1, 0.2):
            mix = pd.DataFrame({"overlay": o, "pair": p})
            tgt = pd.DataFrame({"overlay": 1 - w, "pair": w}, index=common)
            blended = rebalanced_returns(mix, tgt)
            out[f"{a}/{b}"]["blends"][str(w)] = perf_m(blended, rf_monthly=rf)
    out["phase3_overlay"] = perf_m(overlay, rf_monthly=rf)
    return out


def paper_trade_snapshot() -> dict:
    signals = {
        "V/MA": current_signal("V", "MA"),
        "KO/PEP": current_signal("KO", "PEP"),
    }
    as_of = max(s["as_of"] for s in signals.values())
    snapshot = {
        "as_of": as_of,
        "mode": "paper only; no orders",
        "phase3_overlay": {
            "allocation": {"60/40": 0.7, "phase3_book": 0.3},
            "book_weights": {"trend": 0.25, "carry": 0.25,
                             "bab": 0.25, "vrp_gated": 0.25},
            "note": "sleeve-level target; rebalance monthly; BAB is a drag",
        },
        "pair_signals": signals,
        "note": "KO/PEP is the example pair and is not recommended; V/MA is "
                "the only pair in the fixed screen with a cointegrated residual.",
    }
    with open(OUT / "paper_trade.json", "w") as f:
        json.dump(snapshot, f, indent=2)

    log = OUT / "paper_trade_log.csv"
    rows = [{
        "date": as_of, "strategy": "phase3_overlay",
        "target": "70% 60/40 + 30% book",
        "detail": "equal weight trend/carry/BAB/gated VRP",
    }]
    for name, s in signals.items():
        rows.append({
            "date": as_of, "strategy": name,
            "target": s["action"],
            "detail": f"beta={s['beta']} z={s['z']} pos={s['position']}",
        })
    new = pd.DataFrame(rows)
    if log.exists():
        old = pd.read_csv(log)
        new = pd.concat([old, new], ignore_index=True)
        new = new.drop_duplicates(["date", "strategy"], keep="last")
    new.to_csv(log, index=False)
    return snapshot


def run() -> dict:
    overlay, bench, rf = _phase3_overlay()
    out = {
        "trials": {"prior": TRIALS_PRIOR, "pair_screen": TRIALS_PAIR_SCREEN,
                   "grid": TRIALS_GRID, "hedge": TRIALS_HEDGE,
                   "all": TRIALS_ALL},
        "pair_screen": pair_screen(),
        "parameter_grid": parameter_grid(),
        "hedge": hedge_blend(),
        "paper_trade": paper_trade_snapshot(),
        "note": "Pairs are a research sleeve. KO/PEP fails; V/MA is cointegrated "
                "but weak. The hedge blend is a preference trade, not alpha.",
    }
    with open(OUT / "phase5_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    # Chart: Phase 3 overlay and the V/MA hedge blends.
    fig, ax = plt.subplots(figsize=(11, 5.5))
    ax.plot(overlay.index.to_timestamp(), (1 + overlay.fillna(0)).cumprod(),
            label="Phase 3 overlay", lw=2.0)
    for w in (0.1, 0.2):
        pm, _ = _pair_monthly("V", "MA")
        common = overlay.index.intersection(pm.index)
        mix = pd.DataFrame({"overlay": overlay.reindex(common),
                            "pair": pm.reindex(common)})
        tgt = pd.DataFrame({"overlay": 1 - w, "pair": w}, index=common)
        b = rebalanced_returns(mix, tgt)
        ax.plot(b.index.to_timestamp(), (1 + b.fillna(0)).cumprod(),
                label=f"+{int(w*100)}% V/MA", lw=1.5)
    ax.set_yscale("log")
    ax.set_title("Phase 5 — Phase 3 overlay vs V/MA hedge blends")
    ax.set_ylabel("growth of 1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "12_phase5.png", dpi=110)
    plt.close(fig)
    return out
