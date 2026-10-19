"""Project paths, constants and conventions."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / "data" / "raw"
OUT = BASE / "output"
OUT.mkdir(parents=True, exist_ok=True)

TD = 252
TARGET = 0.10
COST = 5.0              # bps per unit turnover, ETFs
COST_VOL = 10.0         # bps, volatility ETFs
START = "2008-01-01"    # value needs five years of prices
RATE_LAG_MONTHS = 2     # publication-safe lag for FRED monthly averages
