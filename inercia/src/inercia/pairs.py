"""Pairs / statistical-arbitrage research.

The first pre-specified pair is KO/PEP: two consumer-staples compounders with a
long common history. The implementation is deliberately simple and honest:

* rolling hedge ratio (252 days, shifted one day);
* spread z-score (60 days, shifted one day);
* enter at |z| > entry, exit at |z| < exit or after max_hold days;
* dollar-neutral spread return, gross normalised by 1 + |beta|;
* 5 bps per leg per turn, plus 50 bps/year short borrow.

The full-sample ADF t-stat is reported as context, not as a trading signal. The
trading hedge ratio is rolling, so the strategy never uses the full-sample fit.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import load_series, prices
from .stats import bootstrap_sharpe, perf


def load_pair(a: str = "KO", b: str = "PEP") -> pd.DataFrame:
    pa = load_series("stocks", a)
    pb = load_series("stocks", b)
    df = pd.DataFrame({a: pa, b: pb}).dropna()
    return df


def _signals(a: str, b: str, beta_window: int = 252, z_window: int = 60,
             entry: float = 2.0, exit: float = 0.5, max_hold: int = 60):
    px = load_pair(a, b)
    la, lb = np.log(px[a]), np.log(px[b])
    beta = la.rolling(beta_window).cov(lb) / lb.rolling(beta_window).var()
    alpha = la.rolling(beta_window).mean() - beta * lb.rolling(beta_window).mean()
    beta_lag, alpha_lag = beta.shift(1), alpha.shift(1)
    spread = la - beta_lag * lb - alpha_lag
    mu = spread.rolling(z_window).mean()
    sd = spread.rolling(z_window).std()
    z = ((spread - mu) / sd).shift(1)
    pos = _positions(z, entry, exit, max_hold)
    return pd.DataFrame({
        "px_a": px[a], "px_b": px[b], "log_a": la, "log_b": lb,
        "beta": beta_lag, "alpha": alpha_lag, "spread": spread,
        "z": z, "position": pos,
    }).dropna(subset=["beta", "z"])


def _positions(z: pd.Series, entry: float, exit: float, max_hold: int) -> pd.Series:
    state = 0
    held = 0
    out = []
    for zi in z.fillna(0.0).to_numpy():
        if state == 0:
            if zi > entry:
                state, held = -1, 0
            elif zi < -entry:
                state, held = 1, 0
        else:
            held += 1
            if abs(zi) < exit or held >= max_hold:
                state = 0
        out.append(state)
    return pd.Series(out, index=z.index, dtype=float)


def pair_backtest(a: str = "KO", b: str = "PEP", beta_window: int = 252,
                  z_window: int = 60, entry: float = 2.0, exit: float = 0.5,
                  max_hold: int = 60, cost_bps: float = 5.0,
                  borrow_bps: float = 50.0):
    sig = _signals(a, b, beta_window, z_window, entry, exit, max_hold)
    ra = sig["log_a"].diff()
    rb = sig["log_b"].diff()
    gross = sig["position"] * (ra - sig["beta"] * rb) / (1.0 + sig["beta"].abs())
    turnover = sig["position"].diff().abs().fillna(0.0)
    cost = turnover * cost_bps / 1e4 * 2.0
    borrow = sig["position"].abs() * borrow_bps / 1e4 / 252.0
    net = (gross - cost - borrow).dropna()
    spy = prices()["SPY"].pct_change().reindex(net.index)
    diag = {
        "pair": f"{a}/{b}",
        "start": str(net.index[0].date()),
        "end": str(net.index[-1].date()),
        "n_days": int(len(net)),
        "annual_turnover": round(float(turnover.mean() * 252.0), 1),
        "avg_abs_position": round(float(sig["position"].abs().mean()), 3),
        "avg_beta": round(float(sig["beta"].mean()), 3),
        "corr_spy": round(float(net.corr(spy)), 3),
        "cost_bps_per_leg": cost_bps,
        "borrow_bps": borrow_bps,
    }
    return net, diag, sig


def cointegration_tstat(a: str = "KO", b: str = "PEP") -> dict:
    """Full-sample Engle-Granger residual ADF t-stat (constant, no lags)."""
    px = load_pair(a, b)
    la, lb = np.log(px[a]).to_numpy(), np.log(px[b]).to_numpy()
    X = np.column_stack([np.ones(len(lb)), lb])
    bhat = np.linalg.lstsq(X, la, rcond=None)[0]
    resid = la - X @ bhat
    dy = np.diff(resid)
    lag = resid[:-1]
    X2 = np.column_stack([np.ones(len(lag)), lag])
    b2 = np.linalg.lstsq(X2, dy, rcond=None)[0]
    e = dy - X2 @ b2
    s2 = float(e @ e / (len(dy) - 2))
    cov = s2 * np.linalg.inv(X2.T @ X2)
    tstat = float(b2[1] / np.sqrt(cov[1, 1]))
    # MacKinnon approximate 5% critical value for a constant, large sample.
    return {
        "beta": round(float(bhat[1]), 4),
        "adf_t": round(tstat, 3),
        "crit_5pct_approx": -2.86,
        "cointegrated_5pct": bool(tstat < -2.86),
        "note": "full-sample Engle-Granger; the trading beta is rolling",
    }


def half_life(a: str = "KO", b: str = "PEP") -> float:
    px = load_pair(a, b)
    la, lb = np.log(px[a]), np.log(px[b])
    X = np.column_stack([np.ones(len(lb)), lb.to_numpy()])
    bhat = np.linalg.lstsq(X, la.to_numpy(), rcond=None)[0]
    spread = la.to_numpy() - X @ bhat
    dy = np.diff(spread)
    lag = spread[:-1]
    X2 = np.column_stack([np.ones(len(lag)), lag])
    b2 = np.linalg.lstsq(X2, dy, rcond=None)[0]
    phi = float(b2[1])
    if phi >= 0 or phi <= -1:
        return np.nan
    return float(-np.log(2.0) / np.log(1.0 + phi))


def summary(a: str = "KO", b: str = "PEP", **kwargs) -> dict:
    net, diag, sig = pair_backtest(a, b, **kwargs)
    return {
        "stats": perf(net),
        "bootstrap": bootstrap_sharpe(net, n_boot=2000, block=21),
        "diagnostics": diag,
        "cointegration": cointegration_tstat(a, b),
        "half_life_days": round(half_life(a, b), 1) if np.isfinite(half_life(a, b)) else None,
        "monthly": ((1.0 + net).resample("ME").prod() - 1.0),
    }


def current_signal(a: str = "KO", b: str = "PEP", **kwargs) -> dict:
    _, _, sig = pair_backtest(a, b, **kwargs)
    last = sig.iloc[-1]
    return {
        "as_of": str(sig.index[-1].date()),
        "pair": f"{a}/{b}",
        "beta": round(float(last["beta"]), 4),
        "spread": round(float(last["spread"]), 5),
        "z": round(float(last["z"]), 3),
        "position": int(last["position"]),
        "action": {1: "long spread (long A / short beta*B)",
                   -1: "short spread (short A / long beta*B)",
                   0: "flat"}[int(last["position"])],
    }
