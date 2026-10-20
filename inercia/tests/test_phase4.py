"""Synthetic tests for the Phase 4 robustness helpers."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.phase4 import block_cpcv, rolling_sharpe  # noqa: E402


def monthly(seed=0, n=96, mu=0.006, sd=0.02):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2018-01", periods=n, freq="M")
    return pd.Series(rng.normal(mu, sd, n), index=idx)


class Phase4Test(unittest.TestCase):
    def test_block_cpcv_distribution(self):
        out = block_cpcv(monthly(), n_blocks=6, k=2, purge=1)
        self.assertEqual(out["n_splits"], 15)
        self.assertLessEqual(out["min"], out["median"])
        self.assertLessEqual(out["median"], out["max"])
        self.assertGreaterEqual(out["pct_positive"], 0.0)
        self.assertLessEqual(out["pct_positive"], 1.0)

    def test_rolling_sharpe_keys(self):
        out = rolling_sharpe(monthly(), window=36)
        self.assertEqual(out["window"], 36)
        self.assertLessEqual(out["min"], out["median"])
        self.assertLessEqual(out["median"], out["max"])


if __name__ == "__main__":
    unittest.main()
