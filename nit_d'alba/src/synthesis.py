"""synthesis.py - the fragility index and scenario stress test (the centerpiece).

Fragility index = mean z-score of five stress components (higher = more fragile):
  debt/GDP, interest burden, real 10Y yield, oil price, VIX.
Scenario stress test = what the debt-service burden looks like after shocks.
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "fred")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"figure.figsize": (11, 5.5), "axes.grid": True, "grid.alpha": 0.3})

def load(sid):
    df = pd.read_csv(os.path.join(RAW, f"{sid}.csv"))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"]

debt = load("GFDEBTN") / 1000.0      # billions
gdp  = load("GDP")                   # billions
d10  = load("DGS10")
t10  = load("T10YIE")
oil  = load("DCOILWTICO")
vix  = load("VIXCLS")

m = pd.DataFrame({
    "debt_gdp": (debt / gdp * 100.0),
    "d10": d10, "t10": t10, "oil": oil, "vix": vix,
}).resample("ME").last().ffill()
m["interest_burden"] = m["debt_gdp"] * m["d10"] / 100.0
m["real_yield"] = m["d10"] - m["t10"]

components = ["debt_gdp", "interest_burden", "real_yield", "oil", "vix"]
z = (m[components] - m[components].mean()) / m[components].std()
m["fragility"] = z.mean(axis=1)

cur = m.iloc[-1]
pct = float((m["fragility"] <= cur["fragility"]).mean() * 100.0)
summary = {
    "fragility_latest": round(float(cur["fragility"]), 2),
    "fragility_percentile_since_1970": round(pct, 1),
    "components_latest": {c: round(float(cur[c]), 2) for c in components},
}

# ------------------------------------------------------------- scenario test
D = float(cur["debt_gdp"]); Y = float(cur["d10"]); B = float(cur["interest_burden"])
scenarios = {}
def burden(d, y): return d * y / 100.0

scenarios["baseline"] = {"debt_gdp": round(D,1), "y10": round(Y,2), "interest_burden": round(B,2)}
# 1: war / oil shock -> inflation +2pp, 10Y +1.5pp
y1 = Y + 1.5
scenarios["war_oil_shock"] = {"debt_gdp": round(D,1), "y10": round(y1,2), "interest_burden": round(burden(D, y1),2)}
# 2: AI correction -> GDP -3%, debt +5% (stimulus)
d2 = D * 1.05 / 0.97
scenarios["ai_correction"] = {"debt_gdp": round(d2,1), "y10": round(Y,2), "interest_burden": round(burden(d2, Y),2)}
# 3: combined (both shocks)
d3 = d2; y3 = Y + 1.5
scenarios["combined_shock"] = {"debt_gdp": round(d3,1), "y10": round(y3,2), "interest_burden": round(burden(d3, y3),2)}
summary["scenarios"] = scenarios

# ------------------------------------------------------------------ charts
fig, ax = plt.subplots()
ax.plot(m.index, m["fragility"], color="#c0392b", lw=1.8)
ax.axhline(0, color="grey", lw=0.8)
ax.axhline(float(cur["fragility"]), color="#2c3e50", ls="--", lw=1)
ax.set_title("Economic fragility index (z-score composite: debt, interest burden, real yield, oil, VIX)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "07_fragility_index.png")); plt.close(fig)

fig, ax = plt.subplots()
names = list(scenarios.keys())
burdens = [scenarios[k]["interest_burden"] for k in names]
colors = ["#7f8c8d", "#e67e22", "#2980b9", "#c0392b"]
ax.bar(names, burdens, color=colors)
for i, v in enumerate(burdens):
    ax.text(i, v + 0.1, f"{v:.2f}%", ha="center")
ax.set_ylabel("Interest burden (% of GDP)")
ax.set_title("Scenario stress test: debt-service burden under shocks")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "08_scenarios.png")); plt.close(fig)

with open(os.path.join(OUT, "synthesis.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
