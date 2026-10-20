# Phase 6 — pre-registered core parameter study

*The grid and the split were fixed before the run. This is a retrospective,
pre-registered split, not a blind forward test: the analyst has seen the data.
The discipline is that the 12 variants and the selection rule were fixed before
the holdout table was read.*

## The grid

One factor changes at a time around the published base:

- base: trend lookbacks 1/3/6/12, 10% vol target, 2-month carry lag, monthly,
  use XS, book 74/26;
- vol target: 8%, 12%;
- trend lookbacks: 3/6/12, 1/3/6, 6/12;
- carry lag: 1, 3 months;
- rebalance: quarterly;
- signal: no XS;
- book weights: 80/20, 60/40.

Selection: **2005-01-01 → 2018-12-31**. Holdout: **2019-01-01 → latest**.
Selection rule: highest selection-period Sharpe, then report the holdout without
changing it. DSR: **115 trials** (103 prior + 12 here).

## Results

| Variant | Selection Sharpe | Holdout Sharpe | Full Sharpe | Full MaxDD |
|---|---:|---:|---:|---:|
| **lb_6_12** | **0.947** | **0.330** | **0.693** | −19.6% |
| lb_3_6_12 | 0.881 | 0.222 | 0.613 | −21.1% |
| vol_08 | 0.872 | 0.130 | 0.575 | −21.4% |
| base | 0.871 | 0.146 | 0.581 | −23.9% |
| lag_1 | 0.871 | 0.153 | 0.583 | −24.1% |
| vol_12 | 0.870 | 0.144 | 0.581 | −26.6% |
| book_60_40 | 0.870 | 0.132 | 0.560 | −22.8% |
| lag_3 | 0.865 | 0.144 | 0.576 | −24.1% |
| book_80_20 | 0.860 | 0.149 | 0.581 | −24.4% |
| lb_1_3_6 | 0.838 | 0.072 | 0.622 | −23.3% |
| no_xs | 0.756 | 0.028 | 0.467 | −29.3% |
| quarterly | 0.626 | −0.066 | 0.356 | −34.6% |

The selection winner is **lb_6_12** (trend 6/12 only):

| lb_6_12 | CAGR | Vol | Sharpe | MaxDD |
|---|---:|---:|---:|---:|
| Selection 2005–2018 | 7.93% | 8.44% | 0.947 | −13.8% |
| Holdout 2019+ | 2.37% | 8.06% | **0.330** | −11.1% |
| Full | 5.45% | 8.14% | 0.693 | −19.6% |

It is also the best holdout variant. But the improvement over the base
(holdout 0.146 → 0.330; full 0.581 → 0.693) is not statistically robust after
deflation.

## Deflated Sharpe

| lb_6_12 | DSR (115 trials) | 95% block bootstrap |
|---|---:|---:|
| Full sample | 0.751 | 0.281 – 1.102 |
| **Holdout** | **0.048** | **−0.208 – 0.992** |

The holdout DSR is **0.048**: after accounting for 115 trials, a holdout Sharpe
of 0.33 over ~7.8 years is not distinguishable from the best of many random
trials. The bootstrap lower bound is negative. This is the central result: the
parameter study does **not** produce a robust improvement.

## Cost stress (selection winner)

| Cost | Full Sharpe | Holdout Sharpe |
|---:|---:|---:|
| 5 bps | 0.693 | 0.330 |
| 10 bps | 0.608 | 0.232 |
| 25 bps | 0.351 | −0.061 |

At 25 bps the holdout is negative. The base is cost-sensitive; the selection
winner is not exempt.

## Verdict

- **No parameter change is justified by this study.** The best variant looks
  better in selection and holdout, but its holdout DSR is 0.048; it is a trial,
  not an improvement.
- **The base remains the published choice.** The study does not overturn the
  74/26, 10%-vol, monthly, 1/3/6/12 configuration.
- **The parameter lever is weaker than the sleeve/hedge decisions.** Quarterly
  rebalancing and dropping XS are clearly worse; vol target and book weights are
  flat. Trend lookbacks 6/12 is the only candidate worth a forward test.
- **Do not adopt lb_6_12 after seeing this table.** Pre-register it for a
  forward/paper test if you want to pursue it.

## Caveats

- The split is retrospective; the analyst saw 2019–2026 before the run.
- The DSR uses daily returns and 115 trials; the holdout has ~7.8 years.
- One path, one cost assumption (5 bps base), one universe.
- The selection period includes 2008; the holdout includes 2020 and 2022. They
  are different regimes.
- Parameter studies are not free: every variant is a trial.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_phase6.py
./.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/phase6_metrics.json`, `output/13_phase6.png`.
