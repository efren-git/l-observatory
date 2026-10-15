"""fetch_stocks.py - broad US equity universe for the XS sleeve."""
import os, io
import requests
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "stocks")
os.makedirs(RAW, exist_ok=True)

url = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
r = requests.get(url, timeout=30); r.raise_for_status()
with open(os.path.join(RAW, "sp500_constituents.csv"), "w") as f:
    f.write(r.text)
cons = pd.read_csv(io.StringIO(r.text))
sym = cons["Symbol"].str.replace(".", "-", regex=False).tolist()
print("constituents:", len(sym))

data = yf.download(sym, start="2005-01-01", interval="1d", auto_adjust=True, progress=False, threads=True)
ok = 0
for t in sym:
    try:
        df = data.xs(t, level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if df["Close"].notna().sum() > 500:
            df.to_csv(os.path.join(RAW, f"{t}.csv")); ok += 1
    except Exception:
        pass
print(f"{ok}/{len(sym)} stocks saved; range {str(data.index.min().date())} -> {str(data.index.max().date())}")
