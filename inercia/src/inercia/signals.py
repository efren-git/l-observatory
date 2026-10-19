"""Signal construction. Every signal uses information available at t."""
from __future__ import annotations

import numpy as np
import pandas as pd

M = 21


def ts_momentum(px: pd.DataFrame, lookbacks=(1, 3, 6, 12), m: int = M) -> pd.DataFrame:
    parts = [np.sign(px / px.shift(n * m) - 1.0) for n in lookbacks]
    return sum(parts) / len(parts)


def xs_momentum(px: pd.DataFrame, m: int = M) -> pd.DataFrame:
    raw = px.shift(m) / px.shift(12 * m) - 1.0
    return np.sign(raw.rank(axis=1, pct=True) - 0.5).fillna(0.0)


def xs_zscore(px: pd.DataFrame, m: int = M, clip: float = 3.0) -> pd.DataFrame:
    raw = px.shift(m) / px.shift(12 * m) - 1.0
    z = raw.sub(raw.mean(axis=1), axis=0).div(raw.std(axis=1), axis=0)
    return z.clip(-clip, clip).fillna(0.0)


def short_term_reversal(px: pd.DataFrame, m: int = M) -> pd.DataFrame:
    raw = px / px.shift(m) - 1.0
    return -np.sign(raw.rank(axis=1, pct=True) - 0.5).fillna(0.0)


def carry_zscore(carry: pd.DataFrame) -> pd.DataFrame:
    z = carry.sub(carry.mean(axis=1), axis=0).div(carry.std(axis=1), axis=0)
    return z.fillna(0.0)
