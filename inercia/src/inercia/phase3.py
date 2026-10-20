"""Phase 3 — one combined book.

Pre-specified in PLAN.md (2026-10-19):

* trend and carry come from inercia (the longer, single implementation);
* cartograf contributes BAB and the gated VRP only;
* monthly frequency, because the proper VRP is monthly;
* Window A: 2008-01+ with the legacy SVXY proxy, labelled;
* Window B: 2009-11+ with the gated VRP (VIX3M starts 2009-09);
* equal-weight and inverse-vol variants, plus fixed 20%/30% overlays;
* 5 bps per unit of combined-book turnover; a sleeve that is not live is flat,
  not backfilled;
* every variant is a trial; report DSR with all trials and final variants.

The module imports cartograf's sleeve implementation directly. Both projects
live in the same repository; adding cartograf/src to sys.path is enough.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import OUT
from .data import prices, risk_free_daily
from .engines import carry_returns, trend_returns
from .stats import bootstrap_sharpe, deflated_sharpe, perf_m

CART_SRC = Path(__file__).resolve().parents[3] / "cartograf" / "src"


def _cartograf_sleeves():
    """Import cartograf lazily so the Phase 3 helpers are testable alone."""
    if str(CART_SRC) not in sys.path:
        sys.path.insert(0, str(CART_SRC))
    from cartograf.sleeves import bab, universe_setup, vrp_monthly
    return bab, universe_setup, vrp_monthly

COST_BPS = 5.0
LOOKBACK = 12          # monthly analogue of the 63-day inverse-vol window
MIN_OBS = 6
TRIALS_PRIOR = 26 + 23  # inercia + cartograf registries
TRIALS_PHASE3 = 12      # 4 books (with/without BAB) + 8 overlays
TRIALS_ALL = TRIALS_PRIOR + TRIALS_PHASE3
TRIALS_FINAL = 2        # the two 30% overlays that are the published claim


def _to_monthly(daily: pd.Series) -> pd.Series:
    m = (1.0 + pd.Series(daily).fillna(0.0)).resample("ME").prod() - 1.0
    m.index = m.index.to_period("M")
    return m


def _monthly_benchmarks():
    px = prices()
    R = px.pct_change()
    spy = (1.0 + R["SPY"].fillna(0.0)).resample("ME").prod() - 1.0
    ief = (1.0 + R["IEF"].fillna(0.0)).resample("ME").prod() - 1.0
    bench = 0.6 * spy + 0.4 * ief
    rf = (1.0 + risk_free_daily(px.index)).resample("ME").prod() - 1.0
    for s in (spy, bench, rf):
        s.index = s.index.to_period("M")
    return spy, bench, rf


def load_sleeves(window: str, cost_bps: float = COST_BPS):
    """Return (monthly returns, live mask, label) for Window A or B.

    cost_bps only scales the inercia trend/carry sleeves; the cartograf BAB and
    VRP sleeves keep their own published cost assumptions.
    """
    px = prices()
    trend_d, _ = trend_returns(px, cost_bps=cost_bps)
    carry_d, _, _ = carry_returns(cost_bps=cost_bps)
    trend_m = _to_monthly(trend_d)
    carry_m = _to_monthly(carry_d)

    bab_fn, universe_setup, vrp_monthly = _cartograf_sleeves()
    cpx, R, tradable, me, groups = universe_setup()
    bab_d, _ = bab_fn(R, tradable, me, groups)
    bab_m = _to_monthly(bab_d)

    v = vrp_monthly()
    vrp_b = v["B"].copy()
    vrp_c = v["C"].copy()
    vrp_b.index = vrp_b.index.to_period("M")
    vrp_c.index = vrp_c.index.to_period("M")

    if window == "A":
        cols = ["trend", "carry", "bab", "vrp"]
        df = pd.concat([
            trend_m.rename("trend"), carry_m.rename("carry"),
            bab_m.rename("bab"), vrp_c.rename("vrp"),
        ], axis=1)
        df = df[df.index >= pd.Period("2008-01", "M")]
        live = df.notna()
        live["vrp"] = vrp_c.notna().reindex(df.index).fillna(False)
        df["vrp"] = df["vrp"].fillna(0.0)
        df = df.dropna(subset=["trend", "carry", "bab"])
        live = live.reindex(df.index).fillna(False)
        return df, live, "A: 2008-01+, legacy SVXY proxy"

    cols = ["trend", "carry", "bab", "vrp"]
    df = pd.concat([
        trend_m.rename("trend"), carry_m.rename("carry"),
        bab_m.rename("bab"), vrp_b.rename("vrp"),
    ], axis=1)
    df = df.dropna()
    df = df[df.index >= pd.Period("2009-11", "M")]
    live = pd.DataFrame(True, index=df.index, columns=cols)
    return df, live, "B: 2009-11+, gated VRP"


def equal_targets(df: pd.DataFrame, live: pd.DataFrame) -> pd.DataFrame:
    """Equal capital per sleeve, with not-live sleeves held in cash.

    Do not renormalise across the live subset: that would backfill a sleeve that
    did not exist yet. The rest of the book is cash until the sleeve is live.
    The live mask is lagged one month: a price at month-end t is not available
    when month t's return is earned.
    """
    n = df.shape[1]
    return live.shift(1).fillna(False).astype(float) / n


def invvol_targets(df: pd.DataFrame, live: pd.DataFrame,
                   lookback: int = LOOKBACK, min_obs: int = MIN_OBS) -> pd.DataFrame:
    vol = df.where(live).rolling(lookback, min_periods=min_obs).std()
    iv = (1.0 / vol.replace(0.0, np.nan)).where(live, 0.0)
    total = iv.sum(axis=1)
    # Scale by the live fraction, so a missing sleeve leaves cash rather than
    # increasing the other sleeves' weights.
    frac = live.sum(axis=1) / float(df.shape[1])
    w = iv.div(total.replace(0.0, np.nan), axis=0).mul(frac, axis=0)
    # The vol estimate at t uses month t's return; the target must be known
    # before that return is earned.
    return w.shift(1).fillna(0.0)


def rebalanced_returns(returns: pd.DataFrame, targets: pd.DataFrame,
                       cost_bps: float = COST_BPS) -> pd.Series:
    """Monthly constant-mix with drift and rebalancing costs.

    Weights are set at the end of each month and earn the next month's return.
    The target at row t is applied to row t (the row is already the next month's
    return in the caller), so there is no look-ahead: targets are built from
    trailing data.
    """
    R = returns.fillna(0.0)
    T = targets.reindex(R.index).fillna(0.0)
    if not len(R):
        return pd.Series(dtype=float)
    w = T.iloc[0].copy()
    out = []
    for d, r in R.iterrows():
        port = float((w * r).sum())
        if 1.0 + port != 0:
            w = w * (1.0 + r) / (1.0 + port)
        tgt = T.loc[d]
        trade = float((tgt - w).abs().sum())
        port -= trade * cost_bps / 1e4
        w = tgt.copy()
        out.append(port)
    return pd.Series(out, index=R.index)


def _book_and_overlays(df: pd.DataFrame, live: pd.DataFrame,
                       bench: pd.Series, spy: pd.Series, rf: pd.Series,
                       label: str) -> dict:
    n = df.shape[1]
    books = {
        "equal": rebalanced_returns(df, equal_targets(df, live)),
        "invvol": rebalanced_returns(df, invvol_targets(df, live)),
    }

    cols3 = [c for c in df.columns if c != "bab"]
    if len(cols3) == n - 1:
        books["equal_no_bab"] = rebalanced_returns(
            df[cols3], equal_targets(df[cols3], live[cols3])
        )
        books["invvol_no_bab"] = rebalanced_returns(
            df[cols3], invvol_targets(df[cols3], live[cols3])
        )

    overlays = {}
    for key, book in books.items():
        for frac in (0.2, 0.3):
            mix = pd.DataFrame({"bench": bench.reindex(book.index),
                                "book": book.reindex(book.index)}).dropna()
            tgt = pd.DataFrame({"bench": 1.0 - frac, "book": frac}, index=mix.index)
            overlays[f"{key}_{int(frac * 100)}"] = rebalanced_returns(mix, tgt)

    out = {
        "label": label,
        "window": [str(df.index[0]), str(df.index[-1])],
        "sleeves": {c: perf_m(df[c].where(live[c])) for c in df.columns},
        "books": {k: perf_m(v) for k, v in books.items()},
        "overlays": {k: perf_m(v, rf_monthly=rf) for k, v in overlays.items()},
        "benchmarks": {
            "SPY": perf_m(spy.reindex(df.index), rf_monthly=rf.reindex(df.index)),
            "60_40_monthly": perf_m(bench.reindex(df.index),
                                   rf_monthly=rf.reindex(df.index)),
        },
        "claims": {},
    }
    for key, s in overlays.items():
        s = s.dropna()
        sr = float(s.mean() / s.std()) if s.std() > 0 else 0.0
        out["claims"][key] = {
            "stats": perf_m(s, rf_monthly=rf),
            "dsr_all_trials": deflated_sharpe(
                sr, TRIALS_ALL, len(s), float(s.skew()), float(s.kurtosis() + 3)
            ),
            "dsr_final_variants": deflated_sharpe(
                sr, TRIALS_FINAL, len(s), float(s.skew()), float(s.kurtosis() + 3)
            ),
            "bootstrap": bootstrap_sharpe(s, n_boot=2000, block=6, periods=12),
        }
    return out


def run() -> dict:
    spy, bench, rf = _monthly_benchmarks()
    out = {
        "trials": {
            "prior_inercia": 26,
            "prior_cartograf": 23,
            "phase3": TRIALS_PHASE3,
            "all": TRIALS_ALL,
            "final": TRIALS_FINAL,
        },
        "cost_bps": COST_BPS,
        "frequency": "monthly",
        "rule": "not-live sleeves are cash; no backfill; drift and rebalancing costs charged",
    }

    for wname in ("A", "B"):
        df, live, label = load_sleeves(wname)
        out[wname] = _book_and_overlays(df, live, bench, spy, rf, label)

    with open(OUT / "phase3_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    # Chart: Window B, the gated-VRP claim.
    # Build the two headline books once for the chart; the JSON holds the numbers.
    dfb, liveb, _ = load_sleeves("B")
    series = {"SPY": spy.reindex(dfb.index), "60/40": bench.reindex(dfb.index)}
    eq = rebalanced_returns(dfb, equal_targets(dfb, liveb))
    iv = rebalanced_returns(dfb, invvol_targets(dfb, liveb))
    for name, book, frac in (("60/40 + 30% equal", eq, 0.3),
                             ("60/40 + 30% invvol", iv, 0.3)):
        mix = pd.DataFrame({"bench": bench.reindex(book.index),
                            "book": book.reindex(book.index)}).dropna()
        tgt = pd.DataFrame({"bench": 1 - frac, "book": frac}, index=mix.index)
        series[name] = rebalanced_returns(mix, tgt)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for name, s in series.items():
        ax.plot(s.index.to_timestamp(), (1 + s.fillna(0)).cumprod(), label=name, lw=1.7)
    ax.set_yscale("log")
    ax.set_title("Phase 3 — combined book (Window B, gated VRP, net of costs)")
    ax.set_ylabel("growth of 1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "10_phase3.png", dpi=110)
    plt.close(fig)
    return out
