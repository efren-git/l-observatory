"""carry.py - G10 FX carry engine + combination with the trend engine."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw"); OUT = os.path.join(BASE, "output")

def stats(r):
    r = r.dropna(); eq = (1+r).cumprod()
    cagr = eq.iloc[-1]**(252.0/len(r))-1; vol = r.std()*np.sqrt(252)
    return {"CAGR": round(float(cagr),4), "Vol": round(float(vol),4),
            "Sharpe": round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "MaxDD": round(float((eq/eq.cummax()-1).min()),4), "Total": round(float(eq.iloc[-1]-1),2)}

# ---------------- FX carry ----------------
def fred_rate(k):
    d = pd.read_csv(os.path.join(RAW,"fred",f"rate_{k}.csv")); d.columns=["date","value"]
    d["date"] = pd.to_datetime(d["date"]); d["value"] = pd.to_numeric(d["value"], errors="coerce")
    return d.dropna().set_index("date")["value"]

def fx(k, invert=False):
    d = pd.read_csv(os.path.join(RAW,"fx",f"{k}.csv"))
    dc = [c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    s = pd.to_numeric(d["Close"], errors="coerce")
    return (1.0/s) if invert else s

CUR = {"EUR":False,"JPY":True,"GBP":False,"CAD":True,"AUD":False,"CHF":True,"NZD":False,"SEK":True,"NOK":True}
S = pd.DataFrame({c: fx(c, inv) for c, inv in CUR.items()}).sort_index()
fxret = S.pct_change()
usd = fred_rate("US").resample("MS").last()
RATEKEY = {"EUR":"EU","JPY":"JP","GBP":"UK","CAD":"CA","AUD":"AU","CHF":"CH","NZD":"NZ","SEK":"SE","NOK":"NO"}
rates = pd.DataFrame({c: fred_rate(RATEKEY[c]).resample("MS").last() for c in CUR})
carry = rates.reindex(fxret.index, method="ffill").sub(usd.reindex(fxret.index, method="ffill"), axis=0)
accrual = carry/100.0/252.0            # daily interest differential (the carry itself)
totret = fxret.add(accrual, fill_value=0.0)
volc = totret.rolling(60).std()*np.sqrt(252.0)
z = carry.sub(carry.mean(axis=1), axis=0).div(carry.std(axis=1), axis=0)
raw = (z/volc).replace([np.inf,-np.inf], np.nan).fillna(0.0)
w = raw.div(raw.abs().sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
w_d = w.resample("ME").last().reindex(w.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
g = (w_d*totret).sum(axis=1).fillna(0.0)
rv = g.rolling(60).std()*np.sqrt(252.0)
scale = (0.10/rv.shift(1)).clip(0,3).fillna(1.0)
ws = w_d.mul(scale, axis=0)
turn = ws.diff().abs().sum(axis=1).fillna(0.0)
carry_ret = g*scale - turn*(5.0/1e4)

# ---------------- trend engine (recomputed) ----------------
def loadp(t):
    d = pd.read_csv(os.path.join(RAW,"prices",f"{t}.csv"))
    dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"], errors="coerce")
tk = sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
px = pd.DataFrame({t: loadp(t) for t in tk}).sort_index(); pret = px.pct_change(); M=21
ts = sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs = np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
sig = 0.5*np.sign(ts)+0.5*xs
volp = pret.rolling(20).std()*np.sqrt(252.0)
rawp = (sig/volp).replace([np.inf,-np.inf], np.nan).fillna(0.0)
wp = rawp.div(rawp.abs().sum(axis=1).replace(0,np.nan), axis=0).fillna(0.0)
wp_d = wp.resample("ME").last().reindex(wp.index, method="ffill").fillna(0.0).shift(1).fillna(0.0)
gp = (wp_d*pret).sum(axis=1).fillna(0.0)
rvp = gp.rolling(60).std()*np.sqrt(252.0)
scalep = (0.10/rvp.shift(1)).clip(0,3).fillna(1.0)
wsp = wp_d.mul(scalep, axis=0)
turnp = wsp.diff().abs().sum(axis=1).fillna(0.0)
trend_ret = gp*scalep - turnp*(5.0/1e4)

# ---------------- combine (risk-matched, equal weight) ----------------
df = pd.DataFrame({"trend": trend_ret, "carry": carry_ret}).dropna()
# scale each to 10% vol then 50/50
def vt(r): return r/r.std()*0.10/np.sqrt(252)
combo = 0.5*vt(df["trend"]) + 0.5*vt(df["carry"])

res = {"carry": stats(carry_ret), "trend": stats(trend_ret), "combo_50_50": stats(combo),
       "corr_trend_carry": round(float(df["trend"].corr(df["carry"])),3)}
print(json.dumps(res, indent=2))

eq = pd.DataFrame({"Carry": (1+carry_ret).cumprod(), "Trend": (1+trend_ret).cumprod(),
                   "50/50 combo": (1+combo).cumprod()}).dropna()
fig, ax = plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index, eq[c], lw=1.7, label=c)
ax.set_yscale("log"); ax.set_title("Two uncorrelated engines: carry vs trend vs combo (log)"); ax.legend()
ax.set_ylabel("growth of $1")
fig.tight_layout(); fig.savefig(os.path.join(OUT,"05_carry_combo.png")); plt.close(fig)
json.dump(res, open(os.path.join(OUT,"carry_metrics.json"),"w"), indent=2)
