"""Performance statistics and risk transforms."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from .config import TD


def _r(x, n=4):
    if x is None:
        return None
    x = float(x)
    return round(x, n) if np.isfinite(x) else None


def annual_returns(daily: pd.Series) -> pd.Series:
    d = pd.Series(daily).dropna()
    return (1 + d).groupby(d.index.year).prod() - 1


def _completed_annual(daily: pd.Series, min_obs: int = 200) -> pd.Series:
    """Annual returns for complete years only (exclude the current stub)."""
    d = pd.Series(daily).dropna()
    ann = annual_returns(d)
    counts = d.groupby(d.index.year).size()
    keep = [y for y in ann.index if int(counts.get(y, 0)) >= min_obs]
    return ann.loc[keep]


def downside_deviation(daily: pd.Series, periods: int = TD) -> float:
    """Downside deviation relative to zero, the Sortino denominator."""
    d = pd.Series(daily).dropna().astype(float)
    if not len(d):
        return np.nan
    return float(np.sqrt(np.mean(np.minimum(d, 0.0) ** 2)) * np.sqrt(periods))


def perf(daily: pd.Series, rf_daily: pd.Series | None = None,
         min_obs: int = 40) -> dict:
    """Daily performance. rf_daily adds excess-return columns.

    Self-financing sleeves should be called without rf_daily: subtracting T-bills
    from a long/short book that is already funded is double-counting. Net-long
    benchmarks (SPY, 60/40) get both raw and excess columns.
    """
    d = pd.Series(daily).dropna().astype(float)
    if len(d) < min_obs:
        return {}
    eq = (1 + d).cumprod()
    years = len(d) / TD
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = d.std() * np.sqrt(TD)
    sharpe = d.mean() / d.std() * np.sqrt(TD) if d.std() > 0 else 0.0
    dn = downside_deviation(d, TD)
    sortino = d.mean() * TD / dn if dn and dn > 0 else 0.0
    dd = eq / eq.cummax() - 1
    ann = _completed_annual(d, 200)
    out = dict(CAGR=_r(cagr), Vol=_r(vol), Sharpe=_r(sharpe, 3),
               Sortino=_r(sortino, 3), MaxDD=_r(dd.min()),
               Total=_r(eq.iloc[-1] - 1), WorstYear=_r(ann.min()),
               BestYear=_r(ann.max()))
    if rf_daily is not None:
        rf = pd.Series(rf_daily).reindex(d.index).ffill().fillna(0.0)
        ex = d - rf
        eqe = (1 + ex).cumprod()
        out["CAGR_excess"] = _r(eqe.iloc[-1] ** (1 / years) - 1)
        out["Vol_excess"] = _r(ex.std() * np.sqrt(TD))
        out["Sharpe_excess"] = _r(ex.mean() / ex.std() * np.sqrt(TD), 3) if ex.std() > 0 else None
    return out


def perf_m(monthly: pd.Series, rf_monthly: pd.Series | None = None,
           min_obs: int = 24) -> dict:
    """Monthly performance, used by the VRP and factor cross-checks."""
    m = pd.Series(monthly).dropna().astype(float)
    if len(m) < min_obs:
        return {}
    eq = (1 + m).cumprod()
    years = len(m) / 12
    vol = m.std() * np.sqrt(12)
    dn = downside_deviation(m, 12)
    ann = _completed_annual(m, 12)
    out = dict(
        CAGR=_r(eq.iloc[-1] ** (1 / years) - 1),
        Vol=_r(vol),
        Sharpe=_r(m.mean() * 12 / vol, 3) if vol > 0 else 0.0,
        Sortino=_r(m.mean() * 12 / dn, 3) if dn and dn > 0 else None,
        MaxDD=_r((eq / eq.cummax() - 1).min()),
        WorstMonth=_r(m.min()),
        WorstYear=_r(ann.min()) if len(ann) else None,
        BestYear=_r(ann.max()) if len(ann) else None,
        Total=_r(eq.iloc[-1] - 1),
    )
    if rf_monthly is not None:
        rf = pd.Series(rf_monthly).reindex(m.index).ffill().fillna(0.0)
        ex = m - rf
        out["CAGR_excess"] = _r((1 + ex).cumprod().iloc[-1] ** (1 / years) - 1)
        out["Sharpe_excess"] = _r(ex.mean() / ex.std() * np.sqrt(12), 3) if ex.std() > 0 else None
    return out


def vol_target(daily: pd.Series, target: float = 0.10, win: int = 63,
               cap: float = 4.0, warmup: float = 1.0) -> tuple[pd.Series, pd.Series]:
    """Scale a daily return stream to a target vol using trailing data only.

    The old implementation filled the first win days with a zero scale, which
    silently put the book in cash for three months (including the start of 2008
    and the first two years of the VRP series). warmup=1.0 keeps the book
    invested at unit size until the first estimate exists. This is a deliberate,
    documented choice, not a free lunch: early risk is not target-controlled.
    """
    d = pd.Series(daily).fillna(0.0)
    vol = d.rolling(win).std() * np.sqrt(TD)
    scale = (target / vol.replace(0, np.nan)).clip(lower=0.0, upper=cap).shift(1)
    return d * scale.fillna(warmup), scale.fillna(warmup)


def vol_target_m(monthly: pd.Series, target: float = 0.10, win: int = 24,
                 cap: float = 4.0, warmup: float = 1.0) -> tuple[pd.Series, pd.Series]:
    """Monthly version of vol_target, for the monthly VRP/core book."""
    m = pd.Series(monthly).fillna(0.0)
    vol = m.rolling(win).std() * np.sqrt(12)
    scale = (target / vol.replace(0, np.nan)).clip(lower=0.0, upper=cap).shift(1)
    return m * scale.fillna(warmup), scale.fillna(warmup)


def drawdown(daily: pd.Series) -> tuple[pd.Series, pd.Series]:
    eq = (1 + pd.Series(daily).fillna(0)).cumprod()
    return eq / eq.cummax() - 1, eq


def sharpe_daily(daily: pd.Series) -> float:
    d = pd.Series(daily).dropna()
    return float(d.mean() / d.std()) if d.std() > 0 else 0.0


def bootstrap_sharpe(daily: pd.Series, n_boot: int = 2000, block: int = 21,
                     periods: int = TD, seed: int = 7) -> dict:
    """Moving-block bootstrap confidence interval for the annualised Sharpe."""
    r = pd.Series(daily).dropna().astype(float).to_numpy()
    n = len(r)
    if n < 2 * block:
        return {}
    rng = np.random.default_rng(seed)
    n_blocks = int(np.ceil(n / block))
    srs = []
    for _ in range(n_boot):
        starts = rng.integers(0, n - block + 1, size=n_blocks)
        sample = np.concatenate([r[s:s + block] for s in starts])[:n]
        sd = float(sample.std())
        if sd > 0:
            srs.append(float(sample.mean() / sd * np.sqrt(periods)))
    srs = np.asarray(srs)
    if not len(srs):
        return {}
    lo, hi = np.percentile(srs, [2.5, 97.5])
    return {
        "sharpe": _r(float(pd.Series(r).mean() / pd.Series(r).std() * np.sqrt(periods)), 3),
        "ci_low": _r(float(lo), 3),
        "ci_high": _r(float(hi), 3),
        "p_sharpe_gt_0": _r(float((srs > 0).mean()), 3),
        "n_boot": int(n_boot),
        "block": int(block),
        "n_obs": int(n),
    }


def deflated_sharpe(sr: float, n_trials: int, n_obs: int,
                    skew: float = 0.0, kurt: float = 3.0) -> dict:
    """Bailey & Lopez de Prado (2014). sr is the non-annualised Sharpe."""
    if n_trials < 1 or n_obs < 2:
        return {}
    emc = 0.5772156649015329
    var_sr = (1 - skew * sr + (kurt - 1) / 4 * sr ** 2) / (n_obs - 1)
    if var_sr <= 0:
        return {}
    sr0 = np.sqrt(var_sr) * (
        (1 - emc) * norm.ppf(1 - 1 / n_trials)
        + emc * norm.ppf(1 - 1 / (n_trials * np.e))
    )
    return dict(sharpe_daily=_r(sr, 5), sr0_expected_max=_r(sr0, 5),
                dsr=_r(float(norm.cdf((sr - sr0) / np.sqrt(var_sr))), 4),
                n_trials=int(n_trials), n_obs=int(n_obs),
                skew=_r(skew, 3), kurtosis=_r(kurt, 3))
