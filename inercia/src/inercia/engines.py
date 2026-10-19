"""Sleeve construction on top of signals + the canonical backtest."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import panel_backtest
from .config import M, STOCK_COST_BPS
from .data import CUR, RATEKEY, fx_panel, monthly_rate, rate_frame
from .signals import carry_zscore, short_term_reversal, ts_momentum, xs_momentum, xs_zscore

CLASS = {}
for t in ["SPY","IWM","MDY","XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY",
          "SMH","KRE","XBI","XRT","XOP","XME","ITB","IYT","XHB","EFA","EEM","EWJ",
          "EWU","EWG","EWC","EWA","EWH","EWS","EWT","EWY","EWZ","EWW","EWM","EWP",
          "EWL","EWD","EWI","EWO","EWN","EZA","FXI","INDA"]:
    CLASS[t] = "equity"
for t in ["TLT","IEF","SHY","LQD","HYG","TIP","EMB"]:
    CLASS[t] = "bond"
for t in ["GLD","SLV","DBC","USO","DBA"]:
    CLASS[t] = "commodity"
for t in ["VNQ","IYR"]:
    CLASS[t] = "reit"
for t in ["FXE","FXY","FXB","FXC","UUP"]:
    CLASS[t] = "fx"


def trend_weights(px: pd.DataFrame, use_xs: bool = True,
                  class_bal: bool = False) -> pd.DataFrame:
    ret = px.pct_change()
    ts = ts_momentum(px)
    xs = xs_momentum(px)
    signal = 0.5 * np.sign(ts) + 0.5 * xs if use_xs else np.sign(ts)
    vol = ret.rolling(20).std() * np.sqrt(252.0)
    raw = (signal / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    if class_bal:
        w = pd.DataFrame(0.0, index=raw.index, columns=raw.columns)
        for cl in sorted(set(CLASS.values())):
            mem = [t for t in raw.columns if CLASS.get(t) == cl]
            if not mem:
                continue
            sub = raw[mem]
            g = sub.abs().sum(axis=1).replace(0.0, np.nan)
            w[mem] = sub.div(g, axis=0).fillna(0.0) / len(set(CLASS.values()))
        return w
    return raw


def trend_returns(px: pd.DataFrame, use_xs: bool = True, class_bal: bool = False,
                  rebalance: str = "ME", cost_bps: float = 5.0) -> tuple[pd.Series, dict]:
    ret = px.pct_change()
    w = trend_weights(px, use_xs=use_xs, class_bal=class_bal)
    return panel_backtest(w, ret, rebalance=rebalance, cost_bps=cost_bps)


def reversal_returns(px: pd.DataFrame, cost_bps: float = 5.0) -> tuple[pd.Series, dict]:
    ret = px.pct_change()
    w = short_term_reversal(px)
    return panel_backtest(w, ret, cost_bps=cost_bps)


def carry_inputs(lag_months: int = 2) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return (fx returns, annualised carry differential, total FX+carry returns)."""
    fx = fx_panel()
    fxret = fx.pct_change()
    rates = rate_frame(list(CUR), lag_months=lag_months)
    usd = monthly_rate("US", lag_months)
    rd = rates.reindex(fxret.index, method="ffill")
    ud = usd.reindex(fxret.index, method="ffill")
    carry = rd.sub(ud, axis=0)
    total = fxret.add(carry / 100.0 / 252.0, fill_value=0.0)
    return fxret, carry, total


def carry_weights(carry: pd.DataFrame, total: pd.DataFrame) -> pd.DataFrame:
    z = carry_zscore(carry)
    vol = total.rolling(60).std() * np.sqrt(252.0)
    raw = (z / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return raw


def carry_returns(lag_months: int = 2, cost_bps: float = 5.0) -> tuple[pd.Series, dict, dict]:
    fxret, carry, total = carry_inputs(lag_months=lag_months)
    w = carry_weights(carry, total)
    r, diag = panel_backtest(w, total, cost_bps=cost_bps)
    return r, diag, {"lag_months": lag_months, "carry_mean": round(float(carry.mean().mean()), 3)}


def decile_weights(signal: pd.DataFrame, long_high: bool = True,
                   quantile: float = 0.1) -> pd.DataFrame:
    r = signal.rank(axis=1, pct=True)
    if not long_high:
        r = 1.0 - r
    w = pd.DataFrame(0.0, index=signal.index, columns=signal.columns)
    w[r >= 1.0 - quantile] = 1.0
    w[r <= quantile] = -1.0
    return w


def stock_sleeve(px: pd.DataFrame, kind: str = "mom",
                 cost_bps: float = STOCK_COST_BPS) -> tuple[pd.Series, dict]:
    ret = px.pct_change()
    if kind == "mom":
        signal = px.shift(M) / px.shift(12 * M) - 1.0
        w = decile_weights(signal, long_high=True)
    elif kind == "lowvol":
        signal = ret.rolling(252).std()
        w = decile_weights(signal, long_high=False)
    else:
        raise ValueError(kind)
    return panel_backtest(w, ret, cost_bps=cost_bps)
