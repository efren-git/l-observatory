"""strategy.py - momentum (TS + XS) with vol-targeting: signals, portfolio, backtest."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "prices")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

def load(t):
    d = pd.read_csv(os.path.join(RAW, f"{t}.csv"))
    dc = [c for c in d.columns if c.lower() == "date"][0]
    d[dc] = pd.to_datetime(d[dc]); d = d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"], errors="coerce")

tickers = sorted(f[:-4] for f in os.listdir(RAW) if f.endswith(".csv"))
px = pd.DataFrame({t: load(t) for t in tickers}).sort_index()
ret = px.pct_change()

# ---------------- signals ----------------
M = 21  # ~trading days per month
ts = sum(np.sign(px / px.shift(n * M) - 1) for n in [1, 3, 6, 12]) / 4.0      # time-series momentum ensemble
xs_raw = px.shift(M) / px.shift(12 * M) - 1                                   # 12-1 cross-sectional momentum
xs = np.sign(xs_raw.rank(axis=1, pct=True) - 0.5)                             # top half long, bottom half short
signal = 0.5 * np.sign(ts) + 0.5 * xs

vol = ret.rolling(20).std() * np.sqrt(252.0)
raw_w = (signal / vol).replace([np.inf, -np.inf], np.nan).fillna(0.0)
gross = raw_w.abs().sum(axis=1).replace(0, np.nan)
w = raw_w.div(gross, axis=0).fillna(0.0)                                      # gross exposure = 1

# monthly rebalance
w_m = w.resample("ME").last()
w_d = w_m.reindex(w.index, method="ffill").fillna(0.0)
w_d = w_d.shift(1).fillna(0.0)                                               # apply from next day (no lookahead)

gross_ret = (w_d * ret).sum(axis=1).fillna(0.0)

# ---------------- vol targeting ----------------
target_vol = 0.10
realized = gross_ret.rolling(60).std() * np.sqrt(252.0)
scale = (target_vol / realized.shift(1)).clip(0, 3).fillna(1.0)
port_ret_gross = gross_ret * scale
w_scaled = w_d.mul(scale, axis=0)

# ---------------- costs ----------------
cost_bps = 5.0
turnover = w_scaled.diff().abs().sum(axis=1).fillna(0.0)
costs = turnover * (cost_bps / 1e4)
port_ret = port_ret_gross - costs

# ---------------- benchmarks ----------------
spy = ret["SPY"].fillna(0.0)
sixty40 = 0.6 * ret["SPY"].fillna(0.0) + 0.4 * ret["IEF"].fillna(0.0)

def stats(r):
    r = r.dropna()
    if len(r) == 0: return {}
    eq = (1 + r).cumprod()
    cagr = eq.iloc[-1] ** (252.0 / len(r)) - 1
    vol_a = r.std() * np.sqrt(252)
    sharpe = r.mean() / r.std() * np.sqrt(252) if r.std() else 0
    dd = (eq / eq.cummax() - 1).min()
    return {"CAGR": round(float(cagr), 4), "Vol": round(float(vol_a), 4),
            "Sharpe": round(float(sharpe), 3), "MaxDD": round(float(dd), 4),
            "Total": round(float(eq.iloc[-1] - 1), 3)}

res = {
  "strategy_net": stats(port_ret),
  "strategy_gross": stats(port_ret_gross),
  "spy_buy_hold": stats(spy),
  "sixty_forty": stats(sixty40),
}
avg_turnover = float(turnover.mean() * 252)
res["annual_turnover"] = round(avg_turnover, 2)
res["corr_to_spy"] = round(float(port_ret.corr(spy)), 3)

# sub-periods
def period(r, a, b):
    return stats(r.loc[a:b])
res["subperiods"] = {
  "2004_2007": period(port_ret, "2004-01-01", "2007-12-31"),
  "2008_2009": period(port_ret, "2008-01-01", "2009-12-31"),
  "2010_2019": period(port_ret, "2010-01-01", "2019-12-31"),
  "2020_2026": period(port_ret, "2020-01-01", "2026-12-31"),
}
print(json.dumps(res, indent=2))

# ---------------- charts ----------------
eq = pd.DataFrame({
  "Strategy (net)": (1 + port_ret).cumprod(),
  "SPY buy & hold": (1 + spy).cumprod(),
  "60/40": (1 + sixty40).cumprod(),
})
fig, ax = plt.subplots(figsize=(11, 5.5))
for c in eq.columns:
    ax.plot(eq.index, eq[c], lw=1.7, label=c)
ax.set_yscale("log"); ax.set_title("inercia: momentum strategy vs benchmarks (log scale)")
ax.set_ylabel("growth of $1"); ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_equity.png")); plt.close(fig)

dd = eq["Strategy (net)"] / eq["Strategy (net)"].cummax() - 1
fig, ax = plt.subplots(figsize=(11, 3.5))
ax.fill_between(dd.index, dd.values, 0, color="#c0392b", alpha=0.6)
ax.set_title("Strategy drawdown"); ax.set_ylabel("drawdown")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_drawdown.png")); plt.close(fig)

with open(os.path.join(OUT, "metrics.json"), "w") as f:
    json.dump(res, f, indent=2)
