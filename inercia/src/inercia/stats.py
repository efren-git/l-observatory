"""Performance statistics and risk transforms."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _round(x, n=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def annual_returns(r: pd.Series) -> pd.Series:
    r = r.dropna()
    return (1 + r).resample("YE").prod() - 1


def perf(r: pd.Series, rf: pd.Series | None = None, periods: int = 252) -> dict:
    """Return the standard metric block. rf adds excess-return columns."""
    r = pd.Series(r).dropna().astype(float)
    if len(r) < 2:
        return {}
    eq = (1 + r).cumprod()
    vol = float(r.std() * np.sqrt(periods))
    cagr = float(eq.iloc[-1] ** (periods / len(r)) - 1)
    sharpe = float(r.mean() / r.std() * np.sqrt(periods)) if r.std() > 0 else 0.0
    downside = float(r[r < 0].std() * np.sqrt(periods)) if (r < 0).any() else np.nan
    sortino = float(r.mean() * periods / downside) if downside and downside > 0 else None
    maxdd = float((eq / eq.cummax() - 1).min())
    years = annual_returns(r)
    out = {
        "CAGR": _round(cagr),
        "Vol": _round(vol),
        "Sharpe": _round(sharpe, 3),
        "Sortino": _round(sortino, 3),
        "MaxDD": _round(maxdd),
        "Total": _round(eq.iloc[-1] - 1, 2),
        "WorstYr": _round(years.min()) if len(years) else None,
        "BestYr": _round(years.max()) if len(years) else None,
    }
    if rf is not None:
        rf = pd.Series(rf).reindex(r.index).ffill().fillna(0.0)
        ex = r - rf
        eqe = (1 + ex).cumprod()
        ve = float(ex.std() * np.sqrt(periods))
        out["CAGR_excess"] = _round(eqe.iloc[-1] ** (periods / len(ex)) - 1)
        out["Sharpe_excess"] = _round(ex.mean() / ex.std() * np.sqrt(periods), 3) if ex.std() > 0 else None
        out["Vol_excess"] = _round(ve)
    return out


def vol_target(r: pd.Series, target: float = 0.10, window: int = 60,
               max_leverage: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """Scale a daily return series to a target annualised volatility.

    The scale uses information through t-1 only; it is applied to the return at t.
    """
    r = pd.Series(r).astype(float)
    rv = r.rolling(window).std() * np.sqrt(252.0)
    scale = (target / rv.shift(1)).clip(0.0, max_leverage).fillna(1.0)
    return r * scale, scale


def drawdown_control(r: pd.Series, maxdd: float = 0.20, floor: float = 0.0) -> pd.Series:
    """CPPI-style exposure cut as the drawdown deepens (no look-ahead)."""
    r = pd.Series(r).fillna(0.0)
    eq = 1.0
    peak = 1.0
    out = []
    for x in r:
        dd = eq / peak - 1.0
        mult = float(np.clip(1.0 + dd / maxdd, floor, 1.0))
        rr = float(x) * mult
        eq *= 1.0 + rr
        peak = max(peak, eq)
        out.append(rr)
    return pd.Series(out, index=r.index)


def sharpe_daily(r: pd.Series) -> float:
    r = pd.Series(r).dropna()
    return float(r.mean() / r.std()) if r.std() > 0 else 0.0


def deflated_sharpe(sr: float, n_trials: int, n_obs: int,
                    skew: float = 0.0, kurt: float = 3.0) -> dict:
    """Bailey & Lopez de Prado (2014) Deflated Sharpe Ratio.

    sr is the non-annualised Sharpe ratio; kurt is raw kurtosis (normal = 3).
    """
    if n_trials < 1 or n_obs < 2:
        return {}
    emc = 0.5772156649015329
    var_sr = (1.0 - skew * sr + (kurt - 1.0) / 4.0 * sr ** 2) / (n_obs - 1.0)
    if var_sr <= 0:
        return {}
    sr0 = np.sqrt(var_sr) * (
        (1.0 - emc) * norm.ppf(1.0 - 1.0 / n_trials)
        + emc * norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    )
    dsr = float(norm.cdf((sr - sr0) / np.sqrt(var_sr)))
    return {
        "sharpe_daily": _round(sr, 5),
        "sr0_expected_max": _round(sr0, 5),
        "dsr": _round(dsr, 4),
        "n_trials": int(n_trials),
        "n_obs": int(n_obs),
        "skew": _round(skew, 3),
        "kurtosis": _round(kurt, 3),
    }
