"""Relative-value lab: buy one asset, short a related one.

Pre-registered before the run (2026-10-20):

* 27 economically linked ETF pairs (sectors, countries, bonds, commodities,
  styles, FX). The list is fixed; it is not expanded after seeing results.
* Rolling hedge ratio (252 days) and spread z-score (60 days), both lagged.
* Entry |z| > 2.0, exit |z| < 0.5, stop after 60 trading days.
* Quarterly selection: keep a pair only if, on the trailing 252 days, the
  Engle-Granger residual has ADF t < -2.86 and a half-life < 63 days.
* At most 8 pairs, ranked by ADF t; equal weight across the selected pairs.
* 5 bps per leg per turn and 50 bps/year short borrow on each pair. The
  portfolio is scaled to 10% vol with a 60-day estimate, shifted one day.
* Trials: 27 pairs. The walk-forward is one strategy, not 84 independent bets.

The question is not "can I find a pair that worked?" It is "does a diversified,
walk-forward-selected basket of pairs make money after costs?" The answer is
allowed to be no.
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
from .pairs import _positions
from .stats import bootstrap_sharpe, deflated_sharpe, perf, perf_m

BETA_WINDOW = 252
Z_WINDOW = 60
ENTRY = 2.0
EXIT = 0.5
MAX_HOLD = 60
COST_BPS = 5.0
BORROW_BPS = 50.0
ADF_CUT = -2.86
MAX_HALF_LIFE = 63
MAX_PAIRS = 8
TARGET_VOL = 0.10
TRIALS = 27

# Fixed before the run. Each pair is an economic link, not a correlation screen.
PAIRS = {
    "XLE/XOP": ("XLE", "XOP"), "XLF/KRE": ("XLF", "KRE"),
    "XLV/XBI": ("XLV", "XBI"), "XLB/XME": ("XLB", "XME"),
    "XLY/XRT": ("XLY", "XRT"), "XLK/SMH": ("XLK", "SMH"),
    "XLI/IYT": ("XLI", "IYT"), "ITB/XHB": ("ITB", "XHB"),
    "IYR/VNQ": ("IYR", "VNQ"), "EWA/EWC": ("EWA", "EWC"),
    "EWG/EWU": ("EWG", "EWU"), "EWI/EWP": ("EWI", "EWP"),
    "IEF/TLT": ("IEF", "TLT"), "SHY/IEF": ("SHY", "IEF"),
    "LQD/HYG": ("LQD", "HYG"), "TIP/IEF": ("TIP", "IEF"),
    "EMB/LQD": ("EMB", "LQD"), "GLD/SLV": ("GLD", "SLV"),
    "USO/DBC": ("USO", "DBC"), "SPY/IWM": ("SPY", "IWM"),
    "SPY/MDY": ("SPY", "MDY"), "IWM/MDY": ("IWM", "MDY"),
    "FXE/UUP": ("FXE", "UUP"), "FXB/FXE": ("FXB", "FXE"),
    "FXC/FXB": ("FXC", "FXB"), "FXY/FXE": ("FXY", "FXE"),
    "EFA/EEM": ("EFA", "EEM"),
}


def _pair_series(a: str, b: str, px: pd.DataFrame) -> pd.Series:
    la, lb = np.log(px[a]), np.log(px[b])
    beta = la.rolling(BETA_WINDOW).cov(lb) / lb.rolling(BETA_WINDOW).var()
    alpha = la.rolling(BETA_WINDOW).mean() - beta * lb.rolling(BETA_WINDOW).mean()
    bl, al = beta.shift(1), alpha.shift(1)
    spread = la - bl * lb - al
    mu = spread.rolling(Z_WINDOW).mean()
    sd = spread.rolling(Z_WINDOW).std()
    z = ((spread - mu) / sd).shift(1)
    pos = _positions(z, ENTRY, EXIT, MAX_HOLD)
    ra, rb = la.diff(), lb.diff()
    gross = pos * (ra - bl * rb) / (1.0 + bl.abs())
    turn = pos.diff().abs().fillna(0.0)
    cost = turn * COST_BPS / 1e4 * 2.0
    borrow = pos.abs() * BORROW_BPS / 1e4 / 252.0
    return (gross - cost - borrow).dropna()


def _adf_half_life(la: pd.Series, lb: pd.Series) -> tuple[float, float]:
    """Engle-Granger ADF t and mean-reversion half-life on one window."""
    x, y = la.to_numpy(dtype=float), lb.to_numpy(dtype=float)
    if len(x) < 50 or not np.isfinite(x).all() or not np.isfinite(y).all():
        return 0.0, np.inf
    X = np.column_stack([np.ones(len(y)), y])
    bhat = np.linalg.lstsq(X, x, rcond=None)[0]
    resid = x - X @ bhat
    dy, lag = np.diff(resid), resid[:-1]
    X2 = np.column_stack([np.ones(len(lag)), lag])
    b2 = np.linalg.lstsq(X2, dy, rcond=None)[0]
    e = dy - X2 @ b2
    s2 = float(e @ e / max(len(dy) - 2, 1))
    cov = s2 * np.linalg.inv(X2.T @ X2)
    t = float(b2[1] / np.sqrt(cov[1, 1])) if cov[1, 1] > 0 else 0.0
    phi = float(b2[1])
    hl = float(-np.log(2.0) / np.log(1.0 + phi)) if -1.0 < phi < 0.0 else np.inf
    return t, hl


def _quarter_ends(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    s = pd.Series(index, index=index)
    return pd.DatetimeIndex(s.groupby(index.to_period("Q")).last().to_numpy())


def selections(px: pd.DataFrame, pairs: dict) -> pd.DataFrame:
    """Quarterly selection matrix: 1 if the pair is allowed to trade."""
    qe = _quarter_ends(px.index)
    sel = pd.DataFrame(0.0, index=px.index, columns=list(pairs))
    la = np.log(px)
    for d in qe:
        hist = la.loc[:d].iloc[-BETA_WINDOW:]
        if len(hist) < BETA_WINDOW:
            continue
        ranked = []
        for name, (a, b) in pairs.items():
            sub = hist[[a, b]].dropna()
            if len(sub) < BETA_WINDOW:
                continue
            t, hl = _adf_half_life(sub[a], sub[b])
            if t < ADF_CUT and hl < MAX_HALF_LIFE:
                ranked.append((t, hl, name))
        ranked.sort(key=lambda x: x[0])
        chosen = [name for _, _, name in ranked[:MAX_PAIRS]]
        if chosen:
            # Replace the previous quarter's basket; do not accumulate it.
            sel.loc[d:, :] = 0.0
            sel.loc[d:, chosen] = 1.0 / len(chosen)
    return sel.shift(1).fillna(0.0)


def _vol_target(r: pd.Series, target: float = TARGET_VOL) -> pd.Series:
    vol = r.rolling(60).std() * np.sqrt(252.0)
    scale = (target / vol.shift(1)).clip(0.0, 3.0).fillna(0.0)
    cost = scale.diff().abs().fillna(0.0) * COST_BPS / 1e4
    return r * scale - cost


def run() -> dict:
    px = prices()
    net = pd.DataFrame({name: _pair_series(a, b, px)
                        for name, (a, b) in PAIRS.items()}).dropna(how="all")
    sel = selections(px, PAIRS).reindex(net.index).fillna(0.0)
    port = (sel * net).sum(axis=1)
    port = _vol_target(port).dropna()

    spy = px["SPY"].pct_change().reindex(port.index)
    ief = px["IEF"].pct_change().reindex(port.index)
    bench = 0.6 * spy + 0.4 * ief

    active = (sel > 0).sum(axis=1)
    out = {
        "rule": {
            "pairs": len(PAIRS), "beta_window": BETA_WINDOW,
            "z_window": Z_WINDOW, "entry": ENTRY, "exit": EXIT,
            "max_hold": MAX_HOLD, "adf_cut": ADF_CUT,
            "max_half_life": MAX_HALF_LIFE, "max_pairs": MAX_PAIRS,
            "cost_bps_per_leg": COST_BPS, "borrow_bps": BORROW_BPS,
            "vol_target": TARGET_VOL, "trials": TRIALS,
        },
        "window": [str(net.index.min().date()), str(net.index.max().date())],
        "portfolio": perf(port),
        "portfolio_monthly": perf_m((1 + port).resample("ME").prod() - 1),
        "bench_spy": perf(spy.dropna()),
        "bench_6040": perf(bench.dropna()),
        "bootstrap": bootstrap_sharpe(port, n_boot=2000, block=21),
        "dsr": deflated_sharpe(
            float(port.mean() / port.std()), TRIALS, len(port),
            skew=float(port.skew()), kurt=float(port.kurtosis() + 3),
        ),
        "active_pairs": {
            "mean": round(float(active.mean()), 2),
            "max": int(active.max()),
            "months_with_zero": int((active.resample("ME").last() == 0).sum()),
        },
        "per_pair": {},
    }
    for name in PAIRS:
        s = (sel[name] * net[name]).dropna()
        # Contribution is scaled by the same vol-target multiplier.
        contrib = s.reindex(port.index).fillna(0.0)
        out["per_pair"][name] = {
            "selected_days": int((sel[name] > 0).sum()),
            "standalone": perf(net[name].dropna()),
            "contribution_cagr": round(float((1 + contrib).prod()
                                             ** (252.0 / max(len(contrib), 1)) - 1), 4),
            "corr_to_spy": round(float(net[name].corr(spy)), 3),
        }

    with open(OUT / "relval_metrics.json", "w") as f:
        json.dump(out, f, indent=2)

    fig, ax = plt.subplots(figsize=(11, 5.5))
    for name, s in (("relative value", port), ("SPY", spy), ("60/40", bench)):
        ax.plot(s.index, (1 + s.fillna(0)).cumprod(), label=name, lw=1.7)
    ax.set_yscale("log")
    ax.set_title("Relative-value basket — walk-forward selected, net of costs")
    ax.set_ylabel("growth of 1")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUT / "15_relval.png", dpi=110)
    plt.close(fig)
    return out
