"""Append-only forward ledger for the Phase 3 overlay.

This is a paper track record, not an order router. Each run recomputes the
published overlay's monthly return series from the current price cache and
appends months that are not already in the log. Existing rows are never
rewritten: the log is evidence, and evidence that can be edited after the fact
is not evidence.

Inception is the first month-end after the ledger was created. The first
eligible return is the first *full* month after inception; a partial month is
not a forward observation.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date

import pandas as pd

from .config import OUT
from .phase3 import load_sleeves
from .phase7 import build_overlay

LEDGER = OUT / "forward_ledger.csv"
META = OUT / "forward_ledger.json"


def _load_meta() -> dict:
    if META.exists():
        return json.loads(META.read_text())
    today = pd.Timestamp(date.today())
    inception = (today + pd.offsets.MonthEnd(0)).normalize()
    meta = {
        "inception": inception.strftime("%Y-%m-%d"),
        "created": today.strftime("%Y-%m-%d"),
        "rule": "first full month after inception; rows are append-only",
        "base": "60/40 + 30% Phase 3 equal-weight overlay, monthly, 5 bps",
        "note": "paper only; no orders. Returns are model returns, not fills.",
    }
    META.write_text(json.dumps(meta, indent=2))
    return meta


def _summary(led: pd.DataFrame) -> dict:
    if led.empty:
        return {"months": 0}
    r = led["overlay"].astype(float)
    nav = (1 + r).cumprod()
    dd = nav / nav.cummax() - 1
    months = len(r)
    out = {
        "months": int(months),
        "nav": round(float(nav.iloc[-1]), 4),
        "total_return": round(float(nav.iloc[-1] - 1), 4),
        "cagr": round(float(nav.iloc[-1] ** (12.0 / months) - 1), 4),
        "vol": round(float(r.std() * (12 ** 0.5)), 4),
        "sharpe": round(float(r.mean() / r.std() * (12 ** 0.5)), 3)
        if r.std() > 0 else None,
        "maxdd": round(float(dd.min()), 4),
        "worst_month": round(float(r.min()), 4),
        "best_month": round(float(r.max()), 4),
        "annualised_from_months": int(months),
        "bench_nav": round(float((1 + led["bench"].astype(float)).cumprod().iloc[-1]), 4),
        "spy_nav": round(float((1 + led["spy"].astype(float)).cumprod().iloc[-1]), 4),
    }
    if months < 24:
        out["warning"] = "fewer than 24 months: CAGR/Sharpe are annualised from a short sample"
    return out


def update_ledger() -> dict:
    meta = _load_meta()
    inception = pd.Period(pd.Timestamp(meta["inception"]), "M")

    overlay, spy, rf, bench = build_overlay(5.0)
    df, live, _ = load_sleeves("B")

    # First full month strictly after inception.
    months = [p for p in overlay.index if p > inception]
    new = pd.DataFrame({
        "month": [str(p) for p in months],
        "overlay": [float(overlay.loc[p]) for p in months],
        "bench": [float(bench.loc[p]) for p in months],
        "spy": [float(spy.loc[p]) for p in months],
        "trend": [float(df.loc[p, "trend"]) for p in months],
        "carry": [float(df.loc[p, "carry"]) for p in months],
        "bab": [float(df.loc[p, "bab"]) for p in months],
        "vrp": [float(df.loc[p, "vrp"]) for p in months],
    })

    if LEDGER.exists():
        old = pd.read_csv(LEDGER)
        old["month"] = old["month"].astype(str)
    else:
        old = pd.DataFrame(columns=new.columns)

    if not old.empty:
        # Never revise an existing month. Keep the first observation.
        new = new[~new["month"].isin(set(old["month"]))]
    led = pd.concat([old, new], ignore_index=True).sort_values("month")
    if not led.empty:
        led["nav"] = (1 + led["overlay"].astype(float)).cumprod().round(6)
    led.to_csv(LEDGER, index=False)

    summary = {
        "inception": meta["inception"],
        "last_month": led["month"].iloc[-1] if len(led) else None,
        "summary": _summary(led) if len(led) else {"months": 0},
        "appended_this_run": len(new),
        "rows": int(len(led)),
        "sha256": hashlib.sha256(LEDGER.read_bytes()).hexdigest() if LEDGER.exists() else None,
        "updated": str(pd.Timestamp.now().date()),
    }
    META.write_text(json.dumps({**meta, **summary}, indent=2))
    return summary
