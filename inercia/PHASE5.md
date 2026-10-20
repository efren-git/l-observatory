# Phase 5 — pairs, hedging and paper trading

*The user's question: can a pairs trade — for example short KO against PEP — improve
or hedge the Phase 3 book? This phase tests that hypothesis, a fixed industry
screen, a small parameter grid, and starts a paper-trading ledger. No live orders.*

## KO/PEP: the example fails

KO/PEP is a sensible hypothesis: two consumer-staples compounders with a long
common history. On this data it is not a valid mean-reverting pair.

| Metric | KO/PEP |
|---|---:|
| Default Sharpe (entry 2.0, z 60, exit 0.5) | **−0.095** |
| CAGR / Vol / MaxDD | −0.8% / 6.2% / −33.7% |
| Full-sample ADF t-stat | **−0.773** (5% approx −2.86) |
| Half-life of the spread | **1,029 days** (~4.1 years) |
| Correlation to SPY | −0.06 |
| Annual turnover | 10.2× |

The residual is not stationary; the half-life is longer than most holding
periods. A negative rolling beta appears in the recent window, which is another
sign of structural divergence rather than a stable hedge ratio. **Do not trade
KO/PEP on this evidence.**

## Fixed industry screen

Eight pre-specified same-industry pairs, same default parameters:

| Pair | Sharpe | CAGR | MaxDD | ADF t | Half-life (d) | Corr SPY |
|---|---:|---:|---:|---:|---:|---:|
| KO/PEP | −0.095 | −0.8% | −33.7% | −0.77 | 1,029 | −0.06 |
| XOM/CVX | 0.106 | 0.5% | −23.6% | −1.41 | 685 | −0.02 |
| **V/MA** | **0.073** | **0.2%** | **−18.8%** | **−5.25** | **63** | **0.01** |
| GS/MS | −0.033 | −0.6% | −28.4% | −3.29 | 245 | 0.11 |
| UPS/FDX | −0.029 | −0.8% | −46.1% | −1.57 | 540 | 0.16 |
| HD/LOW | −0.011 | −0.2% | −23.1% | −2.69 | 262 | −0.01 |
| PG/CL | −0.608 | −3.9% | −62.5% | −2.00 | 538 | 0.13 |
| JNJ/PFE | −0.083 | −1.3% | −36.5% | −1.64 | 501 | 0.28 |

Only **V/MA** passes the full-sample cointegration screen (ADF −5.25, half-life
63 days), and its default strategy is weak: Sharpe 0.073, CAGR 0.2%. This is a
screen, not a portfolio; 8 pairs were tested, so the best of them is subject to
selection bias.

## Parameter sensitivity

12 variants per pair (entry 1.5/2/2.5, z window 60/120, exit 0.5/1.0):

| Pair | Best Sharpe | Best parameters | Worst Sharpe |
|---|---:|---|---:|
| V/MA | 0.19 | entry 1.5, z 120, exit 1.0 | −0.244 |
| KO/PEP | 0.212 | entry 2.5, z 60, exit 1.0 | −0.213 |

The best variants are in-sample and the range includes negative Sharpes. With
**103 trials** across this phase, a best Sharpe of 0.19–0.21 is not evidence. Do
not adopt the best grid after seeing it.

## Hedging the Phase 3 book

Monthly blend of the Phase 3 30% overlay with the default V/MA or KO/PEP pair
(rebalanced monthly, 5 bps):

| Portfolio | CAGR | Vol | Sharpe | MaxDD |
|---|---:|---:|---:|---:|
| Phase 3 overlay | 8.33% | 7.00% | **1.183** | −14.46% |
| + 10% V/MA | 7.50% | 6.24% | **1.192** | −12.81% |
| + 20% V/MA | 6.66% | 5.52% | **1.199** | **−11.14%** |
| + 10% KO/PEP | 7.36% | 6.31% | 1.159 | −13.44% |
| + 20% KO/PEP | 6.38% | 5.69% | 1.120 | −12.42% |

V/MA has correlation **−0.17** to the overlay. A 20% allocation cuts the
drawdown from −14.5% to −11.1% and adds ~0.02 Sharpe, but gives up 1.7 points of
CAGR. That is a **preference trade**, not alpha. KO/PEP lowers Sharpe; it is not
a hedge.

## Paper trading

The first snapshot is in `output/paper_trade.json`; the append-only log is
`output/paper_trade_log.csv`.

- **As of 2026-10-14** (latest cached data).
- Phase 3 allocation: 70% 60/40 + 30% book; book equal-weight trend / carry /
  BAB / gated VRP. Sleeve-level target, rebalanced monthly.
- V/MA: long spread, beta 0.928, z −0.80.
- KO/PEP: long spread, beta −0.436, z −1.43 — recorded for research, **not
  recommended**.
- Mode: paper only; no order router, no broker, no live trading.

Run `src/paper_trade.py` after each month-end to append the latest snapshot.
The point is to compare forward performance with the backtest, not to trade.

## Verdict

- **KO/PEP is not a valid pairs strategy on this data.** The user's example is a
  good hypothesis, but the residual is not stationary and the strategy loses
  money after costs.
- **V/MA is the only cointegrated pair in the fixed screen**, but it is a weak
  return engine. It is a modest, negatively correlated hedge: 20% improves the
  drawdown and slightly improves Sharpe, at the cost of CAGR.
- **The core algorithm does not change.** Trend + carry + gated VRP remains the
  book; pairs are an optional satellite, not a replacement.
- **Paper trading starts now.** A month or a year of forward data is worth more
  than another in-sample optimisation.

## Caveats

- The ADF test is full-sample and approximate (no statsmodels); the trading beta
  is rolling.
- 5 bps per leg and 50 bps/year borrow are assumptions; short borrow and hard-to-
  borrow costs can be higher.
- The pair screen and grid are multiple testing; 103 trials are counted.
- KO/PEP and V/MA can have structural breaks (management, index changes,
  valuation regimes) that a rolling beta reacts to slowly.
- The paper snapshot is a ledger, not an execution system.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_phase5.py
./.venv/bin/python3 src/paper_trade.py
./.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/phase5_metrics.json`, `output/12_phase5.png`,
`output/paper_trade.json`, `output/paper_trade_log.csv`.
