"""combo.py - three engines (trend, carry, reversal) + optimal combination."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw"); OUT = os.path.join(BASE, "output")
M = 21

def stats(r):
    r = r.dropna(); eq = (1+r).cumprod()
    cagr = eq.iloc[-1]**(252.0/len(r))-1; vol = r.std()*np.sqrt(252)
    return {"CAGR": round(float(cagr),4), "Vol": round(float(vol),4),
            "Sharpe": round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "MaxDD": round(float((eq/eq.cummax()-1).min()),4)}

def vt(r, target=0.10):
    return r/r.std()*target/np.sqrt(252)

def port(signal, ret, volw, rebal="ME"):
    vol = volw
    raw = (signal/vol).replace([np.inf,-np.inf], np.nan).fillna(0.0)
    w = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
    w_d = w.resample(rebal).last().reindex(w.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
    g = (w_d*ret).sum(axis=1).fillna(0.0)
    rv = g.rolling(60).std()*np.sqrt(252.0)
    s = (0.10/rv.shift(1)).clip(0,3).fillna(1.0)
    ws = w_d.mul(s, axis=0)
    turn = ws.diff().abs().sum(axis=1).fillna(0.0)
    return g*s - turn*(5.0/1e4)

# ---- prices (equity/asset ETFs) ----
def loadp(folder, t):
    d = pd.read_csv(os.path.join(RAW, folder, f"{t}.csv"))
    dc = [c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"], errors="coerce")
tk = sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
px = pd.DataFrame({t: loadp("prices",t) for t in tk}).sort_index(); pret = px.pct_change()
volp = pret.rolling(20).std()*np.sqrt(252.0)

# trend
ts = sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs = np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
trend = port(0.5*np.sign(ts)+0.5*xs, pret, volp)

# reversal (short-term): long losers, short winners
rev_sig = -np.sign((px/px.shift(M)-1).rank(axis=1,pct=True)-0.5)
rev = port(rev_sig, pret, volp)

# ---- carry ----
def fred_rate(k):
    d = pd.read_csv(os.path.join(RAW,"fred",f"rate_{k}.csv")); d.columns=["date","value"]
    d["date"]=pd.to_datetime(d["date"]); d["value"]=pd.to_numeric(d["value"],errors="coerce")
    return d.dropna().set_index("date")["value"]
def fxs(k, inv=False):
    d = pd.read_csv(os.path.join(RAW,"fx",f"{k}.csv"))
    dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    s=pd.to_numeric(d["Close"],errors="coerce")
    return (1/s) if inv else s
CUR={"EUR":False,"JPY":True,"GBP":False,"CAD":True,"AUD":False,"CHF":True,"NZD":False,"SEK":True,"NOK":True}
RATEKEY={"EUR":"EU","JPY":"JP","GBP":"UK","CAD":"CA","AUD":"AU","CHF":"CH","NZD":"NZ","SEK":"SE","NOK":"NO"}
S=pd.DataFrame({c: fxs(c,i) for c,i in CUR.items()}).sort_index(); fxret=S.pct_change()
usd=fred_rate("US").resample("MS").last()
rates=pd.DataFrame({c: fred_rate(RATEKEY[c]).resample("MS").last() for c in CUR})
carryd=rates.reindex(fxret.index,method="ffill").sub(usd.reindex(fxret.index,method="ffill"),axis=0)
totret=fxret.add(carryd/100.0/252.0, fill_value=0.0)
volc=totret.rolling(60).std()*np.sqrt(252.0)
zc=carryd.sub(carryd.mean(axis=1),axis=0).div(carryd.std(axis=1),axis=0)
carry = port(zc, totret, volc)

# ---- combine ----
df = pd.DataFrame({"trend": trend, "carry": carry, "reversal": rev}).dropna()
res = {"trend": stats(df["trend"]), "carry": stats(df["carry"]), "reversal": stats(df["reversal"])}
res["corr"] = df.corr().round(3).to_dict()

# equal-risk (vol-matched) combo
eq3 = vt(df["trend"])/3 + vt(df["carry"])/3 + vt(df["reversal"])/3
res["combo_equal_3"] = stats(eq3)

# max-Sharpe (tangency) weights, in-sample (caveated)
mu = df.mean().values; cov = df.cov().values
w_tan = np.linalg.solve(cov, mu); w_tan = w_tan/w_tan.sum()
tan = df.values @ w_tan
res["combo_tangency"] = stats(pd.Series(tan, index=df.index))
res["tangency_weights"] = {k: round(float(v),3) for k,v in zip(df.columns, w_tan)}
print(json.dumps(res, indent=2))

eq = pd.DataFrame({"Trend": (1+df["trend"]).cumprod(), "Carry": (1+df["carry"]).cumprod(),
                   "Reversal": (1+df["reversal"]).cumprod(),
                   "Equal-risk combo": (1+eq3).cumprod()}).dropna()
fig, ax = plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index, eq[c], lw=1.7, label=c)
ax.set_yscale("log"); ax.set_title("inercia multi-engine book: trend, carry, reversal (log)"); ax.legend()
ax.set_ylabel("growth of $1")
fig.tight_layout(); fig.savefig(os.path.join(OUT,"06_engines.png")); plt.close(fig)
json.dump(res, open(os.path.join(OUT,"combo_metrics.json"),"w"), indent=2)
