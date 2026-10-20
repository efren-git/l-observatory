"""Phase 7 mechanics: signed hedge, drift, costs, no look-ahead."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.phase7 import hedge_series, marginal, vol_matched


def panel(n=60, base=0.005, asset=0.01):
    idx = pd.period_range("2015-01", periods=n, freq="M")
    return (pd.Series(base, index=idx), pd.Series(asset, index=idx),
            pd.Series(0.0, index=idx), idx)


class HedgeTest(unittest.TestCase):
    def test_short_hedge_costs_money_when_asset_rises(self):
        b, a, rf, idx = panel()
        h = hedge_series(b, a, rf, 0.10, 5.0, sign=-1)
        self.assertLess(float(h.mean()), float(b.mean()))
        # 10% short of a +1%/month asset is about -0.1%/month, plus costs.
        self.assertAlmostEqual(float((b - h).mean()), 0.001, places=4)

    def test_long_hedge_adds_when_asset_rises(self):
        b, a, rf, idx = panel()
        h = hedge_series(b, a, rf, 0.10, 5.0, sign=+1)
        self.assertGreater(float(h.mean()), float(b.mean()))

    def test_no_lookahead_from_last_month(self):
        b, a, rf, idx = panel()
        h1 = hedge_series(b, a, rf, 0.10, 5.0, sign=-1)
        a2 = a.copy()
        a2.iloc[-1] = -0.50
        h2 = hedge_series(b, a2, rf, 0.10, 5.0, sign=-1)
        pd.testing.assert_series_equal(h1.iloc[:-1], h2.iloc[:-1])

    def test_costs_are_monotone(self):
        b, a, rf, idx = panel(asset=-0.01)
        h0 = hedge_series(b, a, rf, 0.10, 0.0, sign=-1)
        h25 = hedge_series(b, a, rf, 0.10, 25.0, sign=-1)
        self.assertGreater(float(h0.mean()), float(h25.mean()))

    def test_marginal_and_vol_matched_are_finite(self):
        b, a, rf, idx = panel(n=48)
        h = hedge_series(b, a, rf, 0.05, 5.0, sign=-1)
        m = marginal(b, h)
        self.assertIn("t_stat", m)
        self.assertIn("dsr_all_trials", m)
        vm = vol_matched({"Vol": 0.10, "MaxDD": -0.20}, {"Vol": 0.09, "MaxDD": -0.18})
        self.assertAlmostEqual(vm["proportional_maxdd"], -0.18, places=6)


if __name__ == "__main__":
    unittest.main()
