"""vrp.py - the volatility risk premium, measured honestly.

Data: CBOE's own indices (VIX = 30-day implied; VIX3M = 3-month implied) plus SPY realized vol.
CBOE's VIX *futures* settlement files are not freely reachable, so the premium is measured the
academic way -- implied variance minus subsequently realized variance -- and the tradable sleeve
is the standard variance-swap P&L per unit of vega, (K^2 - RV^2) / (2K), in vol points.

  A. always-on short variance;
  B. contango-gated (only harvest when the VIX curve slopes up, VIX < VIX3M);
  C. the old crude SVXY proxy, for comparison.

Costs: 5 bps per month that the sleeve is on.  Position size: inverse trailing vol, walk-forward.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from engine import month_end_dates  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(ROOT, "output")
TARGET = 0.10
COST_M = 5.0 / 1e4
WIN = 24


def perf_m(m):
    m = pd.Series(m).dropna()
    if len(m) < 24:
        return {}
    eq = (1 + m).cumprod()
    years = len(m) / 12
    vol = float(m.std() * np.sqrt(12))
    dd = eq / eq.cummax() - 1
    ann = (1 + m).groupby(m.index.year).prod() - 1
    return dict(CAGR=round(float(eq.iloc[-1] ** (1 / years) - 1), 4), Vol=round(vol, 4),
                Sharpe=round(float(m.mean() * 12 / vol), 3) if vol > 0 else 0,
                MaxDD=round(float(dd.min()), 4), WorstMonth=round(float(m.min()), 4),
                WorstYear=round(float(ann.min()), 4), Total=round(float(eq.iloc[-1] - 1), 4))


def main():
    px = pd.read_csv(os.path.join(ROOT, "data", "raw", "prices.csv"), parse_dates=["Date"]).set_index("Date").sort_index()
    term = pd.read_csv(os.path.join(ROOT, "data", "raw", "cboe_vix_term.csv"), parse_dates=["Date"]).set_index("Date").sort_index()

    spy = px["SPY"]
    logret = np.log(spy / spy.shift(1)).dropna()
    me = month_end_dates(spy.index)

    per = logret.index.to_period("M")
    rv = logret.groupby(per).apply(lambda s: float(np.sqrt((s ** 2).mean() * 252)) * 100)
    rv.index = rv.index.to_timestamp(how="end").normalize()

    vix = term["vix"].reindex(spy.index).ffill()
    vix3m = term["vix3m"].reindex(spy.index).ffill()
    df = pd.DataFrame({"K": vix.reindex(me).shift(1), "K3": vix3m.reindex(me).shift(1),
                       "RV": rv.reindex(me)}).dropna(subset=["K", "RV"])
    df["pnl"] = (df["K"] ** 2 - df["RV"] ** 2) / (2 * df["K"])          # vol points per unit vega
    df["contango"] = df["K3"].notna() & (df["K"] < df["K3"])

    # inverse-vol sizing, walk-forward (scale known at month start)
    vol_ann = df["pnl"].rolling(WIN).std() * np.sqrt(12)
    df["scale"] = (TARGET / vol_ann.replace(0, np.nan)).clip(upper=4.0).shift(1).fillna(0.0)

    on_a = df["scale"] > 0
    on_b = on_a & df["contango"]
    a_net = (df["pnl"] * df["scale"] - COST_M * on_a.astype(float))
    b_net = (df["pnl"].where(df["contango"], 0.0) * df["scale"] - COST_M * on_b.astype(float))

    rep = {"vix3m_from": str(vix3m.dropna().index[0].date()),
           "window": [str(df.index[0].date()), str(df.index[-1].date())], "n_months": int(len(df)),
           "premium": {"mean_implied_vol": round(float(df["K"].mean()), 2),
                       "mean_realized_vol": round(float(df["RV"].mean()), 2),
                       "mean_pnl_vol_points": round(float(df["pnl"].mean()), 3),
                       "pct_months_implied_gt_realized": round(float((df["K"] > df["RV"]).mean()), 3)},
           "contango_fraction": round(float(df["contango"].mean()), 3),
           "A_always_on": perf_m(a_net),
           "B_contango_gated": perf_m(b_net)}

    # apples-to-apples: only where the term structure exists (B can trade)
    common = df.index[df["contango"] | ~df["K3"].isna()]
    rep["common_window"] = [str(common[0].date()), str(common[-1].date())]
    rep["A_common_window"] = perf_m(a_net.reindex(common))
    rep["B_common_window"] = perf_m(b_net.reindex(common))

    if "SVXY" in px.columns:
        sv = px["SVXY"].resample("ME").last().pct_change().dropna()
        sv = sv.reindex(common).dropna()
        sv_scale = (TARGET / (sv.rolling(WIN).std() * np.sqrt(12)).replace(0, np.nan)).clip(upper=4).shift(1).fillna(0.0)
        c_net = sv * sv_scale - COST_M * (sv_scale > 0).astype(float)
        rep["C_svxy_proxy_common_window"] = perf_m(c_net)

    m_px = px[["SPY", "IEF"]].resample("ME").last().pct_change().reindex(common).dropna()
    bench = 0.6 * m_px["SPY"] + 0.4 * m_px["IEF"]
    rep["SPY_common"] = perf_m(m_px["SPY"])
    rep["60_40_common"] = perf_m(bench)
    for name, s in (("A_always_on", a_net), ("B_contango_gated", b_net)):
        rep[f"60/40+30 {name}"] = perf_m(0.7 * bench + 0.3 * s.reindex(bench.index).fillna(0.0))

    crisis = {}
    for d in ["2008-10-31", "2018-02-28", "2020-03-31"]:
        ts = pd.Timestamp(d)
        if ts in df.index:
            crisis[d] = {"A": round(float(a_net.get(ts, np.nan)), 4),
                         "B": round(float(b_net.get(ts, np.nan)), 4),
                         "SPY": round(float(m_px["SPY"].get(ts, np.nan)), 4)}
    rep["crisis_months"] = crisis

    with open(os.path.join(OUT, "vrp_metrics.json"), "w") as f:
        json.dump(rep, f, indent=2)

    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 6))
    for name, s in (("A always-on", a_net.reindex(common)), ("B contango-gated", b_net.reindex(common)),
                    ("SPY", m_px["SPY"]), ("60/40", bench)):
        ax.plot((1 + s.fillna(0)).cumprod(), label=f"{name} (Sharpe {perf_m(s).get('Sharpe')})")
    ax.set_yscale("log"); ax.legend(); ax.set_title("cartograf - volatility risk premium (common window)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "07_vrp.png"), dpi=110); plt.close(fig)

    print(json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
