"""Performance statistics and risk transforms."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _round(x, n=4):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def annual_returns(r: pd.Series) -> pd.Series:
    r = pd.Series(r).dropna()
    if isinstance(r.index, pd.PeriodIndex):
        # PeriodIndex does not accept the "YE" resample alias.
        return (1 + r).groupby(r.index.year).prod() - 1
    return (1 + r).resample("YE").prod() - 1


def _completed_annual(r: pd.Series, min_obs: int = 200) -> pd.Series:
    """Annual returns for complete years only.

    The final year of a backtest is usually partial. Including it in WorstYr /
    BestYr can make a nine-month stub look like a calendar-year result.
    """
    r = pd.Series(r).dropna()
    ann = annual_returns(r)
    counts = r.groupby(r.index.year).size()
    keep = [y for y in ann.index
            if int(counts.get(int(getattr(y, "year", y)), 0)) >= min_obs]
    return ann.loc[keep]


def downside_deviation(r: pd.Series, periods: int = 252) -> float:
    """Downside deviation relative to zero, the Sortino denominator."""
    r = pd.Series(r).dropna().astype(float)
    if not len(r):
        return np.nan
    return float(np.sqrt(np.mean(np.minimum(r, 0.0) ** 2)) * np.sqrt(periods))


def perf(r: pd.Series, rf: pd.Series | None = None, periods: int = 252) -> dict:
    """Return the standard metric block. rf adds excess-return columns."""
    r = pd.Series(r).dropna().astype(float)
    if len(r) < 2:
        return {}
    eq = (1 + r).cumprod()
    vol = float(r.std() * np.sqrt(periods))
    cagr = float(eq.iloc[-1] ** (periods / len(r)) - 1)
    sharpe = float(r.mean() / r.std() * np.sqrt(periods)) if r.std() > 0 else 0.0
    downside = downside_deviation(r, periods)
    sortino = float(r.mean() * periods / downside) if downside and downside > 0 else None
    maxdd = float((eq / eq.cummax() - 1).min())
    years = _completed_annual(r, 200)
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


def perf_m(m: pd.Series, rf_monthly: pd.Series | None = None,
           min_obs: int = 24) -> dict:
    """Monthly performance, annualised with 12 periods."""
    m = pd.Series(m).dropna().astype(float)
    if len(m) < min_obs:
        return {}
    eq = (1 + m).cumprod()
    vol = float(m.std() * np.sqrt(12.0))
    sharpe = float(m.mean() / m.std() * np.sqrt(12.0)) if m.std() > 0 else 0.0
    dn = downside_deviation(m, 12)
    sortino = float(m.mean() * 12.0 / dn) if dn and dn > 0 else None
    ann = annual_returns(m)
    counts = m.groupby(m.index.year).size()
    years = ann[[y for y in ann.index
                 if int(counts.get(int(getattr(y, "year", y)), 0)) >= 12]]
    out = {
        "CAGR": _round(eq.iloc[-1] ** (12.0 / len(m)) - 1),
        "Vol": _round(vol),
        "Sharpe": _round(sharpe, 3),
        "Sortino": _round(sortino, 3),
        "MaxDD": _round(float((eq / eq.cummax() - 1).min())),
        "WorstMonth": _round(float(m.min())),
        "WorstYear": _round(years.min()) if len(years) else None,
        "BestYear": _round(years.max()) if len(years) else None,
        "Total": _round(eq.iloc[-1] - 1, 2),
    }
    if rf_monthly is not None:
        rf = pd.Series(rf_monthly).reindex(m.index).ffill().fillna(0.0)
        ex = m - rf
        out["CAGR_excess_series"] = _round((1 + ex).cumprod().iloc[-1] ** (12.0 / len(m)) - 1)
        out["Sharpe_excess"] = _round(ex.mean() / ex.std() * np.sqrt(12.0), 3) if ex.std() > 0 else None
    return out


def bootstrap_sharpe(r: pd.Series, n_boot: int = 2000, block: int = 21,
                     periods: int = 252, seed: int = 7) -> dict:
    """Moving-block bootstrap confidence interval for the annualised Sharpe.

    A single backtest path is one draw. Blocks preserve some autocorrelation and
    volatility clustering; the interval is the honest way to show how much of the
    Sharpe is sampling noise.
    """
    r = pd.Series(r).dropna().astype(float).to_numpy()
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
        "sharpe": _round(float(pd.Series(r).mean() / pd.Series(r).std() * np.sqrt(periods)), 3),
        "ci_low": _round(float(lo), 3),
        "ci_high": _round(float(hi), 3),
        "p_sharpe_gt_0": _round(float((srs > 0).mean()), 3),
        "n_boot": int(n_boot),
        "block": int(block),
        "n_obs": int(n),
    }


def vol_target(r: pd.Series, target: float = 0.10, window: int = 60,
               max_leverage: float = 3.0) -> tuple[pd.Series, pd.Series]:
    """Scale a daily return series to a target annualised volatility.

    The scale uses information through t-1 only; it is applied to the return at t.
    """
    r = pd.Series(r).astype(float)
    rv = r.rolling(window).std() * np.sqrt(252.0)
    scale = (target / rv.shift(1)).clip(0.0, max_leverage).fillna(1.0)
    return r * scale, scale


def drawdown_control(r: pd.Series, maxdd: float = 0.20, floor: float = 0.0,
                     cost_bps: float = 5.0) -> pd.Series:
    """CPPI-style exposure cut as the drawdown deepens (no look-ahead).

    Changing the exposure multiplier is a trade: the overlay pays cost_bps per
    unit of exposure change. Pass cost_bps=0.0 for the gross comparison.
    """
    r = pd.Series(r).fillna(0.0)
    eq = 1.0
    peak = 1.0
    prev = 1.0
    out = []
    for x in r:
        dd = eq / peak - 1.0
        mult = float(np.clip(1.0 + dd / maxdd, floor, 1.0))
        trade = abs(mult - prev)
        rr = float(x) * mult - trade * cost_bps / 1e4
        prev = mult
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
