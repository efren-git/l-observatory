"""fetch_data.py - free daily data for the cartograf book.

Sources (all free, no keys):
  * Yahoo Finance via the yfinance client -- adjusted daily closes for a liquid
    multi-asset ETF universe (this is the route already proven in the other books).
  * Ken French Data Library -- equity factor returns (market/size/value/profitability/
    investment/momentum) for the defensive and value cross-checks.

Everything lands as CSV under data/raw/. Re-run is safe: existing files are reused
unless --force is passed.

Usage:  ./.venv/bin/python3 src/fetch_data.py [--force]
"""
import io
import os
import sys
import time
import zipfile
import urllib.request

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = os.path.join(ROOT, "data", "raw")
os.makedirs(RAW, exist_ok=True)

# --- The universe: liquid ETFs, one row per instrument we are willing to trade. ---
# Groups matter later (a sleeve is scored inside its own group).
UNIVERSE = {
    # --- equities: regions / styles ---
    "SPY": "equity_us", "QQQ": "equity_us", "IWM": "equity_us",
    "EFA": "equity_dev", "EEM": "equity_em",
    "IWD": "equity_style", "IWF": "equity_style", "MTUM": "equity_style",
    "QUAL": "equity_style", "USMV": "equity_style", "SPLV": "equity_style",
    "SPHB": "equity_style",
    # --- fixed income ---
    "SHY": "bond", "IEF": "bond", "TLT": "bond",
    "TIP": "bond", "LQD": "bond", "HYG": "bond", "EMB": "bond", "BNDX": "bond",
    # --- commodities ---
    "DBC": "commodity", "GSG": "commodity", "DBA": "commodity",
    "USO": "commodity", "UNG": "commodity",
    "GLD": "metal", "SLV": "metal", "CPER": "metal",
    # --- FX (USD-priced) ---
    "FXE": "fx", "FXY": "fx", "FXB": "fx", "FXA": "fx", "FXC": "fx", "FXF": "fx",
    # --- real estate ---
    "VNQ": "reit", "RWX": "reit",
    # --- volatility (for the volatility-risk-premium sleeve) ---
    "SVXY": "vol", "VXX": "vol",
}

# Volatility indices and yields are context, not traded instruments.
CONTEXT = ["^VIX", "^VIX3M", "^VIX9D", "^VXN", "^TNX"]

FF_FILES = {
    "ff3": "F-F_Research_Data_Factors_CSV.zip",
    "ff5": "F-F_Research_Data_5_Factors_2x3_CSV.zip",
    "ffmom": "F-F_Momentum_Factor_CSV.zip",
}
FF_BASE = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/"
_UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}


def fetch_prices(force=False):
    out = os.path.join(RAW, "prices.csv")
    if os.path.exists(out) and not force:
        print("prices.csv present: skip (use --force to refetch)")
        return
    import yfinance as yf

    tickers = list(UNIVERSE) + CONTEXT
    frames = []
    for attempt in range(4):
        df = yf.download(tickers, start="2003-01-01", auto_adjust=True,
                         progress=False, threads=True)
        close = df["Close"] if isinstance(df.columns, pd.MultiIndex) else df[["Close"]]
        close = close.dropna(how="all")
        if close.shape[1] >= len(tickers) - 6:
            frames.append(close)
            break
        print(f"attempt {attempt}: got {close.shape[1]}/{len(tickers)} columns, retry")
        time.sleep(5)
    close = frames[-1] if frames else close
    close.index.name = "Date"
    close.to_csv(out)
    print("wrote", out, close.shape)
    miss = [t for t in tickers if t not in close.columns]
    if miss:
        print("missing tickers:", miss)


def _parse_ff(text):
    """Ken French CSVs: prose header, then a monthly block, then an annual block."""
    lines = text.splitlines()
    start = None
    for i, ln in enumerate(lines):
        head = ln.split(",")[0].strip()
        if head.isdigit() and len(head) in (6, 8):
            start = i
            break
    if start is None:
        raise ValueError("no monthly block found")
    cols = [c.strip() for c in lines[start - 1].split(",")]
    rows, dates = [], []
    for ln in lines[start:]:
        parts = [p.strip() for p in ln.split(",")]
        if not parts[0].isdigit() or len(parts[0]) != 6:
            break  # annual block or blank line ends the monthly section
        dates.append(parts[0])
        rows.append([float(x) if x not in ("", "-99.99") else float("nan") for x in parts[1:]])
    df = pd.DataFrame(rows, columns=cols[1:], index=pd.to_datetime(dates, format="%Y%m"))
    df = df / 100.0  # percent -> decimal
    return df


def fetch_factors(force=False):
    for key, fname in FF_FILES.items():
        out = os.path.join(RAW, f"ff_{key}.csv")
        if os.path.exists(out) and not force:
            print(f"ff_{key}.csv present: skip")
            continue
        req = urllib.request.Request(FF_BASE + fname, headers=_UA)
        blob = urllib.request.urlopen(req, timeout=60).read()
        zf = zipfile.ZipFile(io.BytesIO(blob))
        txt = zf.read(zf.namelist()[0]).decode("latin-1")
        df = _parse_ff(txt)
        df.to_csv(out)
        print("wrote", out, df.shape, "from", df.index[0].date(), "to", df.index[-1].date())
        time.sleep(1)


if __name__ == "__main__":
    force = "--force" in sys.argv
    fetch_prices(force)
    fetch_factors(force)
    print("done")
