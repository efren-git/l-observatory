"""fetch_carry.py - G10 short rates (FRED) + FX prices (yfinance) for the carry engine."""
import os
import requests
import yfinance as yf
import pandas as pd

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
os.makedirs(os.path.join(RAW, "fred"), exist_ok=True)
os.makedirs(os.path.join(RAW, "fx"), exist_ok=True)

RATES = {"US":"IR3TIB01USM156N","EU":"IR3TIB01EZM156N","JP":"IR3TIB01JPM156N","UK":"IR3TIB01GBM156N",
         "CA":"IR3TIB01CAM156N","AU":"IR3TIB01AUM156N","CH":"IR3TIB01CHM156N","NZ":"IR3TIB01NZM156N",
         "SE":"IR3TIB01SEM156N","NO":"IR3TIB01NOM156N"}
for k, s in RATES.items():
    r = requests.get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={s}", timeout=30)
    r.raise_for_status()
    with open(os.path.join(RAW, "fred", f"rate_{k}.csv"), "w") as f:
        f.write(r.text)
print("rates saved:", len(RATES))

PAIRS = {"EUR":"EURUSD=X","JPY":"USDJPY=X","GBP":"GBPUSD=X","CAD":"USDCAD=X","AUD":"AUDUSD=X",
         "CHF":"USDCHF=X","NZD":"NZDUSD=X","SEK":"USDSEK=X","NOK":"USDNOK=X"}
data = yf.download(list(PAIRS.values()), start="2003-01-01", interval="1d", auto_adjust=True, progress=False)
ok = 0
for k, pair in PAIRS.items():
    try:
        df = data.xs(pair, level=1, axis=1) if isinstance(data.columns, pd.MultiIndex) else data
        if df["Close"].notna().sum() > 100:
            df.to_csv(os.path.join(RAW, "fx", f"{k}.csv")); ok += 1
    except Exception as e:
        print("skip", k, str(e)[:40])
print(f"{ok}/{len(PAIRS)} FX saved; range {str(data.index.min().date())} -> {str(data.index.max().date())}")
