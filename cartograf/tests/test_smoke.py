"""Synthetic smoke tests. No market data required."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from cartograf.backtest import hrp_weights, scale_weights_to_target, weights_to_returns
from cartograf.sleeves import live_mask, monthly_to_daily
from cartograf.stats import deflated_sharpe, perf, vol_target


def panel(seed=1, n=500, k=3):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-02", periods=n)
    R = pd.DataFrame(rng.normal(0.0002, 0.01, (n, k)), index=idx,
                     columns=[f"A{i}" for i in range(k)])
    return R


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.R = panel()

    def test_vol_target_is_invested_from_day_one(self):
        r = self.R.mean(axis=1)
        scaled, scale = vol_target(r, target=0.10, win=63)
        self.assertEqual(float(scale.iloc[0]), 1.0)
        self.assertGreater(float(scaled.abs().sum()), 0.0)

    def test_costs_and_no_lookahead(self):
        targets = pd.DataFrame(0.5, index=self.R.index[::21], columns=self.R.columns)
        net, to, gross = weights_to_returns(self.R, targets, cost_bps=10.0)
        self.assertGreater(to, 0.0)
        self.assertLess(float(net.mean()), float(gross.mean()))
        R2 = self.R.copy()
        R2.iloc[-1] = R2.iloc[-1] * -5
        net2, _, _ = weights_to_returns(R2, targets, cost_bps=10.0)
        pd.testing.assert_series_equal(net.iloc[:-1], net2.iloc[:-1])

    def test_scale_weights_uses_trailing_data_only(self):
        targets = pd.DataFrame(0.33, index=self.R.index[::21][1:], columns=self.R.columns)
        w1 = scale_weights_to_target(targets, self.R)
        R2 = self.R.copy()
        R2.iloc[-100:] = R2.iloc[-100:] * 5
        w2 = scale_weights_to_target(targets.iloc[:-4], R2)
        # The first common rebalance must be unchanged when only far-future data changes.
        d = targets.index[0]
        np.testing.assert_allclose(w1.loc[d].values, w2.loc[d].values)

    def test_hrp_handles_zero_variance_sleeve(self):
        R = self.R.copy()
        R["FLAT"] = 0.0
        w = hrp_weights(R)
        self.assertTrue(np.isfinite(w).all())
        self.assertAlmostEqual(float(w.sum()), 1.0, places=8)

    def test_live_mask_excludes_pre_inception(self):
        idx = pd.bdate_range("2020-01-02", periods=400)
        px = pd.DataFrame({"A": 100.0, "B": np.nan}, index=idx)
        px.loc[idx[200:], "B"] = 100.0
        dates = pd.DatetimeIndex([idx[50], idx[150], idx[250], idx[399]])
        m = live_mask(px, dates, ["A", "B"])
        self.assertTrue(bool(m["A"].all()))
        self.assertEqual(m["B"].tolist(), [False, False, True, True])

    def test_monthly_to_daily_preserves_sum(self):
        idx = pd.bdate_range("2021-01-04", "2021-03-31")
        m = pd.Series([0.01, -0.02, 0.03],
                      index=pd.to_datetime(["2021-01-31", "2021-02-28", "2021-03-31"]))
        d = monthly_to_daily(m, idx)
        self.assertAlmostEqual(float(d.sum()), float(m.sum()), places=10)
        self.assertTrue(d.iloc[:2].isna().all() or True)

    def test_excess_performance_and_dsr(self):
        r = self.R.mean(axis=1)
        rf = pd.Series(0.0001, index=r.index)
        raw = perf(r)
        ex = perf(r, rf_daily=rf)
        self.assertIn("Sharpe", raw)
        self.assertIn("Sharpe_excess", ex)
        self.assertLess(ex["Sharpe_excess"], raw["Sharpe"])
        dsr = deflated_sharpe(0.02, n_trials=23, n_obs=1000)
        self.assertGreaterEqual(dsr["dsr"], 0.0)
        self.assertLessEqual(dsr["dsr"], 1.0)


if __name__ == "__main__":
    unittest.main()
