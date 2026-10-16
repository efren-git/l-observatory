"""analyze.py — compute core stress metrics and generate charts.

Reads data/raw/fred and data/raw/worldbank, writes charts + a JSON summary to output/.
"""
import os, json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({"figure.figsize": (10, 5.5), "axes.grid": True,
                     "grid.alpha": 0.3, "font.size": 11})

def load_fred(sid):
    df = pd.read_csv(os.path.join(RAW, "fred", f"{sid}.csv"))
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().set_index("date")["value"]
    return df

summary = {}

# ---------------------------------------------------------------- US debt ---
debt = load_fred("GFDEBTN")          # millions of dollars
gdp  = load_fred("GDP")              # billions of dollars (SAAR)
d10  = load_fred("DGS10")            # percent
cpi  = load_fred("CPIAUCSL")         # index
wti  = load_fred("DCOILWTICO")       # dollars/barrel
brent= load_fred("DCOILBRENTEU")     # dollars/barrel
ffr  = load_fred("FEDFUNDS")         # percent
t10yie= load_fred("T10YIE")          # percent

# quarterly debt/GDP (debt millions -> billions)
debt_b = debt / 1000.0
debt_gdp = (debt_b / gdp * 100.0).dropna()   # percent
summary["us_debt_to_gdp_latest"] = round(float(debt_gdp.iloc[-1]), 1)
summary["us_debt_trillion"] = round(float(debt_b.iloc[-1] / 1000.0), 2)
summary["us_gdp_trillion"] = round(float(gdp.iloc[-1] / 1000.0), 2)

# interest-burden stress proxy: if the whole stock paid the current 10Y rate
d10_q = d10.resample("QS").mean().reindex(debt_gdp.index, method="ffill")
aligned = pd.concat([debt_gdp, d10_q], axis=1).dropna()
aligned.columns = ["debt_gdp", "yield10"]
interest_burden = aligned["debt_gdp"] * aligned["yield10"] / 100.0   # % of GDP
summary["interest_burden_pct_gdp_latest"] = round(float(interest_burden.iloc[-1]), 2)
summary["yield10_latest"] = round(float(d10.dropna().iloc[-1]), 2)

# ------------------------------------------------------ real yield & oil ---
real_yield = (d10 - t10yie).dropna()
cpi_yoy = cpi.pct_change(12) * 100.0
wti_yoy = wti.pct_change(12) * 100.0
summary["oil_wti_latest"] = round(float(wti.dropna().iloc[-1]), 2)
summary["cpi_yoy_latest"] = round(float(cpi_yoy.dropna().iloc[-1]), 2)
summary["real_yield10_latest"] = round(float(real_yield.dropna().iloc[-1]), 2)

# ---------------------------------------------------------------- charts ---
# 1) debt/GDP
fig, ax = plt.subplots()
ax.plot(debt_gdp.index, debt_gdp.values, color="#c0392b", lw=2)
ax.axhline(100, color="grey", ls="--", lw=1)
ax.set_title("US federal debt, % of GDP")
ax.set_ylabel("% of GDP")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_debt_to_gdp.png")); plt.close(fig)

# 2) interest burden vs 10Y yield
fig, ax = plt.subplots()
ax.plot(interest_burden.index, interest_burden.values, color="#8e44ad", lw=2, label="Interest burden (% GDP)")
ax2 = ax.twinx()
ax2.plot(aligned.index, aligned["yield10"].values, color="#2980b9", lw=1.5, label="10Y yield (%)", alpha=0.8)
ax2.set_ylabel("10Y yield (%)"); ax.set_ylabel("Interest burden (% GDP)")
ax.set_title("Debt-service stress: interest burden vs 10-year yield")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_interest_burden.png")); plt.close(fig)

# 3) oil price
fig, ax = plt.subplots()
ax.plot(wti.index, wti.values, color="#16a085", lw=1.2, label="WTI")
ax.plot(brent.index, brent.values, color="#e67e22", lw=1.2, alpha=0.7, label="Brent")
ax.set_title("Crude oil price (USD/barrel)")
ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_oil_price.png")); plt.close(fig)

# 4) oil YoY vs CPI YoY (transmission)
fig, ax = plt.subplots()
ax.plot(wti_yoy.index, wti_yoy.values, color="#16a085", lw=1.2, label="Oil price YoY %")
ax.plot(cpi_yoy.index, cpi_yoy.values, color="#c0392b", lw=1.2, label="CPI YoY %")
ax.axhline(0, color="grey", lw=0.8)
ax.set_title("Oil vs inflation: the transmission channel (YoY %)")
ax.legend(); fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_oil_vs_inflation.png")); plt.close(fig)

# 5) real 10Y yield
fig, ax = plt.subplots()
ax.plot(real_yield.index, real_yield.values, color="#2c3e50", lw=1.5)
ax.axhline(0, color="grey", lw=0.8)
ax.set_title("US real 10-year yield (10Y minus breakeven inflation)")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "05_real_yield.png")); plt.close(fig)

# 6) global debt/GDP (World Bank, latest available per country)
wb = pd.read_csv(os.path.join(RAW, "worldbank", "GC.DOD.TOTL.GD.ZS.csv"))
wb = wb.dropna(subset=["value"]).copy()
wb["year"] = pd.to_numeric(wb["year"], errors="coerce")
wb = wb.dropna(subset=["year"])
latest = wb.sort_values("year").groupby("country").tail(1).sort_values("value")
fig, ax = plt.subplots()
ax.barh(latest["country"], latest["value"], color="#c0392b")
ax.set_title("Central government debt, % of GDP (latest available)")
ax.set_xlabel("% of GDP")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "06_global_debt.png")); plt.close(fig)

# ------------------------------------------------------------------ summary --
with open(os.path.join(OUT, "summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

print("SUMMARY")
for k, v in summary.items():
    print(f"  {k} = {v}")
print(f"  charts -> {OUT}")
