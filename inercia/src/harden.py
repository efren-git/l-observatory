"""harden.py - drawdown control + regime-aware risk scaling on the book."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW=os.path.join(BASE,"data","raw"); OUT=os.path.join(BASE,"output"); M=21

def perf(r):
    r=r.dropna(); eq=(1+r).cumprod(); vol=r.std()*np.sqrt(252)
    dsd=r[r<0].std()*np.sqrt(252)
    yr=(1+r).resample("YE").prod()-1
    return {"CAGR":round(float(eq.iloc[-1]**(252.0/len(r))-1),4),"Vol":round(float(vol),4),
            "Sharpe":round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "Sortino":round(float(r.mean()*252/dsd),3) if dsd else None,
            "MaxDD":round(float((eq/eq.cummax()-1).min()),4),
            "WorstYr":round(float(yr.min()),4)}

def loadp(folder,t):
    d=pd.read_csv(os.path.join(RAW,folder,f"{t}.csv")); dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"],errors="coerce")
def port(sig,ret,volw,rebal="ME",cbps=5.0):
    raw=(sig/volw).replace([np.inf,-np.inf],np.nan).fillna(0.0)
    w=raw.div(raw.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
    wd=w.resample(rebal).last().reindex(w.index,method="ffill").fillna(0.0).shift(1).fillna(0.0)
    g=(wd*ret).sum(axis=1).fillna(0.0)
    return g, wd

# --- trend ---
tk=sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
px=pd.DataFrame({t:loadp("prices",t) for t in tk}).sort_index(); pret=px.pct_change()
volp=pret.rolling(20).std()*np.sqrt(252.0)
ts=sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs=np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
gt,_=port(0.5*np.sign(ts)+0.5*xs, pret, volp)

# --- carry ---
def fr(k):
    d=pd.read_csv(os.path.join(RAW,"fred",f"rate_{k}.csv")); d.columns=["date","value"]
    d["date"]=pd.to_datetime(d["date"]); d["value"]=pd.to_numeric(d["value"],errors="coerce")
    return d.dropna().set_index("date")["value"]
def fxs(k,inv=False):
    d=pd.read_csv(os.path.join(RAW,"fx",f"{k}.csv")); dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index(); s=pd.to_numeric(d["Close"],errors="coerce")
    return (1/s) if inv else s
CUR={"EUR":False,"JPY":True,"GBP":False,"CAD":True,"AUD":False,"CHF":True,"NZD":False,"SEK":True,"NOK":True}
RK={"EUR":"EU","JPY":"JP","GBP":"UK","CAD":"CA","AUD":"AU","CHF":"CH","NZD":"NZ","SEK":"SE","NOK":"NO"}
S=pd.DataFrame({c:fxs(c,i) for c,i in CUR.items()}).sort_index(); fxret=S.pct_change()
usd=fr("US").resample("MS").last(); rates=pd.DataFrame({c:fr(RK[c]).resample("MS").last() for c in CUR})
carryd=rates.reindex(fxret.index,method="ffill").sub(usd.reindex(fxret.index,method="ffill"),axis=0)
totret=fxret.add(carryd/100.0/252.0,fill_value=0.0); volc=totret.rolling(60).std()*np.sqrt(252.0)
zc=carryd.sub(carryd.mean(axis=1),axis=0).div(carryd.std(axis=1),axis=0)
gc,_=port(zc, totret, volc)

df=pd.DataFrame({"trend":gt,"carry":gc}).dropna()
mu=df.mean().values; cov=df.cov().values
w=np.clip(np.linalg.solve(cov,mu),0,None); w=w/w.sum()
gbook=(df["trend"]*w[0]+df["carry"]*w[1])
# base: vol target 10%
rv=gbook.rolling(60).std()*np.sqrt(252.0)
book = gbook*(0.10/rv.shift(1)).clip(0,3).fillna(1.0)

def dd_control(r, maxdd=0.20, floor=0.0):
    eq=1.0; peak=1.0; out=[]
    for x in r.fillna(0.0):
        dd=eq/peak-1.0
        mult=float(np.clip(1.0+dd/maxdd, floor, 1.0))
        rr=x*mult
        eq*= (1+rr); peak=max(peak,eq); out.append(rr)
    return pd.Series(out, index=r.index)

# regime: short vol vs long vol
sv=book.rolling(20).std()*np.sqrt(252); lv=book.rolling(252).std()*np.sqrt(252)
regime=np.clip((lv/sv).shift(1),0.4,1.2)      # de-risk when short vol > long vol
book_reg=(book*regime).fillna(0.0)
book_dd=dd_control(book,0.20)
book_hard=(dd_control(book*regime,0.20))

res={"trend":perf(gt),"carry":perf(gc),"book":perf(book),
     "book_dd_control":perf(book_dd),"book_regime":perf(book_reg),"book_hardened":perf(book_hard)}
print(json.dumps(res,indent=2))

eq=pd.DataFrame({"Book":(1+book).cumprod(),"Book + DD control":(1+book_dd).cumprod(),
                 "Book hardened (DD+regime)":(1+book_hard).cumprod()}).dropna()
fig,ax=plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index,eq[c],lw=1.7,label=c)
ax.set_yscale("log"); ax.set_title("Hardening the book: drawdown control + regime scaling"); ax.legend(); ax.set_ylabel("growth of $1")
fig.tight_layout(); fig.savefig(os.path.join(OUT,"08_hardened.png")); plt.close(fig)
json.dump(res,open(os.path.join(OUT,"hardened_metrics.json"),"w"),indent=2)
