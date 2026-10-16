"""fetch_market.py - market data via yfinance (Yahoo, proper session handling)."""
import os, json, time
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR = os.path.join(BASE, "data", "raw", "yahoo")
os.makedirs(OUTDIR, exist_ok=True)

SYMBOLS = {
    "NVDA": "NVIDIA", "MSFT": "Microsoft", "AAPL": "Apple", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "TSLA": "Tesla",
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite", "^NDX": "Nasdaq 100",
}
MAG7 = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "TSLA"]

for sym, label in SYMBOLS.items():
    try:
        h = yf.Ticker(sym).history(period="10y", interval="1mo")
        if len(h):
            h.reset_index().to_csv(os.path.join(OUTDIR, sym.replace("^", "").replace(".", "_") + ".csv"), index=False)
            print(f"OK   {sym:7s} {len(h):3d} rows  {label}")
        else:
            print(f"EMPTY {sym}")
    except Exception as e:
        print(f"FAIL {sym:7s} {str(e)[:60]}")
    time.sleep(1)

fundamentals = {}
for sym in MAG7:
    try:
        info = yf.Ticker(sym).info
        fundamentals[sym] = {
            "name": info.get("shortName"),
            "marketCap": info.get("marketCap"),
            "trailingPE": info.get("trailingPE"),
            "priceToSales": info.get("priceToSalesTrailing12Months"),
        }
        print(f"FUND {sym:7s} mcap={fundamentals[sym]['marketCap']} pe={fundamentals[sym]['trailingPE']}")
    except Exception as e:
        print(f"FUNDFAIL {sym:7s} {str(e)[:60]}")
    time.sleep(1)

with open(os.path.join(OUTDIR, "fundamentals.json"), "w") as f:
    json.dump(fundamentals, f, indent=2)
print(f"done -> {OUTDIR}")
