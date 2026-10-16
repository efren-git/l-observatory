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

# CBOE publishes the VIX term structure (its own index family) for free.  The VIX *futures*
# settlement files are behind AccessDenied, so the VRP sleeve is built from implied vol
# (these indices) versus realized vol -- the honest academic route.
CBOE = {
    "vix9d": "VIX9D_History.csv",
    "vix": "VIX_History.csv",
    "vix3m": "VIX3M_History.csv",
    "vix6m": "VIX6M_History.csv",
}
CBOE_BASE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/"
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


def fetch_cboe(force=False):
    out = os.path.join(RAW, "cboe_vix_term.csv")
    if os.path.exists(out) and not force:
        print("cboe_vix_term.csv present: skip")
        return
    frames = {}
    for key, fname in CBOE.items():
        req = urllib.request.Request(CBOE_BASE + fname, headers=_UA)
        txt = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
        df = pd.read_csv(io.StringIO(txt))
        df.columns = [c.strip().upper() for c in df.columns]
        dcol = df.columns[0]
        df[dcol] = pd.to_datetime(df[dcol], errors="coerce")
        df = df.dropna(subset=[dcol]).set_index(dcol)
        frames[key] = df["CLOSE"].astype(float)
        time.sleep(1)
    term = pd.concat(frames, axis=1).sort_index()
    term.index.name = "Date"
    term.to_csv(out)
    print("wrote", out, term.shape, "from", term.dropna().index[0].date(),
          "to", term.index[-1].date())


# --- carry inputs -----------------------------------------------------------
# Bond carry needs the Treasury curve; FX carry needs short rates for each currency.
# All free from FRED's CSV endpoint (no key; use the DEFAULT User-Agent -- custom UAs get
# throttled).  Commodity carry needs futures curves, which are not free -- not tested.
FRED_SERIES = {
    "dgs3mo": "DGS3MO", "dgs1": "DGS1", "dgs2": "DGS2", "dgs5": "DGS5",
    "dgs7": "DGS7", "dgs10": "DGS10", "dgs20": "DGS20", "dgs30": "DGS30",
    "fx_eur": "IR3TIB01EZM156N", "fx_jpy": "IR3TIB01JPM156N", "fx_gbp": "IR3TIB01GBM156N",
    "fx_aud": "IR3TIB01AUM156N", "fx_cad": "IR3TIB01CAM156N", "fx_chf": "IR3TIB01CHM156N",
    "fx_usd": "IR3TIB01USM156N",
}


def fetch_fred_carry(force=False):
    out = os.path.join(RAW, "fred_carry.csv")
    if os.path.exists(out) and not force:
        print("fred_carry.csv present: skip")
        return
    cols = {}
    for key, sid in FRED_SERIES.items():
        req = urllib.request.Request("https://fred.stlouisfed.org/graph/fredgraph.csv?id=" + sid)
        txt = urllib.request.urlopen(req, timeout=60).read().decode()
        df = pd.read_csv(io.StringIO(txt))
        df.columns = ["date", key]
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df[key] = pd.to_numeric(df[key], errors="coerce")
        cols[key] = df.dropna(subset=["date"]).set_index("date")[key]
        time.sleep(0.5)
    fr = pd.concat(cols, axis=1).sort_index()
    fr.index.name = "Date"
    fr = fr.ffill()          # daily curve: carry gaps on holidays
    fr.to_csv(out)
    print("wrote", out, fr.shape)


EQUITY_FOR_DIV = ["SPY", "QQQ", "IWM", "EFA", "EEM", "IWD", "IWF", "USMV", "SPLV",
                  "QUAL", "MTUM", "SPHB", "VNQ", "RWX"]


def fetch_dividends(force=False):
    out = os.path.join(RAW, "dividends.csv")
    if os.path.exists(out) and not force:
        print("dividends.csv present: skip")
        return
    import yfinance as yf
    ser = {}
    for t in EQUITY_FOR_DIV:
        try:
            d = yf.Ticker(t).dividends
            if d is not None and len(d):
                ser[t] = d
        except Exception as ex:
            print("div fail", t, ex)
        time.sleep(0.3)
    div = pd.DataFrame(ser)
    div.index = pd.to_datetime(div.index).tz_localize(None)   # yfinance gives tz-aware stamps
    div.index.name = "Date"
    div = div[div.index >= pd.Timestamp("2000-01-01")]
    div.to_csv(out)
    print("wrote", out, div.shape)


if __name__ == "__main__":
    force = "--force" in sys.argv
    fetch_prices(force)
    fetch_factors(force)
    fetch_cboe(force)
    fetch_fred_carry(force)
    fetch_dividends(force)
    print("done")
