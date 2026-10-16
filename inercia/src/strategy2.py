"""strategy2.py - test design variants to find a robust configuration."""
import os, json, itertools
import numpy as np, pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "prices")
OUT = os.path.join(BASE, "output")

def load(t):
    d = pd.read_csv(os.path.join(RAW, f"{t}.csv"))
    dc = [c for c in d.columns if c.lower() == "date"][0]
    d[dc] = pd.to_datetime(d[dc]); d = d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"], errors="coerce")

tickers = sorted(f[:-4] for f in os.listdir(RAW) if f.endswith(".csv"))
px = pd.DataFrame({t: load(t) for t in tickers}).sort_index()
ret = px.pct_change()
M = 21
CLASS = {"equity": ["SPY","EFA","EEM","EWJ","EWU","EWG","EWC","XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY"],
         "bond": ["TLT","IEF","SHY","LQD","HYG","TIP"],
         "commodity": ["GLD","SLV","DBC","USO"],
         "other": ["VNQ","FXE","FXY","UUP"]}

def stats(r):
    r = r.dropna()
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (252.0 / len(r)) - 1
    vol = r.std() * np.sqrt(252)
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() else 0
    dd = (eq / eq.cummax() - 1).min()
    return {"CAGR": round(float(cagr),4), "Vol": round(float(vol),4), "Sharpe": round(float(sharpe),3),
            "MaxDD": round(float(dd),4), "Total": round(float(eq.iloc[-1]-1),2)}

def run(freq="ME", use_xs=True, class_bal=False, target_vol=0.10, cost_bps=5.0, vol_window=60):
    ts = sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
    xs = np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1, pct=True)-0.5)
    signal = 0.5*np.sign(ts)+0.5*xs if use_xs else np.sign(ts)
    vol = ret.rolling(20).std()*np.sqrt(252.0)
    raw = (signal/vol).replace([np.inf,-np.inf], np.nan).fillna(0.0)
    if class_bal:
        w = pd.DataFrame(0.0, index=raw.index, columns=raw.columns)
        for cl, mem in CLASS.items():
            mem = [m for m in mem if m in raw.columns]
            sub = raw[mem]
            g = sub.abs().sum(axis=1).replace(0, np.nan)
            w[mem] = sub.div(g, axis=0).fillna(0.0) / len(CLASS)
    else:
        g = raw.abs().sum(axis=1).replace(0, np.nan)
        w = raw.div(g, axis=0).fillna(0.0)
    w_m = w.resample(freq).last()
    w_d = w_m.reindex(w.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
    gross = (w_d*ret).sum(axis=1).fillna(0.0)
    rv = gross.rolling(vol_window).std()*np.sqrt(252.0)
    scale = (target_vol/rv.shift(1)).clip(0,3).fillna(1.0)
    ws = w_d.mul(scale, axis=0)
    turn = ws.diff().abs().sum(axis=1).fillna(0.0)
    net = gross*scale - turn*(cost_bps/1e4)
    d = stats(net); d["turnover"] = round(float(turn.mean()*252),1)
    d["corr_spy"] = round(float(net.corr(ret["SPY"].fillna(0))),3)
    return d

variants = {}
for freq in ["ME","QE"]:
    for use_xs in [False, True]:
        for cb in [False, True]:
            key = f"freq={freq} xs={use_xs} classbal={cb}"
            variants[key] = run(freq=freq, use_xs=use_xs, class_bal=cb)

# print sorted by Sharpe
for k, v in sorted(variants.items(), key=lambda x: -x[1]["Sharpe"]):
    print(f"{v['Sharpe']:.3f}  Sharpe | CAGR {v['CAGR']*100:5.2f}% | Vol {v['Vol']*100:5.1f}% | MaxDD {v['MaxDD']*100:6.1f}% | turn {v['turnover']:5.1f} | corrSPY {v['corr_spy']:5.2f} | {k}")

with open(os.path.join(OUT, "variants.json"), "w") as f:
    json.dump(variants, f, indent=2)
