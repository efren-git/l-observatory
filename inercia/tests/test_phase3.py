"""Synthetic tests for the Phase 3 book construction."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.phase3 import (  # noqa: E402
    _to_monthly, equal_targets, invvol_targets, rebalanced_returns,
)


def panel(seed=0, n=48, k=3):
    rng = np.random.default_rng(seed)
    idx = pd.period_range("2020-01", periods=n, freq="M")
    R = pd.DataFrame(rng.normal(0.002, 0.02, (n, k)), index=idx,
                     columns=["A", "B", "C"][:k])
    live = pd.DataFrame(True, index=idx, columns=R.columns)
    return R, live


class Phase3Test(unittest.TestCase):
    def setUp(self):
        self.R, self.live = panel()

    def test_equal_targets_are_lagged(self):
        w = equal_targets(self.R, self.live)
        self.assertEqual(float(w.iloc[0].sum()), 0.0)
        self.assertAlmostEqual(float(w.iloc[1].sum()), 1.0)

    def test_invvol_weights_are_long_only_and_never_geared(self):
        w = invvol_targets(self.R, self.live, lookback=6, min_obs=3)
        self.assertTrue((w >= 0).all().all())
        self.assertTrue((w.sum(axis=1) <= 1.0 + 1e-12).all())

    def test_rebalancing_costs_reduce_return(self):
        tgt = pd.DataFrame(1.0 / self.R.shape[1], index=self.R.index,
                           columns=self.R.columns)
        gross = rebalanced_returns(self.R, tgt, cost_bps=0.0)
        net = rebalanced_returns(self.R, tgt, cost_bps=10.0)
        self.assertLess(float(net.mean()), float(gross.mean()))

    def test_no_lookahead_from_last_return(self):
        tgt = pd.DataFrame(1.0 / self.R.shape[1], index=self.R.index,
                           columns=self.R.columns)
        a = rebalanced_returns(self.R, tgt, cost_bps=5.0)
        R2 = self.R.copy()
        R2.iloc[-1] = R2.iloc[-1] * -5.0
        b = rebalanced_returns(R2, tgt, cost_bps=5.0)
        pd.testing.assert_series_equal(a.iloc[:-1], b.iloc[:-1])

    def test_monthly_conversion(self):
        idx = pd.bdate_range("2020-01-01", periods=60)
        s = pd.Series(0.001, index=idx)
        m = _to_monthly(s)
        self.assertIsInstance(m.index, pd.PeriodIndex)
        self.assertGreaterEqual(len(m), 2)


if __name__ == "__main__":
    unittest.main()
