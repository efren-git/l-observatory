"""Phase 7 — tail hedges on the Phase 3 overlay.

Pre-registered before the run (2026-10-20). The question is narrow: can a
mechanical tail hedge improve the 60/40 + 30% Phase 3 overlay, or is it
insurance that costs more than it is worth?

Pre-registration
----------------

* Base: 60/40 (SPY/IEF, monthly, net) + 30% equal-weight Phase 3 book
  (trend, carry, BAB, gated VRP), Window B starts 2009-11 because VIX3M does.
* Four hedges, fixed sizes, no grid, no conditional timing:
    1. short 5% SPY notional (cash collateral earns T-bills);
    2. short 10% SPY notional;
    3. long 5% VIX spot, funded at T-bills (diagnostic: not investable, no roll);
    4. short 5% SVXY, funded, 50 bps/yr borrow (investable long-vol proxy,
       starts 2011-11).
* Selection: 2005-01-01 .. 2018-12-31 as pre-registered. The overlay itself
  starts 2009-11 and the SVXY hedge 2011-11; the effective windows are reported
  per variant.
* Holdout: 2019-01-01 .. latest.
* Costs: 5 / 10 / 25 bps on all turnover, applied to the base overlay and the
  hedge together.
* Success rule: the hedge must improve *both* holdout Sharpe and holdout max
  drawdown, and must not turn negative at 25 bps. A drawdown improvement paid
  for with Sharpe is a preference trade, not an improvement.
* Trials: 4 new hedges on top of the 115 already registered -> DSR at 119.
  The final-variant DSR uses 2 (the two short-SPY sizes).

Mechanics
---------

A hedge is a signed notional on top of the base overlay. The base stays at
100%; the hedge is funded at the T-bill rate (a short earns it, a long pays
it). The notional drifts with the hedged asset during the month and is
rebalanced back to the fixed size at each month-end; the rebalancing trade pays
the cost. No signal, no VIX trigger, no option strike: the grid is deliberately
not allowed to grow after seeing the answer.
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
from .stats import bootstrap_sharpe, deflated_sharpe, perf_m

COST_BPS = 5.0
HEDGE_FRACTIONS = (0.05, 0.10)
BORROW_BPS = 50.0          # annual borrow on the short SVXY leg

SELECTION = ("2005-01-01", "2018-12-31")
HOLDOUT_START = "2019-01-01"

TRIALS_PRIOR = 115
TRIALS_PHASE7 = 4
TRIALS_ALL = TRIALS_PRIOR + TRIALS_PHASE7
TRIALS_FINAL = 2

# Fixed before the run: name -> (kind, size)
VARIANTS = {
    "short_spy_5": ("short_spy", 0.05),
    "short_spy_10": ("short_spy", 0.10),
    "long_vol_vix_5": ("long_vix", 0.05),
    "short_svxy_5": ("short_svxy", 0.05),
}

CRISIS = {
    "2018Q4": ("2018-10", "2018-12"),
    "COVID_2020": ("2020-02", "2020-04"),
    "2022": ("2022-01", "2022-12"),
    "2023_rebound": ("2023-01", "2023-12"),
}


def _period_index(index) -> pd.PeriodIndex:
    return pd.PeriodIndex(index, freq="M")


def _to_monthly(daily: pd.Series) -> pd.Series:
    s = daily.dropna()
    m = s.resample("ME").last()
    m.index = m.index.to_period("M")
    return m


def _cartograf_raw(name: str) -> pd.DataFrame:
    base = Path(__file__).resolve().parents[3] / "cartograf" / "data" / "raw"
    d = pd.read_csv(base / name)
    date_col = "Date" if "Date" in d.columns else d.columns[0]
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    return d.dropna(subset=[date_col]).set_index(date_col).sort_index()


def vix_monthly() -> pd.Series:
    """Monthly return of the VIX spot index (not an investable total return)."""
    d = _cartograf_raw("cboe_vix_term.csv")
    v = pd.to_numeric(d["vix"], errors="coerce").dropna()
    m = _to_monthly(v)
    return m.pct_change()


def svxy_monthly() -> pd.Series:
    """Monthly return of SVXY, the short-vol ETF (long-vol hedge is short it)."""
    d = _cartograf_raw("prices.csv")
    s = pd.to_numeric(d["SVXY"], errors="coerce").dropna()
    m = _to_monthly(s)
    return m.pct_change()


def build_overlay(cost_bps: float = COST_BPS):
    """The published Phase 3 claim, rebuilt at a given cost level."""
    spy, bench, rf = _monthly_benchmarks()
    df, live, _ = load_sleeves("B", cost_bps=cost_bps)
    book = rebalanced_returns(df, equal_targets(df, live), cost_bps=cost_bps)
    mix = pd.DataFrame({"bench": bench.reindex(book.index),
                        "book": book.reindex(book.index)}).dropna()
    tgt = pd.DataFrame({"bench": 0.7, "book": 0.3}, index=mix.index)
    overlay = rebalanced_returns(mix, tgt, cost_bps=cost_bps)
    return overlay, spy.reindex(overlay.index), rf.reindex(overlay.index), bench


def hedge_series(base: pd.Series, asset: pd.Series, rf: pd.Series,
                 size: float, cost_bps: float, sign: int,
                 borrow_bps: float = 0.0, fund: bool = True) -> pd.Series:
    """Add a fixed-size hedge to base.

    sign = -1 shorts the asset, +1 goes long. fund=True pays/receives T-bills:
    a short earns the rate on its collateral, a long pays it. The signed notional
    drifts with the asset over the month and is reset at the next month-end; the
    reset pays cost_bps on the traded notional.
    """
    idx = base.index.intersection(asset.dropna().index).intersection(rf.index)
    b = base.reindex(idx).astype(float)
    a = asset.reindex(idx).astype(float)
    f = rf.reindex(idx).astype(float)
    prev = 0.0
    out = []
    for t in idx:
        trade = abs(sign * size - prev)
        cash = 0.0
        if fund:
            cash = size * f.loc[t] if sign < 0 else -size * f.loc[t]
        r = (float(b.loc[t]) + sign * size * float(a.loc[t]) + cash
             - trade * cost_bps / 1e4 - size * borrow_bps / 1e4 / 12.0)
        out.append(r)
        prev = sign * size * (1.0 + float(a.loc[t])) / (1.0 + r)
    return pd.Series(out, index=idx)


def variant_series(name: str, overlay: pd.Series, spy: pd.Series, rf: pd.Series,
                   cost_bps: float = COST_BPS) -> pd.Series:
    kind, size = VARIANTS[name]
    if kind == "short_spy":
        return hedge_series(overlay, spy, rf, size, cost_bps, sign=-1)
    if kind == "long_vix":
        return hedge_series(overlay, vix_monthly(), rf, size, cost_bps, sign=+1)
    if kind == "short_svxy":
        return hedge_series(overlay, svxy_monthly(), rf, size, cost_bps,
                            sign=-1, borrow_bps=BORROW_BPS)
    raise ValueError(name)


def _slice(s: pd.Series, start: str, end: str = "2100-01-01") -> pd.Series:
    lo, hi = pd.Period(start, "M"), pd.Period(end, "M")
    return s[(s.index >= lo) & (s.index <= hi)]


def _window_return(s: pd.Series, start: str, end: str) -> float | None:
    x = _slice(s, start, end)
    if not len(x):
        return None
    return round(float((1.0 + x).prod() - 1.0), 4)


def _stats(s: pd.Series) -> dict:
    return {
        "start": str(s.index.min()),
        "end": str(s.index.max()),
        "full": perf_m(s),
        "selection": perf_m(_slice(s, *SELECTION)),
        "holdout": perf_m(_slice(s, HOLDOUT_START)),
        "crisis": {k: _window_return(s, *v) for k, v in CRISIS.items()},
    }


def _dsr(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 24:
        return {}
    sr = float(s.mean() / s.std())
    return deflated_sharpe(
        sr, TRIALS_ALL, len(s), skew=float(s.skew()), kurt=float(s.kurtosis() + 3)
    )


def _dsr_final(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) < 24:
        return {}
    sr = float(s.mean() / s.std())
    return deflated_sharpe(
        sr, TRIALS_FINAL, len(s), skew=float(s.skew()), kurt=float(s.kurtosis() + 3)
    )


def _spy_beta(s: pd.Series, spy: pd.Series) -> float | None:
    x = pd.concat([s, spy], axis=1).dropna()
    if len(x) < 24 or x.iloc[:, 1].var() == 0:
        return None
    return round(float(x.iloc[:, 0].cov(x.iloc[:, 1]) / x.iloc[:, 1].var()), 3)


def marginal(base: pd.Series, hedged: pd.Series) -> dict:
    """The hedge's own return stream: hedged minus unhedged.

    This is the honest test of a hedge. The hedged portfolio's Sharpe is mostly
    the base's Sharpe; only the difference series isolates what the hedge adds
    and what it costs.
    """
    d = (hedged - base.reindex(hedged.index)).dropna()
    if len(d) < 24 or d.std() == 0:
        return {}
    sr_m = float(d.mean() / d.std())
    return {
        "mean_monthly": round(float(d.mean()), 5),
        "vol_monthly": round(float(d.std()), 5),
        "sharpe_annual": round(sr_m * np.sqrt(12.0), 3),
        "t_stat": round(float(d.mean() / d.std() * np.sqrt(len(d))), 2),
        "hit_rate": round(float((d > 0).mean()), 3),
        "worst_month": round(float(d.min()), 4),
        "best_month": round(float(d.max()), 4),
        "dsr_all_trials": deflated_sharpe(
            sr_m, TRIALS_ALL, len(d), skew=float(d.skew()),
            kurt=float(d.kurtosis() + 3),
        ),
        "bootstrap": bootstrap_sharpe(d, n_boot=2000, block=6, periods=12),
    }


def vol_matched(base_perf: dict, hedge_perf: dict) -> dict:
    """Compare the drawdown with a same-vol unhedged portfolio.

    If a hedge only de-risks, its max drawdown should shrink roughly in
    proportion to its volatility. A drawdown better than proportional is
    convexity; worse is a hedge that costs more than the exposure it removes.
    """
    if not base_perf or not hedge_perf or base_perf["Vol"] == 0:
        return {}
    ratio = hedge_perf["Vol"] / base_perf["Vol"]
    expected = base_perf["MaxDD"] * ratio
    return {
        "vol_ratio": round(float(ratio), 3),
        "proportional_maxdd": round(float(expected), 4),
        "actual_maxdd": round(float(hedge_perf["MaxDD"]), 4),
        "convexity": round(float(hedge_perf["MaxDD"] - expected), 4),
    }


def run() -> dict:
    overlay, spy, rf, bench = build_overlay(COST_BPS)
    series = {"base": overlay}
    for name in VARIANTS:
        series[name] = variant_series(name, overlay, spy, rf, COST_BPS)

    base_stats = _stats(overlay)
    out = {
        "pre_registration": {
            "base": "60/40 + 30% Phase 3 equal-weight overlay (Window B, gated VRP)",
            "variants": {k: {"kind": v[0], "size": v[1]} for k, v in VARIANTS.items()},
            "selection": list(SELECTION),
            "selection_effective": "2009-11+ for the overlay; 2011-11+ for short SVXY",
            "holdout_start": HOLDOUT_START,
            "success_rule": "holdout improvement in both Sharpe and MaxDD, and no "
                            "negative holdout Sharpe at 25 bps",
            "frequency": "monthly",
            "cost_bps": [5, 10, 25],
            "note": "fixed sizes, no grid, no conditional VIX trigger. "
                    "Every variant is a trial.",
        },
        "trials": {"prior": TRIALS_PRIOR, "phase7": TRIALS_PHASE7,
                   "all": TRIALS_ALL, "final": TRIALS_FINAL},
        "base": base_stats,
        "hedges": {},
        "cost_stress": {},
        "note": "The VIX variant is a diagnostic, not an investable product: it "
                "uses spot VIX, ignores futures roll (usually negative), and is "
                "funded at T-bills. The SVXY variant is the investable proxy but "
                "starts in 2011-11 and carries borrow and path-dependence.",
    }

    base_perf = base_stats["full"]
    for name, s in series.items():
        st = _stats(s)
        if name == "base":
            continue
        hold_b = base_stats["holdout"]
        hold_h = st["holdout"]
        out["hedges"][name] = {
            "params": {"kind": VARIANTS[name][0], "size": VARIANTS[name][1]},
            "stats": st,
            "dsr_all_trials": _dsr(s),
            "dsr_final_variants": _dsr_final(s),
            "bootstrap_full": bootstrap_sharpe(s, n_boot=2000, block=6, periods=12),
            "marginal": marginal(overlay, s),
            "vol_matched": vol_matched(base_perf, st["full"]),
            "beta_to_spy": _spy_beta(s, spy),
            "versus_base": {
                "sharpe_full": round(st["full"]["Sharpe"] - base_perf["Sharpe"], 3),
                "maxdd_full": round(st["full"]["MaxDD"] - base_perf["MaxDD"], 4),
                "cagr_full": round(st["full"]["CAGR"] - base_perf["CAGR"], 4),
                "sharpe_holdout": round(hold_h["Sharpe"] - hold_b["Sharpe"], 3),
                "maxdd_holdout": round(hold_h["MaxDD"] - hold_b["MaxDD"], 4),
                "cagr_holdout": round(hold_h["CAGR"] - hold_b["CAGR"], 4),
            },
        }

    # Cost stress: rebuild the whole path (overlay + hedge) at each cost level.
    for bps in (5, 10, 25):
        o, sp, r, _ = build_overlay(bps)
        row = {"base": {
            "selection": perf_m(_slice(o, *SELECTION)),
            "holdout": perf_m(_slice(o, HOLDOUT_START)),
        }}
        for name in VARIANTS:
            h = variant_series(name, o, sp, r, float(bps))
            row[name] = {
                "selection": perf_m(_slice(h, *SELECTION)),
                "holdout": perf_m(_slice(h, HOLDOUT_START)),
            }
        out["cost_stress"][str(bps)] = row

    with open(OUT / "phase7_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    # Chart: growth and drawdown, full window.
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 8), sharex=True)
    for name, s in series.items():
        eq = (1 + s.fillna(0)).cumprod()
        ax1.plot(s.index.to_timestamp(), eq, label=name, lw=1.6)
        ax2.plot(s.index.to_timestamp(), eq / eq.cummax() - 1.0, lw=1.3)
    ax1.set_yscale("log")
    ax1.set_title("Phase 7 — tail hedges on the Phase 3 overlay (net, 5 bps)")
    ax1.set_ylabel("growth of 1")
    ax1.legend(fontsize=8)
    ax2.set_ylabel("drawdown")
    ax2.axhline(0, color="grey", lw=0.7)
    fig.tight_layout()
    fig.savefig(OUT / "14_phase7.png", dpi=110)
    plt.close(fig)
    return out
