# Phase 7 — tail hedges on the Phase 3 overlay

*Can a mechanical tail hedge improve the 60/40 + 30% book? The grid and the
success rule were fixed before the run. Short answer: the investable hedges pass
the letter of the rule only by de-risking, and their own return stream is
significantly negative. Do not adopt them. The one variant that looks good is
not investable.*

## What was tested

Base: 60/40 (SPY/IEF, monthly, net of 5 bps) + 30% equal-weight Phase 3 book
(trend, carry, BAB, gated VRP). Window B starts **2009-11** because VIX3M does.

Four hedges, fixed sizes, no grid and no conditional trigger:

| Variant | Position | Funding |
|---|---|---|
| `short_spy_5` | short 5% SPY notional | collateral earns T-bills |
| `short_spy_10` | short 10% SPY notional | collateral earns T-bills |
| `long_vol_vix_5` | long 5% VIX **spot** | pays T-bills; **no roll, not investable** |
| `short_svxy_5` | short 5% SVXY (long-vol) | pays T-bills + 50 bps/yr borrow; starts 2011-11 |

Selection: **2005-01-01 → 2018-12-31** as pre-registered. The overlay only
starts in 2009-11 (and the SVXY hedge in 2011-11), so the effective selection
windows are shorter; the tables say so. Holdout: **2019-01-01 → 2026-10**.

Success rule, fixed before the run: the hedge must improve **both** holdout
Sharpe and holdout max drawdown, and must not turn negative at 25 bps.

## Full sample (204 months unless noted)

| Portfolio | From | CAGR | Vol | Sharpe | Sortino | MaxDD | Worst month |
|---|---|---:|---:|---:|---:|---:|---:|
| Base overlay | 2009-11 | 8.33% | 7.00% | 1.183 | 1.924 | −14.46% | −5.58% |
| + short SPY 5% | 2009-11 | 7.68% | 6.33% | 1.203 | 1.952 | −13.25% | −5.10% |
| + short SPY 10% | 2009-11 | 7.02% | 5.68% | 1.226 | 1.982 | −12.04% | −4.63% |
| + long VIX spot 5% | 2009-11 | 9.96% | 4.78% | 2.018 | 4.026 | −9.74% | −4.48% |
| + short SVXY 5% | 2011-11 | 6.69% | 5.85% | 1.138 | 1.877 | −13.47% | −5.15% |
| *base, same 2011-11 window* | 2011-11 | 8.15% | 7.08% | 1.146 | 1.827 | −14.46% | −5.58% |

Every hedge lowers volatility. That is not evidence of a hedge; it is evidence
of less exposure.

## Selection and holdout

| Variant | Selection Sharpe | Holdout Sharpe | Holdout MaxDD | Δ holdout Sharpe | Δ holdout MaxDD |
|---|---:|---:|---:|---:|---:|
| Base | 1.341 | 1.079 | −14.46% | — | — |
| short SPY 5% | 1.367 | 1.095 | −13.25% | +0.016 | +1.21 pp |
| short SPY 10% | 1.394 | 1.113 | −12.04% | +0.034 | +2.42 pp |
| long VIX spot 5% | 2.504 | 1.746 | −9.74% | +0.667 | +4.72 pp |
| short SVXY 5% | 1.308* | 1.116 | −13.47% | +0.037 | +0.99 pp |

\* SVXY selection is 2011-11 → 2018-12; the like-for-like base there is 1.296,
so the SVXY hedge adds **+0.012** selection Sharpe, not +0.0x on the longer
window.

By the letter of the pre-registered rule, the two short-SPY hedges pass: both
holdout Sharpe and holdout drawdown improve. The gains are tiny (1.6–3.4 bps of
Sharpe, 1.2–2.4 points of drawdown) and the rule, as written, cannot tell
de-risking apart from hedging. The next section is why that distinction matters.

## The honest test: the hedge's own return stream

The hedged portfolio's Sharpe is mostly the base's Sharpe. The relevant object
is the difference `hedged − base`: what the hedge adds and what it costs.

| Hedge | Mean/month | Vol/month | Sharpe (ann.) | t-stat | Hit rate | DSR (119 trials) | 95% block bootstrap |
|---|---:|---:|---:|---:|---:|---:|---:|
| short SPY 5% | −0.054% | 0.206% | **−0.915** | **−3.77** | 33.8% | 0.000 | −1.37 … −0.49 |
| short SPY 10% | −0.109% | 0.412% | **−0.915** | **−3.77** | 33.8% | 0.000 | −1.37 … −0.49 |
| long VIX spot 5% | +0.115% | 1.256% | +0.316 | +1.30 | 47.1% | 0.114 | +0.01 … +0.61 |
| short SVXY 5% | −0.121% | 0.730% | **−0.571** | **−2.21** | 36.7% | 0.000 | −1.14 … −0.08 |

The short-SPY hedge is a negative-carry insurance policy: it loses in 66% of
months, and the losses are statistically large (t = −3.8). The bootstrap
interval for its Sharpe is entirely below zero. Scaling the size from 5% to 10%
scales the same stream; it does not change its Sharpe.

The short-SVXY hedge is also negative (t = −2.2) and adds path dependence: SVXY
is a daily-reset ETF, so a short position is not a clean long-vol exposure.

The hedged *portfolio* DSR is not evidence for the hedge. It is 0.956–0.959 at
119 trials for the short-SPY variants, but that is the base portfolio's alpha
surviving deflation, not the hedge's contribution. The marginal DSR is 0.000.

## Vol-matched drawdown: de-risking, not convexity

If a hedge only removes exposure, its max drawdown should fall roughly in
proportion to its volatility. Compare the actual drawdown with `base MaxDD ×
(hedged vol / base vol)`:

| Hedge | Vol ratio | Proportional MaxDD | Actual MaxDD | Convexity |
|---|---:|---:|---:|---:|
| short SPY 5% | 0.904 | −13.08% | −13.25% | **−0.17 pp** |
| short SPY 10% | 0.811 | −11.73% | −12.04% | **−0.31 pp** |
| long VIX spot 5% | 0.683 | −9.87% | −9.74% | +0.13 pp |
| short SVXY 5% | 0.836 | −12.08% | −13.47% | **−1.39 pp** |

Every investable hedge is **worse** than proportional: it removes volatility but
buys no convexity. The only positive convexity is the non-investable VIX spot
series, and it is 0.13 pp — not a business case.

## Crisis windows (cumulative return)

| Window | Base | short SPY 5% | short SPY 10% | VIX spot 5% | short SVXY 5% |
|---|---:|---:|---:|---:|---:|
| 2018 Q4 | −6.71% | −6.00% | −5.30% | −1.76% | −5.21% |
| COVID 2020 (Feb–Apr) | −3.24% | −2.78% | −2.33% | **+2.40%** | −0.66% |
| 2022 | −11.29% | −10.33% | −9.37% | −7.92% | −11.08% |
| 2023 rebound | +13.01% | +11.99% | +10.98% | +10.72% | +9.99% |

The hedges do what hedges do in the bad months, and they pay for it in the good
ones. The COVID improvement from short SPY is 0.5–0.9 points — on a 5–10%
notional, that is the arithmetic, not a discovery.

## Cost stress

Holdout Sharpe at 5 / 10 / 25 bps (the whole path is rebuilt at each level):

| Variant | 5 bps | 10 bps | 25 bps |
|---|---:|---:|---:|
| Base | 1.079 | 1.065 | 1.023 |
| short SPY 5% | 1.095 | 1.079 | 1.032 |
| short SPY 10% | 1.113 | 1.096 | 1.043 |
| long VIX spot 5% | 1.746 | 1.726 | 1.664 |
| short SVXY 5% | 1.116 | 1.100 | 1.051 |

The hedge's own turnover is small; cost is not the reason to reject it. The
reason is the negative expected return of the hedge stream.

## The VIX artifact

The 5% long-VIX-spot variant is the best-looking line in the tables and it is a
trap. Spot VIX is not an asset and has no roll. The variant earns the
**arithmetic mean of monthly percentage changes**, which is positive (about
+2.3%/month) even though the VIX level is roughly flat over the sample: a
mean-reverting level produces large percentage gains from low levels and smaller
percentage losses from high levels. A 5% allocation to that series therefore
earns about +0.115%/month without any risk premium. A real long-vol position
(VIX futures, VXX) pays the roll, which is usually negative in contango, and
would not compound this way.

The variant is useful as a diagnostic: it says the *timing* of vol spikes is
real, and the overlay does have crisis beta. It is not an implementable
strategy, and it should not be counted as one.

## Verdict

- **Do not add a short-SPY overlay.** It passes the pre-registered rule on a
  technicality (holdout Sharpe +0.016/+0.034, MaxDD +1.2/+2.4 pp) but its own
  return stream has a Sharpe of **−0.92** (t = −3.8), a 34% hit rate and a
  bootstrap interval entirely below zero. It is de-risking with a fee, and its
  drawdown is worse than proportional to the volatility it removes.
- **Do not add the short-SVXY hedge.** Marginal Sharpe −0.57 (t = −2.2), worse
  than proportional drawdown (−1.39 pp), plus daily-reset path dependence and
  borrow.
- **Do not treat the VIX-spot result as evidence.** It is arithmetic on a
  mean-reverting, non-investable series. It shows the exposure is there; it does
  not show a product that captures it.
- **The base stays.** Phase 7 does not change the Phase 3 book. If the goal is a
  smaller drawdown, hold less of the book; that is cheaper and more honest than
  a constant short overlay.
- **The pre-registered rule was too weak.** It scored the hedged portfolio, not
  the hedge. Every future phase should pre-register a marginal test (difference
  series, t-stat, DSR) as well as the portfolio test.

## Caveats

- Monthly frequency only. A daily or intra-month hedge (and a real option
  strike) is a different question, and a more expensive one.
- One path, one base book. The overlay is the published Window B claim; Window
  A (legacy SVXY) is not re-tested here.
- The SVXY series starts 2011-11; its selection window is 86 months, not 158.
- Spot VIX ignores futures roll and the term premium; the diagnostic is an upper
  bound on the timing signal, not a tradable return.
- No options, no VIX futures, no borrow spikes, no margin calls. A real short
  overlay would face all four.
- Four new trials; DSR at 119. The marginal series is short (180–204 months), so
  even a correct hedge would be hard to distinguish from noise in one sample.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_phase7.py
./.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/phase7_metrics.json`, `output/14_phase7.png`.
