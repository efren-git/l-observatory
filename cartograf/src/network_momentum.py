"""network_momentum.py - does 'momentum spillover' add anything to plain trend?

A reduced, faithful version of arXiv 2501.07135 ("Follow the Leader"): estimate a directed
lead-lag network from trailing weekly returns, then blend each market's own trend signal with
the trend signals of the markets that tend to LEAD it.

Honest question: does the network version beat the plain trend sleeve -- or is it noise dressed
up as structure?
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from fetch_data import UNIVERSE  # noqa: E402
from engine import (month_end_dates, weights_to_returns, perf,  # noqa: E402
                    scale_weights_to_target, drawdown)
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(ROOT, "output")
START = "2008-01-01"
COST = 5.0
TARGET = 0.10
WIN_W = 156   # 3 years of weekly returns to estimate the network
TOP_K = 5     # each market follows its 5 strongest leaders


def main():
    px = pd.read_csv(os.path.join(ROOT, "data", "raw", "prices.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    tradable = [t for t in UNIVERSE if t in px.columns and UNIVERSE[t] != "vol"]
    px = px[tradable]
    R = px.pct_change().fillna(0.0)
    me = month_end_dates(R.index)
    me = me[me >= pd.Timestamp(START)]

    wk = px.resample("W-FRI").last().pct_change()
    trend = sum(np.sign(px / px.shift(h) - 1) for h in (21, 63, 126, 252)) / 4.0
    vol = R.rolling(63).std() * np.sqrt(252)
    volm = vol.reindex(me)
    cols = list(tradable)

    own_rows, net_rows, comb_rows = [], [], []
    edge_stats = []
    for d in me:
        t = trend.loc[d].reindex(cols)
        hist = wk.loc[:d].tail(WIN_W + 1)
        if len(hist) >= 60:
            Z = ((hist - hist.mean()) / hist.std()).fillna(0.0)
            A = Z.values
            M = (A[:-1].T @ A[1:]) / (len(A) - 1)      # M[j, i] = corr(r_j[t], r_i[t+1])
            M = np.nan_to_num(M)
            np.fill_diagonal(M, 0.0)
        else:
            M = np.zeros((len(cols), len(cols)))
        lead = pd.DataFrame(M, index=cols, columns=cols)
        nt = pd.Series(0.0, index=cols)
        kept = []
        for ci in cols:
            col = lead[ci]
            col = col[col > 0].nlargest(TOP_K)
            if len(col):
                w = col / col.sum()
                nt[ci] = float((w * t.reindex(col.index).fillna(0.0)).sum())
                kept.append(float(col.mean()))
        own = t.fillna(0.0)
        own_rows.append(own)
        net_rows.append(nt)
        comb_rows.append(0.5 * own + 0.5 * nt)
        if kept:
            edge_stats.append(float(np.mean(kept)))

    def build(rows, cost=COST, tag=""):
        w = pd.DataFrame(rows, index=me).reindex(columns=cols).fillna(0.0)
        w = w * (TARGET / volm.reindex(columns=cols).clip(lower=0.05)).fillna(0.0)
        w = scale_weights_to_target(w, R, TARGET)
        net, to, _ = weights_to_returns(R, w, cost)
        return net, to

    own_ret, own_to = build(own_rows, tag="own")
    net_ret, net_to = build(net_rows, tag="net")
    comb_ret, comb_to = build(comb_rows, tag="comb")

    spy = R["SPY"]
    rep = {
        "window": [str(me[0].date()), str(me[-1].date())],
        "params": {"window_weeks": WIN_W, "top_k": TOP_K, "blend": 0.5},
        "avg_lead_corr_kept": round(float(np.mean(edge_stats)), 4) if edge_stats else None,
        "trend_only": perf(own_ret), "network_only": perf(net_ret), "trend_plus_network": perf(comb_ret),
        "SPY": perf(spy.reindex(own_ret.index)),
        "corr_own_vs_net": round(float(own_ret.corr(net_ret)), 3),
        "corr_comb_vs_spy": round(float(comb_ret.corr(spy.reindex(comb_ret.index))), 3),
        "turnover": {"own": round(own_to / (len(R) / 252), 2),
                     "net": round(net_to / (len(R) / 252), 2),
                     "comb": round(comb_to / (len(R) / 252), 2)},
    }
    # does the blend lift a 60/40 more than plain trend does?
    bench = (0.6 * R["SPY"] + 0.4 * R["IEF"]).reindex(own_ret.index)
    for name, s in (("trend_only", own_ret), ("trend+network", comb_ret)):
        rep[f"60/40+30 {name}"] = perf(0.7 * bench + 0.3 * s)

    with open(os.path.join(OUT, "network_metrics.json"), "w") as f:
        json.dump(rep, f, indent=2)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 6))
    for name, s in (("trend only", own_ret), ("network only", net_ret),
                    ("trend + network", comb_ret), ("SPY", spy)):
        ax.plot((1 + s.fillna(0)).cumprod(), label=f"{name} (Sharpe {perf(s).get('Sharpe')})")
    ax.set_yscale("log"); ax.legend(); ax.set_title("cartograf - network momentum vs plain trend")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "06_network.png"), dpi=110); plt.close(fig)

    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
