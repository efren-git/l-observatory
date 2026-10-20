# Phase 3 — the combined book

*The cross-project book pre-specified in `PLAN.md` on 2026-10-19. This is the
honest result after the 2026-10-20 corrections.*

## The question

Can one book combine the surviving sleeves from `inercia` and `cartograf`
without double-counting, and does it improve a 60/40 after costs?

The pre-specified answer was: use one trend, one carry, BAB and the gated VRP;
monthly frequency; equal-weight and inverse-vol; 20%/30% overlays; report both
the legacy-SVXY window and the gated-VRP window.

## Overlap audit

| Sleeve | Source | Used? |
|---|---|---|
| trend | inercia (longer history, one implementation) | yes |
| carry | inercia (one implementation) | yes |
| BAB | cartograf | yes, pre-specified; it is a drag after the 2026-10-20 fix |
| gated VRP | cartograf | yes |
| cartograf trend | cartograf | no — duplicate |
| cartograf carry | cartograf | no — duplicate |

No sleeve is counted twice. The stock cross-section is excluded (survivorship).

## Windows and rules

- **Window A:** 2008-01 → 2026-10, legacy SVXY proxy. Labelled; no proper VRP.
- **Window B:** 2009-11 → 2026-10, gated VRP (VIX3M starts 2009-09).
- Monthly returns. The proper VRP is monthly; daily smoothing would create
  artificial autocorrelation.
- 5 bps per unit of combined-book turnover; drift and rebalancing costs are
  charged in the weights. The sleeve returns are already net of their own costs.
- A sleeve that is not live is cash, not backfilled. The live mask is lagged one
  month, so a price at month-end t is not used to earn month t's return.
- The combined book is equal-weight or inverse-vol (12-month vol, shifted one
  month); 20%/30% overlays are fixed, not searched.
- Every variant is a trial. The DSR uses **61 trials** (26 inercia + 23
  cartograf + 12 Phase 3); the final-variant count is 2.

## Window B (the gated-VRP claim)

| Portfolio | CAGR | Vol | Sharpe | MaxDD |
|---|---:|---:|---:|---:|
| SPY | 14.5% | 14.3% | 1.03 | −23.9% |
| 60/40 monthly | 9.8% | 8.9% | 1.10 | −20.5% |
| equal 4 (trend+carry+BAB+VRP) | 4.8% | 5.5% | 0.88 | −11.4% |
| inverse-vol 4 | 6.3% | 5.8% | 1.09 | −14.6% |
| **60/40 + 30% equal** | **8.3%** | **7.0%** | **1.18** | **−14.5%** |
| **60/40 + 30% inverse-vol** | **8.8%** | **7.1%** | **1.23** | **−15.1%** |
| 60/40 + 30% inverse-vol, no BAB | 9.2% | 7.2% | 1.27 | −14.8% |

The pre-specified 30% equal overlay improves the 60/40's Sharpe from **1.10 to
1.18** and cuts the drawdown from **−20.5% to −14.5%**. The inverse-vol overlay
does a little better (1.23 / −15.1%). The no-BAB variant is better still
(1.27 / −14.8%), but it is a post-audit sensitivity, not the pre-specified book.

The standalone 4-sleeve book does **not** beat the 60/40: equal 0.88, inverse-vol
1.09. The product is the overlay, not the standalone book.

## Window A (legacy SVXY, no proper VRP)

| Portfolio | CAGR | Vol | Sharpe | MaxDD |
|---|---:|---:|---:|---:|
| SPY | 11.2% | 15.6% | 0.76 | −46.3% |
| 60/40 monthly | 8.1% | 9.6% | 0.86 | −27.6% |
| equal 4 | 1.7% | 5.0% | 0.37 | −13.4% |
| inverse-vol 4 | 2.1% | 5.5% | 0.40 | −15.0% |
| 60/40 + 30% equal | 6.3% | 7.4% | 0.86 | −19.7% |
| 60/40 + 30% inverse-vol | 6.3% | 7.5% | 0.86 | −19.8% |

Window A **does not improve Sharpe**; it only cuts the drawdown (−19.7% vs
−27.6%). The legacy SVXY proxy is not a good enough VRP to carry the overlay.
This is the honest negative: without the proper gated VRP, the combined book is
insurance, not a Sharpe improvement.

## BAB is a drag

After the 2026-10-20 fix, BAB is negative standalone. In Window B, dropping it
lifts the inverse-vol book from 1.09 to 1.17, and the 30% overlay from 1.23 to
1.27. The pre-specified four-sleeve book is still reported, but the result is
clear: the core should be trend + carry + gated VRP. That is a **new trial**,
not the pre-specified claim; count it.

## Multiple testing and uncertainty

| Claim | Sharpe | DSR (61 trials) | 95% bootstrap |
|---|---:|---:|---:|
| 60/40 + 30% equal | 1.18 | 0.972 | 0.716 – 1.704 |
| 60/40 + 30% inverse-vol | 1.23 | 0.979 | 0.735 – 1.776 |
| 60/40 + 30% inverse-vol, no BAB | 1.27 | 0.984 | 0.759 – 1.825 |

The DSR is high because the overlay's monthly Sharpe is high and the sample is
143–203 months. The bootstrap is the honest width: a lower bound around 0.7 is
still positive, but the interval is wide. One path is not proof.

## Caveats

- The gated VRP has no 2008 observation; Window B starts 2009-11. It is one
  regime.
- 5 bps/month is optimistic for a variance position; stress it.
- The ETF universe is today's list; the cross-sections are upward-biased.
- The 30% fraction and the equal/inverse-vol variants are pre-specified but
  in-sample choices; a locked holdout or CPCV is still missing.
- The no-BAB variant is a post-audit sensitivity; do not present it as the
  original claim.
- Monthly frequency avoids the daily-smoothing autocorrelation, but it also
  gives few observations.

## Verdict

On Window B, the combined book **does what the plan asked**: a 30% allocation
lifts the 60/40's Sharpe from 1.10 to 1.18–1.23 and cuts the drawdown by about a
third. On Window A, it only cuts the drawdown. It does **not** beat SPY
standalone. The honest product is a risk-reducing overlay on a normal portfolio,
not alpha.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_phase3.py
./.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/phase3_metrics.json`, `output/10_phase3.png`.
