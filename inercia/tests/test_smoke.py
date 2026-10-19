"""Synthetic smoke tests. No real market data is committed or required."""
import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from inercia.backtest import panel_backtest
from inercia.signals import ts_momentum, xs_momentum
from inercia.stats import deflated_sharpe, perf, vol_target


def synthetic_panel(seed=0, n=420, k=4):
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2020-01-02", periods=n)
    ret = pd.DataFrame(rng.normal(0.0002, 0.01, (n, k)), index=idx,
                       columns=[f"A{i}" for i in range(k)])
    px = 100.0 * (1 + ret).cumprod()
    return px, px.pct_change()


class SmokeTest(unittest.TestCase):
    def setUp(self):
        self.px, self.ret = synthetic_panel()

    def test_signals_are_finite_and_bounded(self):
        ts = ts_momentum(self.px)
        xs = xs_momentum(self.px)
        self.assertEqual(ts.shape, self.px.shape)
        self.assertTrue(np.isfinite(ts.dropna()).all().all())
        self.assertTrue(set(xs.dropna().stack().unique()).issubset({-1.0, 0.0, 1.0}))

    def test_backtest_charges_costs_and_reports_turnover(self):
        w = xs_momentum(self.px)
        net, diag = panel_backtest(w, self.ret, cost_bps=10.0)
        gross, _ = panel_backtest(w, self.ret, cost_bps=0.0)
        self.assertTrue(np.isfinite(net.dropna()).all())
        self.assertGreater(diag["annual_turnover"], 0.0)
        self.assertGreater(float((gross - net).mean()), 0.0)
        self.assertIsInstance(perf(net), dict)
        self.assertIn("Sharpe", perf(net))

    def test_no_lookahead_from_last_return(self):
        w = xs_momentum(self.px)
        net, _ = panel_backtest(w, self.ret, cost_bps=10.0)
        ret2 = self.ret.copy()
        ret2.iloc[-1] = ret2.iloc[-1] * -5.0
        net2, _ = panel_backtest(w, ret2, cost_bps=10.0)
        pd.testing.assert_series_equal(net.iloc[:-1], net2.iloc[:-1])

    def test_vol_target_and_dsr(self):
        r = self.ret.mean(axis=1)
        scaled, scale = vol_target(r, target=0.10)
        self.assertTrue(np.isfinite(scaled.dropna()).all())
        self.assertTrue((scale.dropna() >= 0).all())
        dsr = deflated_sharpe(0.02, n_trials=10, n_obs=1000)
        self.assertGreaterEqual(dsr["dsr"], 0.0)
        self.assertLessEqual(dsr["dsr"], 1.0)


if __name__ == "__main__":
    unittest.main()
