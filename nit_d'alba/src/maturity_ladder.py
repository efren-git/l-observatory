"""maturity_ladder.py - refinancing cliff from Treasury auction data (with diagnostics)."""
import os, json, datetime
import requests, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "output")
TRE = os.path.join(BASE, "data", "raw", "treasury")
API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
today = datetime.date.today().isoformat()
rawpath = os.path.join(TRE, "auctions_outstanding.csv")

if os.path.exists(rawpath):
    df = pd.read_csv(rawpath)
else:
    rows = []
    page = 1
    while True:
        url = (f"{API}/v1/accounting/od/auctions_query"
               f"?filter=maturity_date:gte:{today}&page[size]=10000&page[number]={page}")
        js = requests.get(url, timeout=180).json()
        rows.extend(js["data"])
        tp = js.get("meta", {}).get("total-pages", 1)
        if page >= tp or page >= 20:
            break
        page += 1
    df = pd.DataFrame(rows)
    df.to_csv(rawpath, index=False)

print("cols:", [c for c in df.columns if "amt" in c or "outstanding" in c or "accepted" in c])
for c in ["currently_outstanding", "total_accepted", "offering_amt", "est_pub_held_mat_by_type_amt"]:
    if c in df.columns:
        v = pd.to_numeric(df[c], errors="coerce")
        print(f"  {c:34s} nonnull={v.notna().sum():5d} sum={v.sum()/1e12:7.3f}T")

df["maturity_date"] = pd.to_datetime(df["maturity_date"], errors="coerce")
df["auction_date"] = pd.to_datetime(df["auction_date"], errors="coerce")
df = df.dropna(subset=["maturity_date"]).sort_values("auction_date").drop_duplicates("cusip", keep="last")
amt = pd.to_numeric(df["currently_outstanding"], errors="coerce")
if "total_accepted" in df.columns:
    amt = amt.fillna(pd.to_numeric(df["total_accepted"], errors="coerce"))
df["out"] = amt.fillna(0)
df["mat_year"] = df["maturity_date"].dt.year

print("rows after dedupe:", len(df), "| types:", df["security_type"].value_counts().to_dict())
ladder = df.groupby("mat_year")["out"].sum() / 1e12
total = float(df["out"].sum()) / 1e12
next12 = float(df[df["maturity_date"] < pd.Timestamp(today) + pd.DateOffset(years=1)]["out"].sum()) / 1e12
print("TOTAL from auctions: %.2fT | next 12m: %.2fT" % (total, next12))

summary = {
    "total_outstanding_from_auctions_trillion": round(total, 2),
    "maturing_next_12_months_trillion": round(next12, 2),
    "by_year": {str(int(k)): round(float(v), 3) for k, v in ladder.items()},
}
print(json.dumps(summary, indent=2))

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.bar([str(int(x)) for x in ladder.index], ladder.values, color="#e67e22")
ax.set_title("The refinancing wall: Treasury debt maturing by year (from auction data)")
ax.set_ylabel("$ trillion")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "15_maturity_ladder.png")); plt.close(fig)
with open(os.path.join(OUT, "maturity.json"), "w") as f:
    json.dump(summary, f, indent=2)
