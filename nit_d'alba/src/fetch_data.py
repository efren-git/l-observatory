"""fetch_data.py — download raw datasets from primary sources.

All sources are free and require no API key:
  - FRED: fredgraph.csv endpoints (St. Louis Fed)
  - World Bank: REST API
  - Stooq: daily price CSV

Output: data/raw/<source>/<id>.csv
"""
import os
import requests
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
HEADERS = {}  # default requests UA — fredgraph.csv serves it; custom UAs get bot-throttled

results = []

def log(source, name, ok, note=""):
    results.append((source, name, ok, note))
    print(("OK   " if ok else "FAIL ") + f"{source:10s} {name:22s} {note}")

# ---------------------------------------------------------------- FRED ------
FRED_SERIES = {
    "DGS10":        "US 10-Year Treasury yield",
    "FEDFUNDS":     "Effective Federal Funds Rate",
    "CPIAUCSL":     "US CPI (all items)",
    "DCOILWTICO":   "WTI crude oil price",
    "DCOILBRENTEU": "Brent crude oil price",
    "GFDEBTN":      "US federal debt (total public)",
    "GDP":          "US nominal GDP",
    "T10YIE":       "10Y breakeven inflation",
    "DEXUSEU":      "USD/EUR exchange rate",
}

os.makedirs(os.path.join(RAW, "fred"), exist_ok=True)
for sid, label in FRED_SERIES.items():
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        path = os.path.join(RAW, "fred", f"{sid}.csv")
        with open(path, "w") as f:
            f.write(r.text)
        df = pd.read_csv(path)
        log("fred", sid, len(df) > 0, f"{len(df)} rows | {label}")
    except Exception as e:
        log("fred", sid, False, str(e)[:70])

# ---------------------------------------------------------- WORLD BANK ------
WB_COUNTRIES = ["US", "DE", "FR", "GB", "JP", "CN", "IT", "ES", "BR", "IN", "TR", "AR", "GR", "KR"]
WB_INDICATORS = {
    "GC.DOD.TOTL.GD.ZS": "Central government debt (% of GDP)",
    "TM.VAL.FUEL.ZS.UN": "Fuel imports (% of merchandise imports)",
    "NY.GDP.MKTP.CD":    "GDP (current US dollars)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
}

os.makedirs(os.path.join(RAW, "worldbank"), exist_ok=True)
for ind, label in WB_INDICATORS.items():
    url = (
        "https://api.worldbank.org/v2/country/"
        + ";".join(WB_COUNTRIES)
        + f"/indicator/{ind}?format=json&per_page=20000&date=1990:2026"
    )
    try:
        r = requests.get(url, headers=HEADERS, timeout=60)
        r.raise_for_status()
        js = r.json()
        # js[0] = metadata, js[1] = rows
        rows = js[1] if len(js) > 1 and js[1] else []
        recs = []
        for row in rows:
            recs.append({
                "country": row["country"]["value"],
                "country_code": row["countryiso3code"],
                "year": row["date"],
                "value": row["value"],
            })
        df = pd.DataFrame(recs)
        path = os.path.join(RAW, "worldbank", f"{ind}.csv")
        df.to_csv(path, index=False)
        log("worldbank", ind, len(df) > 0, f"{len(df)} rows | {label}")
    except Exception as e:
        log("worldbank", ind, False, str(e)[:70])

# ---------------------------------------------------------------- STOOQ ------
STOOQ_SYMBOLS = {
    "nvda.us":  "NVIDIA",
    "msft.us":  "Microsoft",
    "aapl.us":  "Apple",
    "googl.us": "Alphabet",
    "amzn.us":  "Amazon",
    "meta.us":  "Meta",
    "tsla.us":  "Tesla",
    "^spx":     "S&P 500",
    "^ndx":     "Nasdaq 100",
}

os.makedirs(os.path.join(RAW, "stooq"), exist_ok=True)
for sym, label in STOOQ_SYMBOLS.items():
    url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        r.raise_for_status()
        path = os.path.join(RAW, "stooq", f"{sym.replace('^','').replace('.','_')}.csv")
        with open(path, "w") as f:
            f.write(r.text)
        df = pd.read_csv(path)
        log("stooq", sym, len(df) > 0, f"{len(df)} rows | {label}")
    except Exception as e:
        log("stooq", sym, False, str(e)[:70])

# ---------------------------------------------------------------- summary ---
ok = sum(1 for r in results if r[2])
print(f"\n=== {ok}/{len(results)} datasets fetched ===")
