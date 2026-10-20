"""Synthetic tests for the Phase 6 helpers and registered grid."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.phase6 import VARIANTS, _slice, fixed_book  # noqa: E402


class Phase6Test(unittest.TestCase):
    def test_registered_grid_size(self):
        self.assertEqual(len(VARIANTS), 12)
        self.assertIn("base", VARIANTS)
        self.assertIn("lb_6_12", VARIANTS)

    def test_fixed_book_weights(self):
        df = pd.DataFrame({
            "trend": [0.01, 0.02],
            "carry": [0.03, 0.04],
        }, index=pd.bdate_range("2020-01-01", periods=2))
        s = fixed_book(df, (0.75, 0.25))
        self.assertAlmostEqual(float(s.iloc[0]), 0.015)
        self.assertAlmostEqual(float(s.iloc[1]), 0.025)

    def test_slice_is_inclusive(self):
        idx = pd.bdate_range("2020-01-01", periods=10)
        s = pd.Series(range(10), index=idx)
        out = _slice(s, "2020-01-02", "2020-01-05")
        self.assertEqual(len(out), 2)


if __name__ == "__main__":
    unittest.main()
