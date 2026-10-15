"""final.py - final artifacts: equity curves, annual returns, metrics."""
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
ret = px.pct_change(); M = 21

ts = sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs = np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1, pct=True)-0.5)
signal = 0.5*np.sign(ts)+0.5*xs
vol = ret.rolling(20).std()*np.sqrt(252.0)
raw = (signal/vol).replace([np.inf,-np.inf], np.nan).fillna(0.0)
w = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
w_d = w.resample("ME").last().reindex(w.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
gross = (w_d*ret).sum(axis=1).fillna(0.0)
rv = gross.rolling(60).std()*np.sqrt(252.0)
scale = (0.10/rv.shift(1)).clip(0,3).fillna(1.0)
ws = w_d.mul(scale, axis=0)
turn = ws.diff().abs().sum(axis=1).fillna(0.0)
strat = gross*scale - turn*(5.0/1e4)
spy = ret["SPY"].fillna(0.0)
sixty40 = 0.6*spy + 0.4*ret["IEF"].fillna(0.0)
combo = 0.7*sixty40 + 0.3*strat

def stats(r):
    r = r.dropna(); eq = (1+r).cumprod()
    cagr = eq.iloc[-1]**(252.0/len(r))-1; volr = r.std()*np.sqrt(252)
    return {"CAGR": round(float(cagr),4), "Vol": round(float(volr),4),
            "Sharpe": round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "MaxDD": round(float((eq/eq.cummax()-1).min()),4)}

ann = pd.DataFrame({"strategy": strat, "SPY": spy}).dropna()
ann_table = (1+ann).groupby(ann.index.year).prod()-1
print("annual returns (strategy vs SPY):")
print((ann_table*100).round(1).to_string())

eq = pd.DataFrame({"Strategy": (1+strat).cumprod(), "SPY": (1+spy).cumprod(),
                   "60/40": (1+sixty40).cumprod(), "60/40 + 30% strategy": (1+combo).cumprod()})
fig, ax = plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index, eq[c], lw=1.7, label=c)
ax.set_yscale("log"); ax.set_title("inercia strategy vs benchmarks (log scale)")
ax.set_ylabel("growth of $1"); ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_equity_final.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(10,4.5))
ax.bar(ann_table.index.astype(str), ann_table["strategy"]*100, color="#8e44ad", label="strategy")
for i, y in enumerate(ann_table.index):
    v = ann_table["strategy"].iloc[i]*100
fig, ax = plt.subplots(figsize=(11,4.5))
x = np.arange(len(ann_table.index)); wd = 0.4
ax.bar(x-wd/2, ann_table["strategy"]*100, wd, label="Strategy", color="#8e44ad")
ax.bar(x+wd/2, ann_table["SPY"]*100, wd, label="SPY", color="#2c3e50")
ax.set_xticks(x); ax.set_xticklabels(ann_table.index.astype(str), rotation=45)
ax.axhline(0, color="grey", lw=0.8); ax.set_ylabel("annual return %"); ax.legend()
ax.set_title("Annual returns: strategy vs SPY")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_annual.png")); plt.close(fig)

final = {"strategy": stats(strat), "spy": stats(spy), "sixty40": stats(sixty40),
         "combo_60_40_plus_30": stats(combo),
         "corr_strategy_spy": round(float(strat.corr(spy)),3),
         "annual_turnover": round(float(turn.mean()*252),1)}
json.dump(final, open(os.path.join(OUT,"final_metrics.json"),"w"), indent=2)
print(json.dumps(final, indent=2))
