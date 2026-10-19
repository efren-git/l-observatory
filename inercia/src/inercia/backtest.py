"""One canonical portfolio backtest.

Weights are target weights at the signal date. They are sampled at the rebalance
frequency, forward-filled, shifted one day, then scaled by a volatility target
computed from information through t-1. Turnover is charged on the scaled weights.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .stats import vol_target


def normalize_weights(w: pd.DataFrame) -> pd.DataFrame:
    gross = w.abs().sum(axis=1).replace(0.0, np.nan)
    return w.div(gross, axis=0).fillna(0.0)


def panel_backtest(weights: pd.DataFrame, returns: pd.DataFrame,
                   rebalance: str = "ME", cost_bps: float = 5.0,
                   target_vol: float = 0.10, vol_window: int = 60,
                   max_leverage: float = 3.0, lag: int = 1,
                   normalize: bool = True) -> tuple[pd.Series, dict]:
    idx = returns.index
    w = weights.reindex(index=idx, columns=returns.columns).fillna(0.0)
    if normalize:
        w = normalize_weights(w)
    w_reb = (
        w.resample(rebalance).last()
        .reindex(idx, method="ffill")
        .fillna(0.0)
        .shift(lag)
        .fillna(0.0)
    )
    gross = (w_reb * returns).sum(axis=1).fillna(0.0)
    net, scale = vol_target(gross, target=target_vol, window=vol_window,
                            max_leverage=max_leverage)
    ws = w_reb.mul(scale, axis=0)          # axis=0 aligns the date index
    turnover = ws.diff().abs().sum(axis=1).fillna(0.0)
    costs = turnover * (cost_bps / 1e4)
    net = gross * scale - costs
    diag = {
        "annual_turnover": round(float(turnover.mean() * 252), 1),
        "annual_cost_drag": round(float(costs.mean() * 252), 4),
        "avg_gross_exposure": round(float(ws.abs().sum(axis=1).mean()), 3),
        "avg_scale": round(float(scale.mean()), 3),
        "cost_bps": cost_bps,
        "rebalance": rebalance,
        "target_vol": target_vol,
    }
    return net, diag
