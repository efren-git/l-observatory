"""ai_module.py - AI-valuation fragility from yfinance (Mag-7 vs S&P, valuations)."""
import os, json
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
YH = os.path.join(BASE, "data", "raw", "yahoo")
OUT = os.path.join(BASE, "output")

def load(sym):
    p = os.path.join(YH, sym.replace("^", "").replace(".", "_") + ".csv")
    df = pd.read_csv(p)
    datecol = [c for c in df.columns if c.lower() == "date"] or [df.columns[0]]
    closecol = [c for c in df.columns if c.lower() == "close"][0]
    d = pd.to_datetime(df[datecol[0]].astype(str).str[:10])
    return pd.Series(pd.to_numeric(df[closecol], errors="coerce").values, index=d).dropna()

mag7 = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA"]
closes = {s: load(s) for s in mag7}
sp = load("^GSPC")
df = pd.DataFrame(closes).dropna()
sp = sp.reindex(df.index).dropna()
df = df.reindex(sp.index)

rb = df / df.iloc[0] * 100.0
sp_rb = sp / sp.iloc[0] * 100.0
mag_avg = rb.mean(axis=1)

fig, ax = plt.subplots(figsize=(11, 5.5))
for s in mag7:
    ax.plot(rb.index, rb[s], color="grey", lw=0.8, alpha=0.55)
ax.plot(mag_avg.index, mag_avg, color="#8e44ad", lw=2.2, label="Mag-7 (equal-weight)")
ax.plot(sp_rb.index, sp_rb, color="#2c3e50", lw=2.2, label="S&P 500")
ax.set_yscale("log")
ax.set_title("The AI trade: Mag-7 vs S&P 500 (rebased to 100, log scale, 10y monthly)")
ax.set_ylabel("rebased (start = 100)")
ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "12_mag7_vs_sp.png")); plt.close(fig)

fund = json.load(open(os.path.join(YH, "fundamentals.json")))
names = mag7
pes = [float(fund.get(s, {}).get("trailingPE") or 0) for s in mag7]
caps = [float(fund.get(s, {}).get("marketCap") or 0) for s in mag7]

fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(names, pes, color="#2980b9")
for i, v in enumerate(pes):
    ax.text(i, v + 4, f"{v:.0f}", ha="center")
ax.set_title("Valuation dispersion: trailing P/E of the Mag-7")
ax.set_ylabel("trailing P/E")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "13_mag7_pe.png")); plt.close(fig)

summary = {
    "mag7_combined_marketcap_trillion": round(sum(caps) / 1e12, 2),
    "mag7_pe": {s: round(pes[i], 1) for i, s in enumerate(names)},
    "mag7_vs_sp_10y_pct": round(float(mag_avg.iloc[-1] / sp_rb.iloc[-1] * 100 - 100), 1),
    "sp_10y_return_pct": round(float(sp_rb.iloc[-1] - 100), 1),
}
with open(os.path.join(OUT, "ai.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
