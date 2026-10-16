"""fetch_treasury.py - US Treasury Fiscal Data API (free, no key)."""
import os
import requests
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "data", "raw", "treasury")
os.makedirs(OUT, exist_ok=True)
API = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"

candidates = {
    "avg_interest_rates":   ("v2/accounting/od/avg_interest_rates", "page[size]=10000&sort=record_date"),
    "debt_to_penny":        ("v2/accounting/od/debt_to_penny", "page[size]=10000&sort=-record_date"),
    "interest_expense":     ("v2/accounting/od/interest_expense", "page[size]=10000&sort=record_date"),
    "mspd_table_3":         ("v1/accounting/mspd/mspd_table_3", "page[size]=10000"),
    "securities_outstanding": ("v1/accounting/od/securities_outstanding", "page[size]=10000"),
    "historic_debt":        ("v2/accounting/od/historical_debt_outstanding", "page[size]=10000"),
}

for name, (ep, params) in candidates.items():
    try:
        r = requests.get(f"{API}/{ep}?{params}", timeout=60)
        if r.status_code == 200:
            js = r.json()
            df = pd.DataFrame(js.get("data", []))
            if len(df):
                df.to_csv(os.path.join(OUT, f"{name}.csv"), index=False)
                print(f"OK   {name:24s} {len(df):6d} rows  cols={list(df.columns)[:6]}")
            else:
                print(f"OK   {name:24s} 0 rows")
        else:
            print(f"HTTP {r.status_code} {name}")
    except Exception as e:
        print(f"FAIL {name:24s} {str(e)[:70]}")
