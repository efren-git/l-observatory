"""carry.py - cross-asset carry, done properly.

Carry (Koijen, Moskowitz, Pedersen & Vrugt 2018) is *the return to an asset if its price does
not change*: the interest you earn, the dividend you collect, the yield above cash.

Three asset classes, each ranked cross-sectionally (long the highest carry, short the lowest):

  bonds   carry = Treasury yield at the ETF's tenor  minus  3-month cash
  equities carry = trailing dividend yield            minus  3-month cash
  FX      carry = foreign 3-month rate                minus  US 3-month rate

Commodity carry needs futures curves, which are not freely available -- so it is NOT tested here
rather than approximated badly.

Data: FRED (Treasury curve + G10 3-month rates), Yahoo dividends (via yfinance), Yahoo prices.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from engine import (month_end_dates, weights_to_returns, perf,  # noqa: E402
                    scale_weights_to_target, vol_target, drawdown)
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(ROOT, "output")
START = "2007-01-01"
COST = 5.0
TARGET = 0.10

BOND_TENOR = {"SHY": "dgs2", "IEF": "dgs7", "TLT": "dgs30"}
FX_MAP = {"FXE": "fx_eur", "FXY": "fx_jpy", "FXB": "fx_gbp",
          "FXA": "fx_aud", "FXC": "fx_cad", "FXF": "fx_chf"}
EQ = ["SPY", "QQQ", "IWM", "EFA", "EEM", "IWD", "IWF", "USMV", "SPLV",
      "QUAL", "MTUM", "SPHB", "VNQ", "RWX"]


def z_weights(score, cols):
    """Cross-sectional carry weights: proportional to the demeaned score, gross exposure 1."""
    s = pd.Series(score).reindex(cols).dropna()
    if len(s) < 2:
        return pd.Series(0.0, index=cols)
    z = s - s.mean()
    denom = float(z.abs().sum())
    if denom <= 0:
        return pd.Series(0.0, index=cols)
    return (z / denom).reindex(cols).fillna(0.0)


def main():
    px = pd.read_csv(os.path.join(ROOT, "data", "raw", "prices.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    fr = pd.read_csv(os.path.join(ROOT, "data", "raw", "fred_carry.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    div = pd.read_csv(os.path.join(ROOT, "data", "raw", "dividends.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    R = px.pct_change().fillna(0.0)
    me = month_end_dates(R.index)
    me = me[me >= pd.Timestamp(START)]
    frd = fr.reindex(R.index).ffill()

    # trailing-12m dividends per share, then dividend yield at each month end
    div_m = div.resample("ME").sum()
    trail = div_m.rolling(12).sum()
    eq_cols = [c for c in EQ if c in px.columns]
    dyield = (trail.reindex(me, method="ffill").div(px[eq_cols].reindex(me).replace(0, np.nan)) * 100.0)

    bond_cols = [c for c in BOND_TENOR if c in px.columns]
    fx_cols = [c for c in FX_MAP if c in px.columns]

    wb, we, wf = [], [], []
    cash = frd["dgs3mo"].reindex(me)
    for d in me:
        c = cash.loc[d]
        # bonds: yield at tenor minus cash
        yb = {t: frd[BOND_TENOR[t]].loc[d] - c for t in bond_cols}
        wb.append(z_weights(yb, bond_cols))
        # equities: dividend yield minus cash
        ye = (dyield.loc[d] - c).to_dict()
        we.append(z_weights(ye, eq_cols))
        # fx: foreign 3m minus US 3m
        yf = {t: frd[FX_MAP[t]].loc[d] - frd["fx_usd"].loc[d] for t in fx_cols}
        wf.append(z_weights(yf, fx_cols))

    def book(rows, cols, rets, cost=COST):
        w = pd.DataFrame(rows, index=me).reindex(columns=cols).fillna(0.0)
        w = scale_weights_to_target(w, rets, TARGET)
        net, to, _ = weights_to_returns(rets, w, cost)
        return net, to

    Rfx = R[fx_cols].sub(frd["fx_usd"].reindex(R.index).ffill() / 1200.0, axis=0)  # funding cancels in a zero-sum book
    bond_ret, bond_to = book(wb, bond_cols, R)
    eq_ret, eq_to = book(we, eq_cols, R)
    fx_ret, fx_to = book(wf, fx_cols, Rfx)

    combined = pd.DataFrame({"bond_carry": bond_ret, "equity_carry": eq_ret, "fx_carry": fx_ret})
    combined = combined.loc[combined.index >= pd.Timestamp("2007-01-01")]  # all classes live
    mix = combined.mean(axis=1)
    carry_book = vol_target(mix, TARGET)[0]

    spy = R["SPY"].reindex(combined.index)
    bench = (0.6 * R["SPY"] + 0.4 * R["IEF"]).reindex(combined.index)

    rep = {"window": [str(combined.index[0].date()), str(combined.index[-1].date())],
           "turnover_x_yr": {"bond": round(bond_to / (len(R) / 252), 2),
                             "equity": round(eq_to / (len(R) / 252), 2),
                             "fx": round(fx_to / (len(R) / 252), 2)},
           "sleeves": {"bond_carry": perf(bond_ret), "equity_carry": perf(eq_ret),
                       "fx_carry": perf(fx_ret), "carry_book": perf(carry_book)},
           "corr": {"carry_vs_spy": round(float(carry_book.corr(spy)), 3),
                    "carry_vs_6040": round(float(carry_book.corr(bench)), 3),
                    "bond_vs_fx": round(float(bond_ret.corr(fx_ret)), 3),
                    "bond_vs_eq": round(float(bond_ret.corr(eq_ret)), 3),
                    "eq_vs_fx": round(float(eq_ret.corr(fx_ret)), 3)},
           "benchmarks": {"SPY": perf(spy), "60/40": perf(bench)}}
    for frac in (0.2, 0.3):
        rep[f"60/40+{int(frac*100)} carry"] = perf((1 - frac) * bench + frac * carry_book)
    rep["annual"] = {k: (1 + v).groupby(v.index.year).prod().sub(1).round(4).to_dict()
                     for k, v in (("carry", carry_book), ("SPY", spy))}

    with open(os.path.join(OUT, "carry_metrics.json"), "w") as f:
        json.dump(rep, f, indent=2)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 6))
    for name, s in (("carry book", carry_book), ("bond carry", bond_ret),
                    ("equity carry", eq_ret), ("fx carry", fx_ret), ("SPY", spy),
                    ("60/40", bench)):
        ax.plot((1 + s.fillna(0)).cumprod(), label=f"{name} (Sharpe {perf(s).get('Sharpe')})")
    ax.set_yscale("log"); ax.legend(); ax.set_title("cartograf - cross-asset carry")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "08_carry.png"), dpi=110); plt.close(fig)

    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
