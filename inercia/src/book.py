"""book.py - the honest multi-engine book (trend + carry) and its portfolio value."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE,"data","raw"); OUT = os.path.join(BASE,"output"); M=21

def stats(r):
    r=r.dropna(); eq=(1+r).cumprod()
    return {"CAGR":round(float(eq.iloc[-1]**(252.0/len(r))-1),4),"Vol":round(float(r.std()*np.sqrt(252)),4),
            "Sharpe":round(float(r.mean()/r.std()*np.sqrt(252)),3),"MaxDD":round(float((eq/eq.cummax()-1).min()),4)}
def vt(r,t=0.10): return r/r.std()*t/np.sqrt(252)
def loadp(folder,t):
    d=pd.read_csv(os.path.join(RAW,folder,f"{t}.csv")); dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"],errors="coerce")
def port(sig,ret,volw,rebal="ME",cbps=5.0):
    raw=(sig/volw).replace([np.inf,-np.inf],np.nan).fillna(0.0)
    w=raw.div(raw.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
    wd=w.resample(rebal).last().reindex(w.index,method="ffill").fillna(0.0).shift(1).fillna(0.0)
    g=(wd*ret).sum(axis=1).fillna(0.0); rv=g.rolling(60).std()*np.sqrt(252.0)
    s=(0.10/rv.shift(1)).clip(0,3).fillna(1.0); ws=wd.mul(s,axis=0)
    turn=ws.diff().abs().sum(axis=1).fillna(0.0)
    return g*s - turn*(cbps/1e4)

tk=sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
px=pd.DataFrame({t:loadp("prices",t) for t in tk}).sort_index(); pret=px.pct_change()
volp=pret.rolling(20).std()*np.sqrt(252.0)
ts=sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs=np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
trend=port(0.5*np.sign(ts)+0.5*xs, pret, volp)

def fred_rate(k):
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
usd=fred_rate("US").resample("MS").last()
rates=pd.DataFrame({c:fred_rate(RK[c]).resample("MS").last() for c in CUR})
carryd=rates.reindex(fxret.index,method="ffill").sub(usd.reindex(fxret.index,method="ffill"),axis=0)
totret=fxret.add(carryd/100.0/252.0,fill_value=0.0); volc=totret.rolling(60).std()*np.sqrt(252.0)
zc=carryd.sub(carryd.mean(axis=1),axis=0).div(carryd.std(axis=1),axis=0)
carry=port(zc, totret, volc)

df=pd.DataFrame({"trend":trend,"carry":carry}).dropna()
# constrained long-only optimal weights for the book
mu=df.mean().values; cov=df.cov().values
wt=np.clip(np.linalg.solve(cov,mu),0,None); wt=wt/wt.sum()
book=vt(df["trend"])*wt[0]+vt(df["carry"])*wt[1]
spy=pret["SPY"].fillna(0.0); ief=pret["IEF"].fillna(0.0); s40=0.6*spy+0.4*ief
combo=0.7*s40+0.3*vt(book)

res={"trend":stats(df["trend"]),"carry":stats(df["carry"]),"corr_trend_carry":round(float(df["trend"].corr(df["carry"])),3),
     "book_weights":{"trend":round(float(wt[0]),3),"carry":round(float(wt[1]),3)},"book":stats(book),
     "sixty40":stats(s40),"combo_60_40_plus_30_book":stats(combo)}
print(json.dumps(res,indent=2))

eq=pd.DataFrame({"Trend":(1+df["trend"]).cumprod(),"Carry":(1+df["carry"]).cumprod(),
                 "Book (trend+carry)":(1+book).cumprod(),"60/40 + 30% book":(1+combo).cumprod()}).dropna()
fig,ax=plt.subplots(figsize=(11,5.5))
for c in eq.columns: ax.plot(eq.index,eq[c],lw=1.7,label=c)
ax.set_yscale("log"); ax.set_title("inercia book: trend + carry, and its portfolio value"); ax.legend(); ax.set_ylabel("growth of $1")
fig.tight_layout(); fig.savefig(os.path.join(OUT,"07_book.png")); plt.close(fig)
json.dump(res,open(os.path.join(OUT,"book_metrics.json"),"w"),indent=2)
