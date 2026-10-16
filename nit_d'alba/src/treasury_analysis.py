"""treasury_analysis.py - true interest burden from Treasury Fiscal Data."""
import os, json
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRE = os.path.join(BASE, "data", "raw", "treasury")
FRED = os.path.join(BASE, "data", "raw", "fred")
OUT = os.path.join(BASE, "output")

ie = pd.read_csv(os.path.join(TRE, "interest_expense.csv"))
ie["record_date"] = pd.to_datetime(ie["record_date"])
ie["month_expense_amt"] = pd.to_numeric(ie["month_expense_amt"], errors="coerce")
mt = ie.groupby("record_date")["month_expense_amt"].sum().sort_index()
print("distinct record_dates:", mt.shape[0], "| span:", mt.index.min().date(), "->", mt.index.max().date())
t12 = mt.rolling(12).sum()

def load(sid):
    df = pd.read_csv(os.path.join(FRED, f"{sid}.csv")); df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]); df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"]

gdp = load("GDP")
gdp_m = gdp.resample("ME").last().ffill()
df = pd.concat([t12.rename("int12"), gdp_m.rename("gdp")], axis=1).dropna()
df["burden"] = df["int12"] / (df["gdp"] * 1e9) * 100.0

air = pd.read_csv(os.path.join(TRE, "avg_interest_rates.csv"))
air["record_date"] = pd.to_datetime(air["record_date"])
air["avg_interest_rate_amt"] = pd.to_numeric(air["avg_interest_rate_amt"], errors="coerce")
print("air security_type:", air["security_type_desc"].unique())
eff = air[air["security_type_desc"] == "Interest-bearing Debt"].groupby("record_date")["avg_interest_rate_amt"].mean()

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(df.index, df["burden"], color="#8e44ad", lw=2, label="True interest burden (% GDP)")
ax.set_title("True debt-service burden: actual Treasury interest expense / GDP")
ax.set_ylabel("Interest burden (% of GDP)")
ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "11_true_interest_burden.png")); plt.close(fig)

summary = {
    "true_interest_burden_latest_pct": round(float(df["burden"].iloc[-1]), 2),
    "annual_interest_bn_latest": round(float(df["int12"].iloc[-1] / 1e9), 1),
    "effective_rate_latest_pct": round(float(eff.dropna().iloc[-1]), 2) if len(eff.dropna()) else None,
}
with open(os.path.join(OUT, "treasury.json"), "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
