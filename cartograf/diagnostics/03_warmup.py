"""Diagnostic: the old vol-target warm-up put the book in cash.

Run: ./.venv/bin/python3 diagnostics/03_warmup.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cartograf.data import prices  # noqa: E402
from cartograf.stats import perf, vol_target  # noqa: E402


def old_vol_target(daily, target=0.10, win=63, cap=4.0):
    d = pd.Series(daily).fillna(0.0)
    vol = d.rolling(win).std() * np.sqrt(252)
    scale = (target / vol.replace(0, np.nan)).clip(upper=cap).shift(1).fillna(0.0)
    return d * scale, scale


def main():
    spy = prices()["SPY"].pct_change().dropna()
    old, old_scale = old_vol_target(spy)
    new, new_scale = vol_target(spy, target=0.10, win=63)
    out = {
        "input": {"name": "SPY daily returns", "n": int(len(spy)),
                  "start": str(spy.index[0].date()), "end": str(spy.index[-1].date())},
        "old_first_nonzero_scale": str(old_scale[old_scale > 0].index[0].date()),
        "old_zero_days": int((old_scale == 0).sum()),
        "new_first_scale_value": round(float(new_scale.iloc[0]), 4),
        "old_stats": perf(old),
        "new_stats": perf(new),
        "interpretation": "Old code was flat for the first 63 trading days; new code "
                          "is invested at unit size until the first vol estimate exists.",
    }
    (ROOT / "diagnostics" / "warmup_diagnostic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
