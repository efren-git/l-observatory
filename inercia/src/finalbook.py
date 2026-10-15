"""finalbook.py - trend + carry + cross-sectional equity momentum: the final book."""
import os, json
import numpy as np, pandas as pd
BASE=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW=os.path.join(BASE,"data","raw"); OUT=os.path.join(BASE,"output"); M=21

def perf(r):
    r=r.dropna(); eq=(1+r).cumprod(); dsd=r[r<0].std()*np.sqrt(252)
    return {"CAGR":round(float(eq.iloc[-1]**(252.0/len(r))-1),4),"Vol":round(float(r.std()*np.sqrt(252)),4),
            "Sharpe":round(float(r.mean()/r.std()*np.sqrt(252)),3),
            "Sortino":round(float(r.mean()*252/dsd),3) if dsd else None,"MaxDD":round(float((eq/eq.cummax()-1).min()),4)}
def loadp(folder,t):
    d=pd.read_csv(os.path.join(RAW,folder,f"{t}.csv")); dc=[c for c in d.columns if c.lower()=="date"][0]
    d[dc]=pd.to_datetime(d[dc]); d=d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"],errors="coerce")
def vt(r,t=0.10): return r/r.rolling(60).std().shift(1)/np.sqrt(252)*t
def bt_panel(w, ret, freq="ME", cbps=5.0):
    wd=w.resample(freq).last().reindex(w.index,method="ffill").fillna(0.0).shift(1).fillna(0.0)
    g=(wd*ret).sum(axis=1).fillna(0.0); rv=g.rolling(60).std()*np.sqrt(252)
    s=(0.10/rv.shift(1)).clip(0,3).fillna(1.0); ws=wd.mul(s,axis=0)
    return g*s - ws.diff().abs().sum(axis=1).fillna(0.0)*(cbps/1e4)

# trend (multi-asset)
tk=sorted(f[:-4] for f in os.listdir(os.path.join(RAW,"prices")) if f.endswith(".csv"))
px=pd.DataFrame({t:loadp("prices",t) for t in tk}).sort_index(); pret=px.pct_change()
volp=pret.rolling(20).std()*np.sqrt(252.0)
ts=sum(np.sign(px/px.shift(n*M)-1) for n in [1,3,6,12])/4.0
xs=np.sign((px.shift(M)/px.shift(12*M)-1).rank(axis=1,pct=True)-0.5)
wt=((0.5*np.sign(ts)+0.5*xs)/volp).replace([np.inf,-np.inf],np.nan).fillna(0.0)
wt=wt.div(wt.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
trend=bt_panel(wt, pret)

# carry (G10 FX)
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
wc=(zc/volc).replace([np.inf,-np.inf],np.nan).fillna(0.0); wc=wc.div(wc.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
carry=bt_panel(wc, totret)

# cross-sectional equity momentum (continuous z-weights)
sdir=os.path.join(RAW,"stocks"); stk=sorted(f[:-4] for f in os.listdir(sdir) if f.endswith(".csv") and not f.startswith("sp500"))
spx=pd.DataFrame({t:loadp("stocks",t) for t in stk}).sort_index(); sret=spx.pct_change()
mom=spx.shift(M)/spx.shift(12*M)-1
zv=mom.sub(mom.mean(axis=1),axis=0).div(mom.std(axis=1),axis=0).clip(-3,3)
vols=sret.rolling(60).std()*np.sqrt(252.0)
wm=(zv/vols).replace([np.inf,-np.inf],np.nan).fillna(0.0)
wm=wm.div(wm.abs().sum(axis=1).replace(0,np.nan),axis=0).fillna(0.0)
xsm=bt_panel(wm, sret, cbps=10.0)

df=pd.DataFrame({"trend":trend,"carry":carry,"xsmom":xsm}).dropna()
res={"trend":perf(df["trend"]),"carry":perf(df["carry"]),"xs_momentum":perf(df["xsmom"])}
res["corr"]=df.corr().round(3).to_dict()
# optimal long-only weights
mu=df.mean().values; cov=df.cov().values
wts=np.clip(np.linalg.solve(cov,mu),0,None); wts=wts/wts.sum()
book=(df.values@wts)
book=pd.Series(book,index=df.index)
res["book_weights"]={k:round(float(v),3) for k,v in zip(df.columns,wts)}
res["book"]=perf(book)
spy=pret["SPY"].fillna(0.0); s40=0.6*spy+0.4*pret["IEF"].fillna(0.0)
res["sixty40"]=perf(s40)
res["combo_60_40_plus_30_book"]=perf(0.7*s40+0.3*vt(book))
print(json.dumps(res,indent=2))
json.dump(res, open(os.path.join(OUT,"finalbook_metrics.json"),"w"), indent=2)
