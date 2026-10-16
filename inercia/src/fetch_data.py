"""fetch_data.py - expanded multi-asset ETF universe for inercia."""
import os
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw", "prices")
os.makedirs(RAW, exist_ok=True)

TICKERS = [
    # broad equity / size
    "SPY", "IWM", "MDY",
    # US sectors
    "XLB", "XLE", "XLF", "XLI", "XLK", "XLP", "XLU", "XLV", "XLY",
    # industries
    "SMH", "KRE", "XBI", "XRT", "XOP", "XME", "ITB", "IYT", "XHB",
    # developed / emerging country
    "EFA", "EEM", "EWJ", "EWU", "EWG", "EWC", "EWA", "EWH", "EWS", "EWT",
    "EWY", "EWZ", "EWW", "EWM", "EWP", "EWL", "EWD", "EWI", "EWO", "EWN",
    "EZA", "FXI", "INDA",
    # fixed income
    "TLT", "IEF", "SHY", "LQD", "HYG", "TIP", "EMB",
    # commodities / metals
    "GLD", "SLV", "DBC", "USO", "DBA",
    # real estate
    "VNQ", "IYR",
    # FX
    "FXE", "FXY", "FXB", "FXC", "UUP",
]

data = yf.download(TICKERS, start="2004-01-01", interval="1d", auto_adjust=True, progress=False)
ok = 0
for t in TICKERS:
    try:
        df = data.xs(t, level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if df["Close"].notna().sum() > 100:
            df.to_csv(os.path.join(RAW, f"{t}.csv"))
            ok += 1
    except Exception:
        pass
print(f"{ok}/{len(TICKERS)} ETFs saved")
