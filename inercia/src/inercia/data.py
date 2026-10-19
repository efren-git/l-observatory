"""Data access for inercia.

All loaders are read-only and cached. Dates are parsed, sorted, and de-duplicated.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from .config import RAW, RATE_LAG_MONTHS

CUR = {
    "EUR": False, "JPY": True, "GBP": False, "CAD": True, "AUD": False,
    "CHF": True, "NZD": False, "SEK": True, "NOK": True,
}
RATEKEY = {
    "EUR": "EU", "JPY": "JP", "GBP": "UK", "CAD": "CA", "AUD": "AU",
    "CHF": "CH", "NZD": "NZ", "SEK": "SE", "NOK": "NO",
}


def _read_csv(path: Path) -> pd.DataFrame:
    d = pd.read_csv(path)
    lower = {c.lower(): c for c in d.columns}
    date_col = lower.get("date") or lower.get("observation_date") or d.columns[0]
    d[date_col] = pd.to_datetime(d[date_col], errors="coerce")
    d = d.dropna(subset=[date_col]).set_index(date_col).sort_index()
    return d[~d.index.duplicated(keep="last")]


def load_series(folder: str, ticker: str) -> pd.Series:
    """Load one close/value series from data/raw/<folder>/<ticker>.csv."""
    d = _read_csv(Path(RAW) / folder / f"{ticker}.csv")
    for col in ("Close", "close", "Adj Close", "value", "VALUE"):
        if col in d.columns:
            return pd.to_numeric(d[col], errors="coerce")
    return pd.to_numeric(d.iloc[:, -1], errors="coerce")


def list_tickers(folder: str, exclude_prefixes: tuple[str, ...] = ()) -> list[str]:
    p = Path(RAW) / folder
    out = []
    for f in sorted(p.glob("*.csv")):
        if f.stem.startswith(exclude_prefixes):
            continue
        out.append(f.stem)
    return out


def load_panel(folder: str, tickers: list[str] | None = None,
               exclude_prefixes: tuple[str, ...] = ()) -> pd.DataFrame:
    if tickers is None:
        tickers = list_tickers(folder, exclude_prefixes=exclude_prefixes)
    cols = {}
    for t in tickers:
        try:
            s = load_series(folder, t)
        except FileNotFoundError:
            continue
        if s.notna().sum() > 100:
            cols[t] = s
    return pd.DataFrame(cols).sort_index()


@lru_cache(maxsize=1)
def prices() -> pd.DataFrame:
    return load_panel("prices")


@lru_cache(maxsize=1)
def stocks() -> pd.DataFrame:
    return load_panel("stocks", exclude_prefixes=("sp500",))


@lru_cache(maxsize=1)
def fx_panel() -> pd.DataFrame:
    """Each column is the value of one currency in USD."""
    cols = {}
    for c, invert in CUR.items():
        s = load_series("fx", c)
        cols[c] = (1.0 / s) if invert else s
    return pd.DataFrame(cols).sort_index()


@lru_cache(maxsize=None)
def monthly_rate(key: str, lag_months: int = RATE_LAG_MONTHS) -> pd.Series:
    """Monthly policy rate, shifted so the value is known before it is used.

    FRED IR3TIB series are monthly averages. A one-month shift still uses an
    average that is not published on day 1; two months is publication-safe.
    """
    s = load_series("fred", f"rate_{key}").dropna()
    s.index = s.index.to_period("M")
    s = s[~s.index.duplicated(keep="last")].sort_index()
    s.index = s.index + lag_months
    s = s.sort_index()
    s.index = s.index.to_timestamp(how="start")
    return s.astype(float)


def rate_frame(currencies: list[str] | None = None,
               lag_months: int = RATE_LAG_MONTHS) -> pd.DataFrame:
    currencies = currencies or list(CUR)
    return pd.DataFrame({c: monthly_rate(RATEKEY[c], lag_months) for c in currencies})


def risk_free_daily(index: pd.DatetimeIndex,
                    lag_months: int = RATE_LAG_MONTHS) -> pd.Series:
    """Daily risk-free return from the US 3-month rate (already publication-lagged)."""
    s = monthly_rate("US", lag_months)
    return s.reindex(index, method="ffill").fillna(0.0) / 100.0 / 252.0


def inception_dates(panel: pd.DataFrame) -> pd.Series:
    return pd.Series({c: panel[c].first_valid_index() for c in panel.columns})


def survivorship_note() -> dict:
    return {
        "universe": "current S&P 500 constituents",
        "biased": True,
        "direction": "upward",
        "reason": "no free point-in-time membership; delisted losers are absent",
        "treatment": "reported separately and excluded from the combined book",
    }
