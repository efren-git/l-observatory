"""Merger-arb spread math, sizing and risk tiers."""
import sys
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from merger_arb import Deal, evaluate, risk_tier


def deal(**kw):
    base = dict(
        deal_id="T", target="TGT", acquirer="ACQ", structure="cash",
        cash_per_share=100.0, exchange_ratio=0.0,
        announce_date=pd.Timestamp("2026-01-01"),
        expected_close=pd.Timestamp("2026-04-01"),
        status="pending", pre_announce_price=80.0,
        regulatory_risk=1, financing_risk=1, shareholder_risk=1, timing_risk=1,
        notes="",
    )
    base.update(kw)
    return Deal(**base)


class MergerArbTest(unittest.TestCase):
    def test_cash_spread_and_annualisation(self):
        r = evaluate(deal(), target_price=95.0, acquirer_price=None,
                     today=pd.Timestamp("2026-01-01"))
        self.assertAlmostEqual(r["deal_value"], 100.0)
        self.assertAlmostEqual(r["gross_spread"], 0.0526, places=4)
        self.assertGreater(r["annualised"], 0.20)
        self.assertAlmostEqual(r["break_downside"], -0.1579, places=4)
        self.assertEqual(r["signal"], "enter")

    def test_stock_needs_acquirer_price(self):
        r = evaluate(deal(structure="stock", cash_per_share=0.0,
                          exchange_ratio=0.5),
                     target_price=90.0, acquirer_price=None)
        self.assertEqual(r["signal"], "no data")

    def test_stock_deal_value(self):
        r = evaluate(deal(structure="stock", cash_per_share=0.0,
                          exchange_ratio=0.5),
                     target_price=90.0, acquirer_price=200.0)
        self.assertAlmostEqual(r["deal_value"], 100.0)
        self.assertAlmostEqual(r["gross_spread"], 0.1111, places=4)

    def test_mixed_deal_value(self):
        r = evaluate(deal(structure="mixed", cash_per_share=20.0,
                          exchange_ratio=0.4),
                     target_price=90.0, acquirer_price=200.0)
        self.assertAlmostEqual(r["deal_value"], 100.0)

    def test_risk_tiers(self):
        self.assertEqual(risk_tier(8), "A")
        self.assertEqual(risk_tier(12), "B")
        self.assertEqual(risk_tier(13), "C")

    def test_position_size_is_capped(self):
        r = evaluate(deal(pre_announce_price=95.0), target_price=100.0,
                     acquirer_price=None)
        self.assertAlmostEqual(r["position_pct"], 10.0)
        r = evaluate(deal(pre_announce_price=80.0), target_price=100.0,
                     acquirer_price=None)
        self.assertAlmostEqual(r["position_pct"], 5.0)

    def test_high_risk_passes(self):
        r = evaluate(deal(regulatory_risk=5, financing_risk=5,
                          shareholder_risk=5, timing_risk=5),
                     target_price=95.0, acquirer_price=None)
        self.assertEqual(r["signal"], "pass")


if __name__ == "__main__":
    unittest.main()
