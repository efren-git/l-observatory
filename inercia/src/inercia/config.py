"""Project paths and shared defaults."""
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
RAW = BASE / "data" / "raw"
OUT = BASE / "output"
OUT.mkdir(parents=True, exist_ok=True)

M = 21                    # trading days per month
TARGET_VOL = 0.10
COST_BPS = 5.0            # ETF sleeves
STOCK_COST_BPS = 10.0     # single-name sleeve
VOL_WINDOW = 60
VOL_LOOKBACK = 20
MAX_LEVERAGE = 3.0
RATE_LAG_MONTHS = 2       # publication-safe lag for FRED monthly averages
