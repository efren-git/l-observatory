"""war_study.py - do oil shocks follow wars? (the war/conflict module)."""
import os, json
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "fred")
OUT = os.path.join(BASE, "output")

def load_monthly(sid):
    df = pd.read_csv(os.path.join(RAW, f"{sid}.csv")); df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"]); df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna().set_index("date")["value"].resample("ME").mean()

oil = load_monthly("WTISPLC")

events = [
    ("1973-10-06", "Yom Kippur War / oil embargo"),
    ("1979-01-16", "Iranian Revolution"),
    ("1980-09-22", "Iran-Iraq War"),
    ("1990-08-02", "Gulf War"),
    ("2003-03-20", "Iraq War"),
    ("2011-02-15", "Arab Spring / Libya"),
    ("2022-02-24", "Russia invades Ukraine"),
    ("2023-10-07", "Israel-Hamas War"),
]

def px(ts):
    w = oil.loc[:ts]
    return float(w.iloc[-1]) if len(w) else None

rows = []
for ds, name in events:
    d = pd.Timestamp(ds)
    p0 = px(d); p1 = px(d + pd.DateOffset(months=6))
    chg = round((p1 / p0 - 1) * 100, 1) if (p0 and p1) else None
    rows.append({"date": ds, "event": name,
                 "oil_at": round(p0, 1) if p0 else None,
                 "oil_+6m": round(p1, 1) if p1 else None,
                 "pct_6m": chg})

fig, ax = plt.subplots(figsize=(12, 6))
ax.plot(oil.index, oil.values, color="#16a085", lw=1.3, zorder=1)
ymax = float(oil.max())
for ds, name in events:
    d = pd.Timestamp(ds)
    if d >= oil.index.min() and d <= oil.index.max():
        ax.axvline(d, color="#c0392b", ls=":", lw=1, alpha=0.6, zorder=0)
        ax.annotate(name.split(" / ")[0], (d, ymax), rotation=90, fontsize=7,
                    ha="right", va="top", color="#7b241c")
ax.set_title("Oil price and major conflicts / energy shocks (WTI, monthly)")
ax.set_ylabel("USD per barrel")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "09_war_oil.png")); plt.close(fig)

with open(os.path.join(OUT, "war_study.json"), "w") as f:
    json.dump(rows, f, indent=2)
for rr in rows:
    print(rr)
