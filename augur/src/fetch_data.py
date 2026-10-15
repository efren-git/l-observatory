"""fetch_data.py - prices (yfinance) + macro (FRED) for augur."""
import os
import requests
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
os.makedirs(os.path.join(RAW, "prices"), exist_ok=True)
os.makedirs(os.path.join(RAW, "fred"), exist_ok=True)

TICKERS = ["SPY", "AAPL", "MSFT", "NVDA", "JPM", "XOM", "JNJ", "WMT", "KO", "DIS"]
data = yf.download(TICKERS, start="2005-01-01", interval="1d", auto_adjust=True, progress=False)
for t in TICKERS:
    df = data.xs(t, level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
    df.to_csv(os.path.join(RAW, "prices", f"{t}.csv"))
print("prices:", {t: int(data.xs(t, level=1, axis=1)["Close"].notna().sum()) for t in TICKERS})

for sid in ["DGS10", "VIXCLS", "DCOILWTICO", "CPIAUCSL", "FEDFUNDS"]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    with open(os.path.join(RAW, "fred", f"{sid}.csv"), "w") as f:
        f.write(r.text)
    print("fred", sid, len(r.text.splitlines()), "lines")
