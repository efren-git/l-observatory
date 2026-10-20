"""Merger-arbitrage deal tracker and spread calculator.

This is a live/paper tool, not a historical backtest. Free price data drops
delisted targets (confirmed: HES, PXD, DFS, ATVI, XLNX all return 404), so a
credible historical study needs a paid M&A database or a manually curated deal
set. What can be built honestly with free data is the part that matters for a
small book: the deal schema, the spread math, the break-risk scorecard and an
append-only paper ledger.

Mechanics
---------
A stock deal: buy the target, short the acquirer at the exchange ratio. The
target should trade below the deal value; the gap is the annualised return if
the deal closes. A cash deal: buy the target; the gap to cash is the time value
of completion risk. A mixed deal: cash + ratio * acquirer.

The spread is not free money. It is payment for completion risk: regulatory
block, financing failure, shareholder vote, a material adverse change, or a long
delay. The break downside is the target's fall back to its pre-announcement
price. Size by that loss, not by the spread.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "output"
OUT.mkdir(parents=True, exist_ok=True)
LEDGER = OUT / "paper_ledger.csv"

DEFAULT_MAX_POSITION = 10.0       # % of capital per deal
DEFAULT_RISK_BUDGET = 1.0         # % of capital lost if the deal breaks
MIN_ANNUALISED = 0.08             # 8% annualised gross spread
MAX_BREAK_DOWNSIDE = -0.20        # do not risk more than 20% on a break
MAX_RISK_POINTS = 12              # 4 categories, 1-5 each; 12 = tier B limit
MAX_GROSS_EXPOSURE = 40.0         # % of capital across all deals


@dataclass
class Deal:
    deal_id: str
    target: str
    acquirer: str
    structure: str
    cash_per_share: float
    exchange_ratio: float
    announce_date: pd.Timestamp
    expected_close: pd.Timestamp
    status: str
    pre_announce_price: float | None
    regulatory_risk: int
    financing_risk: int
    shareholder_risk: int
    timing_risk: int
    notes: str = ""


def _num(x, default=0.0) -> float:
    try:
        v = float(x)
        return v if np.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def load_deals(path: str | Path) -> list[Deal]:
    df = pd.read_csv(path)
    deals = []
    for _, row in df.iterrows():
        if str(row.get("status", "")).strip().lower() == "draft":
            continue
        structure = str(row["structure"]).strip().lower()
        if structure not in ("cash", "stock", "mixed"):
            raise ValueError(f"{row['deal_id']}: structure must be cash/stock/mixed")
        deals.append(Deal(
            deal_id=str(row["deal_id"]).strip(),
            target=str(row["target"]).strip().upper(),
            acquirer=str(row.get("acquirer", "")).strip().upper(),
            structure=structure,
            cash_per_share=_num(row.get("cash_per_share")),
            exchange_ratio=_num(row.get("exchange_ratio")),
            announce_date=pd.Timestamp(row["announce_date"]),
            expected_close=pd.Timestamp(row["expected_close"]),
            status=str(row.get("status", "pending")).strip().lower(),
            pre_announce_price=_num(row.get("pre_announce_price"), np.nan),
            regulatory_risk=int(_num(row.get("regulatory_risk"), 3)),
            financing_risk=int(_num(row.get("financing_risk"), 3)),
            shareholder_risk=int(_num(row.get("shareholder_risk"), 3)),
            timing_risk=int(_num(row.get("timing_risk"), 3)),
            notes=str(row.get("notes", "")),
        ))
    return deals


def fetch_last_prices(tickers: list[str]) -> dict[str, float]:
    """Last close for each ticker. Missing/delisted names come back as NaN."""
    tickers = sorted({t for t in tickers if t})
    if not tickers:
        return {}
    try:
        import yfinance as yf
        raw = yf.download(tickers, period="10d", auto_adjust=True, progress=False)
        close = raw["Close"]
        if isinstance(close, pd.Series):
            close = close.to_frame(tickers[0])
        return {t: float(close[t].dropna().iloc[-1])
                for t in close.columns if close[t].notna().any()}
    except Exception:
        return {}


def deal_value(deal: Deal, acquirer_price: float | None) -> float | None:
    if deal.structure == "cash":
        return deal.cash_per_share
    if acquirer_price is None or not np.isfinite(acquirer_price):
        return None
    if deal.structure == "stock":
        return deal.exchange_ratio * acquirer_price
    return deal.cash_per_share + deal.exchange_ratio * acquirer_price


def risk_tier(points: int) -> str:
    if points <= 8:
        return "A"
    if points <= 12:
        return "B"
    return "C"


def evaluate(deal: Deal, target_price: float | None,
             acquirer_price: float | None, today: pd.Timestamp | None = None,
             max_position: float = DEFAULT_MAX_POSITION,
             risk_budget: float = DEFAULT_RISK_BUDGET) -> dict:
    today = pd.Timestamp(today or pd.Timestamp.today().normalize())
    value = deal_value(deal, acquirer_price)
    row = {
        "deal_id": deal.deal_id, "target": deal.target,
        "acquirer": deal.acquirer, "structure": deal.structure,
        "status": deal.status, "announce_date": str(deal.announce_date.date()),
        "expected_close": str(deal.expected_close.date()),
        "target_price": None, "acquirer_price": None, "deal_value": None,
        "gross_spread": None, "annualised": None, "days_to_close": None,
        "break_downside": None, "risk_points": None, "risk_tier": None,
        "position_pct": None, "signal": "no data", "reason": "",
    }
    if target_price is not None and np.isfinite(target_price):
        row["target_price"] = round(float(target_price), 4)
    if acquirer_price is not None and np.isfinite(acquirer_price):
        row["acquirer_price"] = round(float(acquirer_price), 4)

    if value is None or target_price is None or not np.isfinite(target_price):
        row["reason"] = "missing target or acquirer price"
        return row
    if target_price <= 0:
        row["reason"] = "bad target price"
        return row

    spread = value / target_price - 1.0
    days = (deal.expected_close - today).days
    row["deal_value"] = round(float(value), 4)
    row["gross_spread"] = round(float(spread), 4)
    row["days_to_close"] = int(days)
    if days > 0:
        row["annualised"] = round(float((1.0 + spread) ** (365.0 / days) - 1.0), 4)
    else:
        row["annualised"] = None

    if deal.pre_announce_price is not None and np.isfinite(deal.pre_announce_price) \
            and deal.pre_announce_price > 0:
        row["break_downside"] = round(float(deal.pre_announce_price / target_price - 1.0), 4)

    points = (deal.regulatory_risk + deal.financing_risk
              + deal.shareholder_risk + deal.timing_risk)
    row["risk_points"] = int(points)
    row["risk_tier"] = risk_tier(points)

    if row["break_downside"] is not None and row["break_downside"] < 0:
        row["position_pct"] = round(float(min(
            max_position, risk_budget / abs(row["break_downside"])
        )), 2)

    reasons = []
    if row["annualised"] is None or row["annualised"] < MIN_ANNUALISED:
        reasons.append("annualised spread below 8%")
    if row["break_downside"] is None:
        reasons.append("missing pre-announcement price")
    elif row["break_downside"] < MAX_BREAK_DOWNSIDE:
        reasons.append("break downside worse than -20%")
    if points > MAX_RISK_POINTS:
        reasons.append("risk score above 12")
    if deal.status != "pending":
        reasons.append(f"status is {deal.status}")
    row["signal"] = "enter" if not reasons else "pass"
    row["reason"] = "; ".join(reasons) if reasons else "meets the entry rule"
    return row


def run(deals_path: str | Path, today: str | None = None) -> dict:
    deals = load_deals(deals_path)
    tickers = []
    for d in deals:
        tickers.append(d.target)
        tickers.append(d.acquirer)
    prices = fetch_last_prices(tickers)
    rows = [evaluate(d, prices.get(d.target), prices.get(d.acquirer), today=today)
            for d in deals]
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "merger_arb.csv", index=False)
    out = {
        "as_of": str(pd.Timestamp(today or pd.Timestamp.today().normalize()).date()),
        "deals": rows,
        "rules": {
            "min_annualised": MIN_ANNUALISED,
            "max_break_downside": MAX_BREAK_DOWNSIDE,
            "max_risk_points": MAX_RISK_POINTS,
            "max_position_pct": DEFAULT_MAX_POSITION,
            "risk_budget_pct": DEFAULT_RISK_BUDGET,
            "max_gross_exposure_pct": MAX_GROSS_EXPOSURE,
        },
        "note": "Live/paper tool. A historical backtest needs delisted target "
                "prices and deal terms; free Yahoo data drops them.",
    }
    (OUT / "merger_arb.json").write_text(json.dumps(out, indent=2))
    return out


def paper_snapshot(deals_path: str | Path, today: str | None = None) -> pd.DataFrame:
    out = run(deals_path, today=today)
    rows = []
    for d in out["deals"]:
        if d["signal"] != "enter":
            continue
        rows.append({
            "date": out["as_of"], "deal_id": d["deal_id"],
            "target": d["target"], "structure": d["structure"],
            "target_price": d["target_price"], "deal_value": d["deal_value"],
            "gross_spread": d["gross_spread"],
            "annualised": d["annualised"],
            "break_downside": d["break_downside"],
            "position_pct": d["position_pct"],
            "risk_tier": d["risk_tier"],
        })
    if not rows:
        return pd.DataFrame(columns=["date", "deal_id"])
    new = pd.DataFrame(rows)
    if LEDGER.exists():
        old = pd.read_csv(LEDGER)
        new = pd.concat([old, new], ignore_index=True)
        new = new.drop_duplicates(["date", "deal_id"], keep="first")
    new.to_csv(LEDGER, index=False)
    return new
