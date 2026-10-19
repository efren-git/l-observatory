"""Book construction: equal weight, inverse vol, HRP, and the core book."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import hrp_weights
from .config import TARGET
from .stats import vol_target


def equal_book(sleeves: pd.DataFrame) -> pd.Series:
    return vol_target(sleeves.mean(axis=1), TARGET)[0]


def invvol_book(sleeves: pd.DataFrame) -> pd.Series:
    trailing = sleeves.rolling(63).std() * np.sqrt(252)
    ivw = (1.0 / trailing.replace(0, np.nan)).shift(1)
    ivw = ivw.div(ivw.sum(axis=1), axis=0)
    return vol_target((sleeves * ivw).sum(axis=1), TARGET)[0]


def hrp_book(sleeves: pd.DataFrame, min_hist: int = 36, rebalance_month: int = 1):
    """HRP with annual re-estimation on the first trading day of January.

    The old code re-estimated every January *day* and stored every day's weights
    in metrics.json. The weights were identical within January, so the JSON was
    needlessly large. This version re-estimates once per year and stores only the
    annual weights.
    """
    cols = list(sleeves.columns)
    monthly = (1 + sleeves).resample("ME").prod() - 1.0
    ret = pd.Series(0.0, index=sleeves.index)
    w_cur = pd.Series(1.0 / len(cols), index=cols)
    diag = {}
    current_year = None
    for i, d in enumerate(sleeves.index):
        if d.month == rebalance_month and d.year != current_year:
            current_year = d.year
            hist = monthly.loc[:d].dropna().tail(min_hist)
            if len(hist) >= 18:
                w_new = hrp_weights(hist).reindex(cols).fillna(0.0)
                if float(w_new.sum()) > 1e-6:
                    w_cur = w_new / w_new.sum()
                    diag[str(d.date())] = {c: round(float(v), 3) for c, v in w_cur.items()}
        ret.iloc[i] = float((sleeves.loc[d, cols] * w_cur).sum())
    return vol_target(ret, TARGET)[0], diag


def core_book(sleeves: pd.DataFrame, cols=("trend", "bab", "vrp")) -> pd.Series:
    """Equal-weight the pre-specified survivors; vol-target the book."""
    return vol_target(sleeves[list(cols)].mean(axis=1), TARGET)[0]


def mix_with_benchmark(bench: pd.Series, sleeve: pd.Series,
                       frac: float = 0.3) -> pd.Series:
    idx = bench.index.intersection(sleeve.index)
    return (1 - frac) * bench.reindex(idx) + frac * sleeve.reindex(idx)
