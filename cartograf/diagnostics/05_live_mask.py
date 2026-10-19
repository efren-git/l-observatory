"""Diagnostic: per-month live-name masking.

A zero-filled return panel makes a fund that has not listed look like a
riskless asset: beta=0, vol=0. The BAB score then ranks phantom names ahead of
live ones and normalises live weights against them. This script reports the
pre-inception share of the BAB score and the sleeve before/after the mask.

Run after: ./.venv/bin/python3 src/run.py
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cartograf.backtest import scale_weights_to_target, turnover_annual, weights_to_returns
from cartograf.config import COST
from cartograf.sleeves import bab, live_mask, universe_setup
from cartograf.stats import perf

try:
    from fetch_data import UNIVERSE
except Exception:
    UNIVERSE = {}


def bab_unmasked(px, R, tradable, me):
    eq = [t for t in tradable if UNIVERSE.get(t, "").startswith("equity")]
    spy = R["SPY"]
    beta = pd.DataFrame({t: R[t].rolling(252).cov(spy) / spy.rolling(252).var()
                         for t in eq})
    score = -(beta.sub(1.0))
    score = score.div((R[eq].rolling(63).std() * np.sqrt(252)).clip(lower=0.05))
    rows = score.div(score.abs().sum(axis=1).replace(0, np.nan), axis=0)
    w = rows.reindex(me).reindex(columns=tradable).fillna(0.0)
    w = scale_weights_to_target(w, R)
    net, to, _ = weights_to_returns(R, w, COST)
    return net, turnover_annual(to, len(R)), score


def main():
    px, R, tradable, me, groups = universe_setup()
    live = live_mask(px, me, tradable)
    eq = [t for t in tradable if UNIVERSE.get(t, "").startswith("equity")]

    net_old, to_old, score = bab_unmasked(px, R, tradable, me)
    old_share = {}
    for d in me:
        s = score.loc[d].dropna()
        if s.empty or float(s.abs().sum()) == 0:
            continue
        not_live = [c for c in s.index if not bool(live.loc[d, c])]
        old_share[d] = float(s[not_live].abs().sum() / s.abs().sum())

    net_new, to_new = bab(R, tradable, me, groups)

    out = {
        "window": [str(me[0].date()), str(me[-1].date())],
        "live_names_by_year": {
            int(y): int(live.loc[g.index].sum(axis=1).max())
            for y, g in live.groupby(live.index.year)
        },
        "bab_pre_inception_score_share_by_year": {
            int(y): round(float(v), 4)
            for y, v in pd.Series(old_share).groupby(lambda d: d.year).mean().items()
        },
        "bab_unmasked": {**perf(net_old.loc[me[0]:]), "turnover": to_old},
        "bab_masked": {**perf(net_new.loc[me[0]:]), "turnover": to_new},
        "note": "mask uses the first valid price as the listing date; signal "
                "lookbacks still require their own history",
    }
    (ROOT / "diagnostics" / "live_mask_diagnostic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
