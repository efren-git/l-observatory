# Phase 4 — robustness and out-of-sample checks

*Phase 3 fixed the book. Phase 4 asks whether it survives contact with
subperiods, costs, a post-hoc holdout and a block sample-split. It does not
change the algorithm.*

## What is fixed

The Phase 3 parameters are unchanged: monthly frequency; Window B (2009-11+,
gated VRP); inercia trend + carry once; cartograf BAB + gated VRP; equal or
inverse-vol; 20/30/40% overlays; 5 bps combined-book turnover. Nothing in Phase
4 is tuned.

## Subperiod stability

Contiguous, pre-specified folds; the overlay is the 30% allocation.

| Fold | Equal 30 Sharpe | Inverse-vol 30 Sharpe | Worst MaxDD |
|---|---:|---:|---:|
| 2009-11 → 2013-12 | 1.88 | 2.07 | −4.6% |
| 2014-01 → 2018-12 | 0.93 | 0.95 | −7.5% |
| 2019-01 → 2023-12 | 0.86 | 0.89 | −15.1% |
| 2024-01 → 2026-10 | 1.65 | 1.71 | −3.7% |

The weakest fold is 2019–2023 at ~0.86–0.89; the strongest is the first and the
most recent. The strategy is not uniformly strong, but it is positive in every
fold.

## Post-hoc holdout

Last 24 months (2024-11 → 2026-10) of the pre-specified 30% overlays:

| Claim | Sharpe | CAGR | Vol | MaxDD |
|---|---:|---:|---:|---:|
| 60/40 + 30% equal | 1.46 | 9.4% | 6.5% | −3.7% |
| 60/40 + 30% inverse-vol | 1.51 | 9.9% | 6.5% | −3.5% |

**This is not a blind holdout.** The data were already in the sample used to
choose the structure. It is a subperiod check, and it should be read as such.

## Cost stress

### VRP leg

The gated VRP sleeve is ~25% of the book; the overlay allocates 30% to the book.

| VRP cost / month | VRP sleeve Sharpe | Equal 30 Sharpe | Inverse-vol 30 Sharpe |
|---:|---:|---:|---:|
| 5 bps | 1.181 | 1.183 | 1.232 |
| 10 bps | 1.135 | 1.177 | 1.225 |
| 25 bps | 0.998 | 1.159 | 1.203 |

The sleeve loses ~0.18 Sharpe at 25 bps/month, but the overlay loses only ~0.02
because the sleeve is a minority of the book. The product is diversified against
this cost; the sleeve is not.

### Combined-book turnover

| Cost | Equal 30 Sharpe | Inverse-vol 30 Sharpe |
|---:|---:|---:|
| 5 bps | 1.183 | 1.232 |
| 10 bps | 1.181 | 1.229 |
| 25 bps | 1.177 | 1.221 |

Monthly rebalancing is cheap here; this is not the fragile part of the design.

## Overlay-size sensitivity

| Fraction | Equal 30 | Inverse-vol 30 | Equal no-BAB | Inverse-vol no-BAB |
|---:|---:|---:|---:|---:|
| 20% | 1.158 | 1.189 | 1.192 | 1.213 |
| 30% | 1.183 | 1.232 | 1.233 | 1.266 |
| 40% | 1.201 | 1.270 | 1.267 | 1.313 |

The result is monotone over 20–40%: a larger allocation would have looked better
in this sample. That is a warning, not a recommendation. The 30% choice is
pre-specified and is not special; do not chase 40% after seeing this table.

## Block sample-split and rolling Sharpe

Combinatorial block sample-split: 6 contiguous blocks, hold out 2 at a time,
purge one month at each boundary, 15 splits.

| Claim | Mean | Median | Min | Max | % positive |
|---|---:|---:|---:|---:|---:|
| Equal 30 | 1.18 | 1.24 | 0.49 | 1.91 | 100% |
| Inverse-vol 30 | 1.24 | 1.30 | 0.53 | 2.04 | 100% |
| Inverse-vol no-BAB 30 | 1.26 | 1.26 | 0.54 | 2.05 | 100% |

Rolling 36-month Sharpe of the two pre-specified overlays: min **0.32–0.33**,
median **1.21–1.27**, max **2.63–2.86**, latest **1.87–1.93**, and **0% of
windows negative**. This is a path-stability check, not a blind OOS test.

## Verdict

- The Phase 3 edge survives the pre-specified folds, the cost stresses and the
  block sample-split.
- The weakest period is 2019–2023 (~0.86–0.89); the recent period is strong, but
  it is the post-hoc holdout.
- The VRP sleeve is cost-sensitive at 25 bps/month; the overlay is not, because
  the sleeve is a minority of the book.
- The 30% choice is not special: 40% looks better in-sample. Do not re-optimise
  it after seeing this.
- **This is still not a blind out-of-sample test.** A true holdout needs data
  that were never used to choose the structure; the honest next step is a
  pre-registered forward test, not another backtest.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_phase4.py
./.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/phase4_metrics.json`, `output/11_phase4.png`.
