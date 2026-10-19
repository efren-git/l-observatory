"""Cached data access for cartograf.

The raw files are downloaded by fetch_data.py and are git-ignored. This module is
read-only: every loader returns a copy-safe frame and no caller mutates it.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import RAW, RATE_LAG_MONTHS


def _read_csv(name: str, date_col: str = "Date") -> pd.DataFrame:
    p = Path(RAW) / name
    d = pd.read_csv(p)
    lower = {c.lower(): c for c in d.columns}
    dc = lower.get(date_col.lower()) or lower.get("date") or d.columns[0]
    d[dc] = pd.to_datetime(d[dc], errors="coerce")
    d = d.dropna(subset=[dc]).set_index(dc).sort_index()
    return d[~d.index.duplicated(keep="last")]


@lru_cache(maxsize=1)
def prices() -> pd.DataFrame:
    return _read_csv("prices.csv")


@lru_cache(maxsize=1)
def fred() -> pd.DataFrame:
    return _read_csv("fred_carry.csv")


@lru_cache(maxsize=1)
def dividends() -> pd.DataFrame:
    return _read_csv("dividends.csv")


@lru_cache(maxsize=1)
def cboe_term() -> pd.DataFrame:
    return _read_csv("cboe_vix_term.csv")


@lru_cache(maxsize=None)
def factor(name: str) -> pd.DataFrame:
    return _read_csv(name)


def daily_rate(col: str, index: pd.DatetimeIndex | None = None) -> pd.Series:
    """A daily yield series (percent), forward-filled and optionally aligned."""
    s = fred()[col].ffill()
    if index is not None:
        s = s.reindex(index, method="ffill")
    return s


def monthly_rate_lagged(col: str, index: pd.DatetimeIndex,
                        lag_months: int = RATE_LAG_MONTHS) -> pd.Series:
    """Monthly-average policy rate, made publication-safe and aligned to daily dates.

    FRED IR3TIB series are averages of a month. A value for month t is not
    knowable at the start of month t (and often not on day 1 of t+1), so the
    default lag is two months. This is the FX-carry fix described in the audit.
    """
    s = fred()[col].dropna()
    m = s.resample("ME").last()
    m.index = m.index.to_period("M") + lag_months
    m = m.sort_index()
    m.index = m.index.to_timestamp(how="end").normalize()
    return m.reindex(index, method="ffill")


def risk_free_daily(index: pd.DatetimeIndex) -> pd.Series:
    """US 3-month T-bill daily return, lagged one day (known at yesterday's close)."""
    y = daily_rate("dgs3mo", index).shift(1).fillna(0.0)
    return y / 100.0 / 252.0


def risk_free_monthly(index: pd.DatetimeIndex) -> pd.Series:
    y = daily_rate("dgs3mo").resample("ME").last().shift(1)
    return (y.reindex(index, method="ffill").fillna(0.0) / 100.0 / 12.0)


def survivorship_note() -> dict:
    return {
        "universe": "current liquid ETF list",
        "biased": True,
        "direction": "upward",
        "reason": "funds that closed or never gathered assets are absent; "
                  "the list is chosen with today's knowledge",
        "treatment": "reported as a caveat; no point-in-time ETF membership is free",
    }
