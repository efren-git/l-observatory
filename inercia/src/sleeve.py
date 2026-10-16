"""sleeve.py - cross-sectional equity sleeve (momentum + low-vol) vs the trend book."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW=os.path.join(BASE,"data","raw"); OUT=os.path.join(BASE,"output"); M=21

def perf(r):
    r=r.dropna(); eq=(1+r).cumprod()
    dsd=r[r<0].std()*np.sqrt(252)
    return {"CAGR":round(float(eq.iloc[-1]**(252.0/len(r))-1),4),"Vol":round(float(r.std()*np.sqrt(252)),4),
            "Sharpe":round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "Sortino":round(float(r.mean()*252/dsd),3) if dsd else None,
            "MaxDD":round(float((eq/eq.cummax()-1).min()),4)}
def loadp(folder,t):
    d=pd.read_csv(os.path.join(RAW,folder,f"{t}.csv")); dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"],errors="coerce")

# ---- equity universe ----
sdir=os.path.join(RAW,"stocks")
stk=sorted(f[:-4] for f in os.listdir(sdir) if f.endswith(".csv") and not f.startswith("sp500"))
px=pd.DataFrame({t:loadp("stocks",t) for t in stk}).sort_index()
ret=px.pct_change()
mom=px.shift(M)/px.shift(12*M)-1
vol=ret.rolling(252).std()

def xsw(signal, long_high=True):
    r=signal.rank(axis=1,pct=True)
    if not long_high: r=1-r
    w=pd.DataFrame(0.0,index=signal.index,columns=signal.columns)
    w[r>=0.9]=1.0; w[r<=0.1]=-1.0
    return w.div(w.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)

w_mom=xsw(mom, True); w_lv=xsw(vol, False); w_mix=(w_mom+w_lv)/2

def bt(w, freq="ME", cbps=10.0):
    wd=w.resample(freq).last().reindex(w.index,method="ffill").fillna(0.0).shift(1).fillna(0.0)
    g=(wd*ret).sum(axis=1).fillna(0.0)
    rv=g.rolling(60).std()*np.sqrt(252); s=(0.10/rv.shift(1)).clip(0,3).fillna(1.0)
    ws=wd.mul(s,axis=1); turn=ws.diff().abs().sum(axis=1).fillna(0.0)
    return g*s - turn*(cbps/1e4), float(turn.mean()*252)

mom_r,tm=bt(w_mom); lv_r,tl=bt(w_lv); mix_r,tx=bt(w_mix)

# ---- trend book (recompute for correlation) ----
tk=sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
epx=pd.DataFrame({t:loadp("prices",t) for t in tk}).sort_index(); eret=epx.pct_change()
evol=eret.rolling(20).std()*np.sqrt(252.0)
ts=sum(np.sign(epx/epx.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs=np.sign((epx.shift(M)/epx.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
sig=0.5*np.sign(ts)+0.5*xs
raw=(sig/evol).replace([np.inf,-np.inf],np.nan).fillna(0.0)
w=raw.div(raw.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
wd=w.resample("ME").last().reindex(w.index,method="ffill").fillna(0.0).shift(1).fillna(0.0)
g=(wd*eret).sum(axis=1).fillna(0.0); rv=g.rolling(60).std()*np.sqrt(252)
trend=g*(0.10/rv.shift(1)).clip(0,3).fillna(1.0)

df=pd.DataFrame({"trend":trend,"xs_mom":mom_r,"lowvol":lv_r,"sleeve":mix_r}).dropna()
res={"xs_momentum":perf(df["xs_mom"]),"low_vol":perf(df["lowvol"]),"equity_sleeve":perf(df["sleeve"]),
     "trend":perf(df["trend"]),
     "corr_sleeve_trend":round(float(df["sleeve"].corr(df["trend"])),3),
     "corr_mom_trend":round(float(df["xs_mom"].corr(df["trend"])),3),
     "turnover_mom":round(tm,1),"turnover_sleeve":round(tx,1)}
# combine trend book + equity sleeve (equal risk)
book=vt_=None
def vt(r): return r/r.std()*0.10/np.sqrt(252)
combo=0.5*vt(df["trend"])+0.5*vt(df["sleeve"])
res["combo_trend_sleeve"]=perf(combo)
print(json.dumps(res,indent=2))

eq=pd.DataFrame({"Trend book":(1+df["trend"]).cumprod(),"Equity sleeve":(1+df["sleeve"]).cumprod(),
                 "50/50":(1+combo).cumprod()}).dropna()
fig,ax=plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index,eq[c],lw=1.7,label=c)
ax.set_yscale("log"); ax.set_title("inercia: trend book + cross-sectional equity sleeve (log)"); ax.legend(); ax.set_ylabel("growth of $1")
fig.tight_layout(); fig.savefig(os.path.join(OUT,"09_sleeve.png")); plt.close(fig)
json.dump(res,open(os.path.join(OUT,"sleeve_metrics.json"),"w"),indent=2)
