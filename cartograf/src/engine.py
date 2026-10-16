"""engine.py - backtest plumbing shared by every sleeve.

Rule that never bends: a signal computed from data up to a month-end is applied only
from the NEXT trading day. Nothing in this file looks forward.
"""
import numpy as np
import pandas as pd

TD = 252


def month_end_dates(idx):
    """Last trading day of each month, in order."""
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(sorted(s.groupby([idx.year, idx.month]).max().values))


def weights_to_returns(R, targets, cost_bps=5.0):
    """R: daily simple returns (T x N).  targets: DataFrame indexed by rebalance dates.

    Returns (net_daily, turnover_sum, gross_daily).  Weights are held constant between
    rebalances and the cost is charged on the day the new book is applied.
    """
    tgt = targets.reindex(columns=R.columns).fillna(0.0)
    W = tgt.reindex(R.index).ffill().shift(1).fillna(0.0)
    gross = (W * R).sum(axis=1)

    delta = tgt.diff()
    if len(tgt):
        delta.iloc[0] = tgt.iloc[0]
    to = delta.abs().sum(axis=1)

    cost = pd.Series(0.0, index=R.index)
    for d, c in to.items():
        pos = R.index.searchsorted(d, side="right")
        if pos < len(R.index):
            cost.iloc[pos] += c * cost_bps / 1e4
    return gross - cost, float(to.sum()), gross


def perf(daily, rf=0.0):
    d = pd.Series(daily).dropna()
    if len(d) < 40:
        return {}
    eq = (1 + d).cumprod()
    years = len(d) / TD
    cagr = eq.iloc[-1] ** (1 / years) - 1
    vol = d.std() * np.sqrt(TD)
    sharpe = (d.mean() * TD - rf) / vol if vol > 0 else 0.0
    dn = d[d < 0].std() * np.sqrt(TD)
    sortino = (d.mean() * TD) / dn if dn and dn > 0 else 0.0
    dd = eq / eq.cummax() - 1
    ann = (1 + d).groupby(d.index.year).prod() - 1
    return dict(CAGR=round(float(cagr), 4), Vol=round(float(vol), 4),
                Sharpe=round(float(sharpe), 3), Sortino=round(float(sortino), 3),
                MaxDD=round(float(dd.min()), 4), Total=round(float(eq.iloc[-1] - 1), 4),
                WorstYear=round(float(ann.min()), 4), BestYear=round(float(ann.max()), 4))


def scale_weights_to_target(w_targets, R, target=0.10, win=63, cap=4.0, eps=0.02):
    """Scale each rebalance's target weights so the ex-ante portfolio vol equals target.

    The covariance comes from the trailing `win` days of returns *up to and including*
    the rebalance date -- no lookahead.  This is the honest way to hit a vol target:
    the weights (and therefore the trading costs) are real, not post-hoc rescaled.
    """
    out = w_targets.copy().astype(float)
    idx = R.index
    for d in w_targets.index:
        pos = idx.searchsorted(d, side="right")
        hist = R.iloc[max(0, pos - win):pos]
        w = w_targets.loc[d].reindex(R.columns).fillna(0.0)
        if len(hist) < 20 or float(w.abs().sum()) < eps:
            out.loc[d] = w
            continue
        cov = hist.cov().reindex(index=R.columns, columns=R.columns).fillna(0.0)
        var = float(w.values @ cov.values @ w.values)
        volp = (var ** 0.5) * (TD ** 0.5) if var > 0 else 0.0
        scale = min(target / volp, cap) if volp > 1e-6 else 1.0
        out.loc[d] = w * scale
    return out


def vol_target(daily, target=0.10, win=63, cap=4.0):
    """Scale a daily return stream to a target vol, using only trailing data."""
    d = pd.Series(daily).fillna(0.0)
    vol = d.rolling(win).std() * np.sqrt(TD)
    scale = (target / vol.replace(0, np.nan)).clip(upper=cap).shift(1).fillna(0.0)
    return d * scale, scale


def drawdown(s):
    eq = (1 + pd.Series(s).fillna(0)).cumprod()
    return eq / eq.cummax() - 1, eq


# --- Hierarchical Risk Parity (Lopez de Prado, 2016) -------------------------
def _get_ivp(cov):
    ivp = 1.0 / np.diag(cov)
    return ivp / ivp.sum()


def _cluster_var(cov, items):
    c = cov.loc[items, items]
    ivp = _get_ivp(c)
    return float(ivp @ c.values @ ivp)


def _quasi_diag(link):
    link = link.astype(int)
    sort_ix = pd.Series([link[-1, 0], link[-1, 1]])
    n = link[-1, 3]
    while sort_ix.max() >= n:
        sort_ix.index = range(0, sort_ix.shape[0] * 2, 2)
        df0 = sort_ix[sort_ix >= n]
        i, j = df0.index, df0.values - n
        sort_ix[i] = link[j, 0]
        df0 = pd.Series(link[j, 1], index=i + 1)
        sort_ix = pd.concat([sort_ix, df0]).sort_index()
        sort_ix.index = range(sort_ix.shape[0])
    return sort_ix.tolist()


def _cluster_weights(cov, sort_ix):
    w = pd.Series(1.0, index=sort_ix)
    clusters = [sort_ix]
    while clusters:
        clusters = [c[i:j] for c in clusters for i, j in ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            left, right = clusters[i], clusters[i + 1]
            v_left, v_right = _cluster_var(cov, left), _cluster_var(cov, right)
            alpha = 1 - v_left / (v_left + v_right)
            w[left] *= alpha
            w[right] *= 1 - alpha
    return w


def hrp_weights(returns, method="single"):
    """returns: DataFrame of asset returns (rows = periods). Returns weight Series."""
    from scipy.cluster.hierarchy import linkage
    from scipy.spatial.distance import squareform
    x = returns.dropna(axis=1, how="any")
    if x.shape[1] < 2:
        return pd.Series(1.0, index=returns.columns)
    corr = x.corr().fillna(0.0)
    cov = x.cov()
    dist = ((1 - corr) / 2.0) ** 0.5
    link = linkage(squareform(dist.values, checks=False), method=method)
    sort_ix = _quasi_diag(link)
    names = [corr.columns[i] for i in sort_ix]
    w = _cluster_weights(cov, names)
    return w.reindex(returns.columns).fillna(0.0)
