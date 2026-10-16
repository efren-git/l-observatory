"""market_module.py - AI/tech concentration proxy from index data (+ any Yahoo names)."""
import os, glob, json
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRED = os.path.join(BASE, "data", "raw", "fred")
YAHOO = os.path.join(BASE, "data", "raw", "yahoo")
OUT = os.path.join(BASE, "output")

def load_fred(sid):
    df = pd.read_csv(os.path.join(FRED, f"{sid}.csv")); df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]); df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"]

sp = load_fred("SP500").resample("ME").mean()
nq = load_fred("NASDAQCOM").resample("ME").mean()
df = pd.concat([sp.rename("sp500"), nq.rename("nasdaq")], axis=1).dropna()
df["ratio"] = df["nasdaq"] / df["sp500"]
df["rebased"] = df["ratio"] / df["ratio"].iloc[0] * 100.0

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(df.index, df["rebased"], color="#8e44ad", lw=1.6)
ax.axhline(100, color="grey", ls="--", lw=0.8)
ax.set_title("Tech dominance: Nasdaq Composite vs S&P 500 (ratio rebased to 100)")
ax.set_ylabel("Nasdaq/S&P ratio (rebased)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "10_tech_concentration.png")); plt.close(fig)

summary = {
    "nasdaq_vs_sp_ratio_latest": round(float(df["ratio"].iloc[-1]), 3),
    "ratio_rebased_latest": round(float(df["rebased"].iloc[-1]), 1),
    "ratio_min": round(float(df["rebased"].min()), 1),
    "yahoo_names": [os.path.basename(n)[:-4] for n in sorted(glob.glob(os.path.join(YAHOO, "*.csv")))],
}
with open(os.path.join(OUT, "market.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
