"""Backtest plumbing: rebalance, lag, costs, vol targeting, HRP."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .config import TD


def month_end_dates(idx) -> pd.DatetimeIndex:
    s = pd.Series(idx, index=idx)
    return pd.DatetimeIndex(sorted(s.groupby([idx.year, idx.month]).max().values))


def weights_to_returns(R: pd.DataFrame, targets: pd.DataFrame,
                       cost_bps: float = 5.0):
    """Apply target weights from the next trading day and charge turnover costs.

    The target is indexed by rebalance date. It is forward-filled, shifted one
    day, and only then multiplied by returns. Costs are charged on the day the
    new book is applied, not on the signal date.
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


def turnover_annual(turnover_sum: float, n_days: int) -> float:
    return round(float(turnover_sum) / (n_days / TD), 2)


def scale_weights_to_target(w_targets: pd.DataFrame, R: pd.DataFrame,
                            target: float = 0.10, win: int = 63,
                            cap: float = 4.0, eps: float = 0.02) -> pd.DataFrame:
    """Scale each rebalance's weights so ex-ante portfolio vol equals target.

    Covariance uses the trailing win days *before* the rebalance date. The
    resulting weights are what you would actually hold, so turnover and costs
    are real.
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


# --- Hierarchical Risk Parity (Lopez de Prado, 2016) -------------------------
def _get_ivp(cov):
    # A sleeve that is flat because its instruments do not exist yet has zero
    # variance. 1/0 would poison the HRP recursion, so give that sleeve zero
    # inverse-variance weight and normalise over the live ones.
    d = np.diag(np.asarray(cov, dtype=float))
    ivp = np.zeros_like(d)
    positive = d > 0
    ivp[positive] = 1.0 / d[positive]
    total = float(ivp.sum())
    return ivp / total if total > 0 else np.zeros_like(ivp)


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
        clusters = [c[i:j] for c in clusters for i, j in
                    ((0, len(c) // 2), (len(c) // 2, len(c))) if len(c) > 1]
        for i in range(0, len(clusters), 2):
            left, right = clusters[i], clusters[i + 1]
            v_left, v_right = _cluster_var(cov, left), _cluster_var(cov, right)
            alpha = 1 - v_left / (v_left + v_right)
            w[left] *= alpha
            w[right] *= 1 - alpha
    return w


def hrp_weights(returns: pd.DataFrame, method: str = "single") -> pd.Series:
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
