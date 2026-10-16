"""strategy3.py - risk-allocation variants + diversification value."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

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

CLASS = {}
for t in ["SPY","IWM","MDY","XLB","XLE","XLF","XLI","XLK","XLP","XLU","XLV","XLY","SMH","KRE","XBI","XRT","XOP","XME","ITB","IYT","XHB","EFA","EEM","EWJ","EWU","EWG","EWC","EWA","EWH","EWS","EWT","EWY","EWZ","EWW","EWM","EWP","EWL","EWD","EWI","EWO","EWN","EZA","FXI","INDA"]:
    CLASS[t] = "equity"
for t in ["TLT","IEF","SHY","LQD","HYG","TIP","EMB"]: CLASS[t] = "bond"
for t in ["GLD","SLV","DBC","USO","DBA"]: CLASS[t] = "commodity"
for t in ["VNQ","IYR"]: CLASS[t] = "reit"
for t in ["FXE","FXY","FXB","FXC","UUP"]: CLASS[t] = "fx"
nsize = {t: sum(1 for x in tickers if CLASS.get(x) == CLASS.get(t)) for t in tickers}

def stats(r):
    r = r.dropna(); eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (252.0/len(r)) - 1
    vol = r.std()*np.sqrt(252)
    sharpe = r.mean()/r.std()*np.sqrt(252) if r.std() else 0
    dd = (eq/eq.cummax()-1).min()
    return {"CAGR": round(float(cagr),4), "Vol": round(float(vol),4), "Sharpe": round(float(sharpe),3),
            "MaxDD": round(float(dd),4), "Total": round(float(eq.iloc[-1]-1),2)}

def run(weighting="gross", use_xs=True, target_vol=0.10, cost_bps=5.0, freq="ME"):
    ts = sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
    xs = np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1, pct=True)-0.5)
    signal = 0.5*np.sign(ts)+0.5*xs if use_xs else np.sign(ts)
    vol = ret.rolling(20).std()*np.sqrt(252.0)
    raw = (signal/vol).replace([np.inf,-np.inf], np.nan).fillna(0.0)
    if weighting == "class":
        for t in raw.columns:
            raw[t] = raw[t] / nsize.get(t, 1)
    g = raw.abs().sum(axis=1).replace(0, np.nan)
    w = raw.div(g, axis=0).fillna(0.0)
    w_d = w.resample(freq).last().reindex(w.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
    gross = (w_d*ret).sum(axis=1).fillna(0.0)
    rv = gross.rolling(60).std()*np.sqrt(252.0)
    scale = (target_vol/rv.shift(1)).clip(0,3).fillna(1.0)
    ws = w_d.mul(scale, axis=0)
    turn = ws.diff().abs().sum(axis=1).fillna(0.0)
    net = gross*scale - turn*(cost_bps/1e4)
    d = stats(net); d["turnover"] = round(float(turn.mean()*252),1); d["corr_spy"] = round(float(net.corr(ret["SPY"].fillna(0))),3)
    return net, d

res = {}
best = {}
for wname in ["gross","class"]:
    for xs in [False, True]:
        net, d = run(weighting=wname, use_xs=xs)
        key = f"w={wname} xs={xs}"
        res[key] = d; best[key] = net
        print(f"{d['Sharpe']:.3f} | CAGR {d['CAGR']*100:5.2f}% | Vol {d['Vol']*100:4.1f}% | MaxDD {d['MaxDD']*100:6.1f}% | turn {d['turnover']:5.1f} | corr {d['corr_spy']:5.2f} | {key}")

# pick the best and show the diversification value vs 60/40
bestkey = max(res, key=lambda k: res[k]["Sharpe"])
net = best[bestkey]
spy = ret["SPY"].fillna(0.0); ief = ret["IEF"].fillna(0.0)
sixty40 = 0.6*spy + 0.4*ief
for w_trend in [0.0, 0.2, 0.3, 0.4]:
    combo = (1-w_trend)*sixty40 + w_trend*net
    res[f"combo_60_40_plus_{int(w_trend*100)}trend"] = stats(combo)
print("best:", bestkey)
print(json.dumps({k: res[k] for k in res if k.startswith("combo")}, indent=2))

with open(os.path.join(OUT, "riskalloc.json"), "w") as f:
    json.dump({"variants": res, "best": bestkey}, f, indent=2)
