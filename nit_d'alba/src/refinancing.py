"""refinancing.py - refinancing exposure from Treasury securities outstanding."""
import os, json
import pandas as pd, numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRE = os.path.join(BASE, "data", "raw", "treasury")
OUT = os.path.join(BASE, "output")

d = pd.read_csv(os.path.join(TRE, "securities_outstanding.csv"))
d["record_date"] = pd.to_datetime(d["record_date"])
d["amt"] = pd.to_numeric(d["securities_outstanding_amt"], errors="coerce")
m = d[d["security_type_desc"] == "Marketable"]
p = m.pivot_table(index="record_date", columns="security_class_desc", values="amt", aggfunc="sum").sort_index()
p["Total"] = p.sum(axis=1)
ch = "Bill" if "Bill" in p.columns else None
if ch:
    p["bill_share"] = p[ch] / p["Total"] * 100.0

last = p.iloc[-1]
summary = {
    "date": str(p.index[-1].date()),
    "total_marketable_trillion": round(float(last["Total"]) / 1e12, 3),
    "bills_trillion": round(float(last.get("Bill", 0)) / 1e12, 3),
    "bill_share_pct": round(float(last.get("bill_share", 0)), 1),
    "notes_trillion": round(float(last.get("Note", 0)) / 1e12, 3),
    "bonds_trillion": round(float(last.get("Bond", 0)) / 1e12, 3),
}
print(json.dumps(summary, indent=2))

cols = [c for c in ["Bill", "Note", "Bond", "TIPS", "FRN"] if c in p.columns]
fig, ax = plt.subplots(figsize=(11, 5.5))
ax.stackplot(p.index, [p[c] / 1e12 for c in cols], labels=cols, alpha=0.85)
ax.set_title("Marketable Treasury debt by type (short-term bills = the refinancing exposure)")
ax.set_ylabel("$ trillion")
ax.legend(loc="upper left")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "14_refinancing.png")); plt.close(fig)

with open(os.path.join(OUT, "refinancing.json"), "w") as f:
    json.dump(summary, f, indent=2)
