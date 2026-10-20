# Forward test — one year of paper, then a small live book

*The backtests cannot validate the strategy any further. A forward record can
validate the **implementation**, and over a long enough horizon it can weaken or
confirm the return claim. One year is enough for the first job and almost
useless for the second. This note pre-registers what the year is for.*

## What a year can and cannot prove

For a true annualised Sharpe `SR`, the standard error of a `T`-year estimate is
approximately

```
SE(SR_hat) ≈ sqrt((1 + SR² / 2) / T)
```

At SR = 1.0 that is **1.22** after one year, **0.71** after three, **0.55** after
five. A one-year 95% interval for a Sharpe of 1 is roughly `[-1.4, +3.4]`. It
cannot tell a good strategy from a mediocre one. Anyone who claims a one-year
track record proves alpha is selling something.

What a year *can* prove:

1. the data pipeline runs on schedule and does not silently break;
2. the month-end signal produces the weights the backtest says it should;
3. the orders can be placed at a realistic size, with realistic spreads and
   borrow;
4. the realised cost per unit of turnover is close to the 5 bps assumption;
5. the paper NAV tracks the model NAV, so there is no hidden look-ahead or
   accounting bug;
6. the drawdown is survivable *behaviourally* — the owner does not turn it off
   in the worst month.

Those are the failure modes that kill real books. The Sharpe question needs
years, not months.

## Three stages

### Stage 0 — paper ledger (now)

`src/forward_ledger.py` appends the model's monthly return to
`output/forward_ledger.csv`. Inception is the first month-end after the ledger
was created (**2026-10-31**); the first eligible observation is the first full
month after it. Rows are append-only: a month, once written, is never revised.

`src/paper_trade.py` records the current target (70% 60/40 + 30% book, plus the
V/MA and KO/PEP pair signals) in `output/paper_trade.json` and
`output/paper_trade_log.csv`. This is a target snapshot, not a fill.

Run monthly, after the month-end close:

```bash
./.venv/bin/python3 src/forward_ledger.py
./.venv/bin/python3 src/paper_trade.py
```

### Stage 1 — shadow execution (months 1–3)

Keep the paper ledger, but also write down the orders you *would* have placed:
instrument, side, quantity, limit price, quote at the decision time. At the next
month-end, compare the hypothetical fill with the model price. The output is a
slippage distribution and a list of instruments that are hard to short or too
illiquid at the intended size. No capital at risk.

Gate to Stage 2: three clean months, no missed rebalance, realised slippage
within 2× the 5 bps assumption, and a reconciled NAV.

### Stage 2 — small live capital (months 4–12)

Size it so that a −20% drawdown is annoying, not damaging: an amount the owner
is willing to lose entirely. Unlevered. Monthly rebalance, same signal, same
instruments. Record every fill and every fee in a separate ledger; do not edit
the model.

Practical constraints:

- the book is long/short multi-asset. A retail account needs margin and short
  borrow; not every ETF is shortable at a reasonable fee. Stage 1 should find
  this out before money is involved;
- the 60/40 sleeve is easy (SPY/IEF); the trend/carry sleeve is the hard part;
- the gated VRP sleeve is a volatility-selling exposure. If it cannot be
  implemented with the intended instrument, leave it in cash rather than
  substitute a different product silently;
- taxes, financing and borrow are not in the backtest. Add them to the live
  ledger, not to the model.

## Pre-registered evaluation

Record these every month, before looking at the P&L:

| Dimension | Metric | Pass condition (12 months) |
|---|---|---|
| Process | rebalances executed / scheduled | 12 / 12 |
| Process | weight deviation per sleeve | < 1% of NAV |
| Data | as-of date vs month-end | ≤ 1 trading day |
| Cost | realised bps per unit turnover | ≤ 10 bps |
| Tracking | paper return − model return | within ±2× model monthly vol |
| Risk | live max drawdown | ≤ 1.5× backtest max drawdown |
| Behaviour | strategy still running at month 12 | yes |

Do **not** add a Sharpe target for year one. The interval is too wide to be a
test; a Sharpe target would be a coin flip dressed as discipline.

At 36 months, compare the realised Sharpe with the backtest's block-bootstrap
interval. If it sits inside, the backtest is not contradicted. If it sits below
the lower bound for two consecutive years, the edge has probably decayed.

## Kill criteria (operational, not performance)

Stop and investigate if any of these happens:

- two consecutive missed or late rebalances;
- a data gap longer than five trading days, or a silent universe change;
- weight deviation above 2% of NAV for two months;
- unexplained live-vs-model NAV drift above 1% in a month;
- a drawdown above 1.5× the backtest max (≈ −22% for the overlay);
- three consecutive months with tracking error above 3× the model's monthly
  volatility.

Do not stop because of one bad month. The backtest already contains bad months;
that is what the drawdown column is for.

## What would count as success

At 12 months: **the process survived contact with reality** — every rebalance
done, costs near the assumption, NAV reconciled, drawdown inside the envelope.
That is a successful year even if the return is flat.

At 36 months: the realised Sharpe is inside the backtest's bootstrap interval
and the drawdown is not worse than the model's. That is the first point at which
the forward record says something about the edge.

## Data hygiene

- The monthly job refreshes prices before appending. Adjusted historical prices
  can be revised by the vendor; the ledger keeps the first observation for every
  month and never rewrites it. New months use the new vintage. This is a
  feature: it preserves the forward record.
- The VRP sleeve needs the CBOE VIX term structure; the job refreshes it from
  the free CBOE files. If the download fails, the ledger should skip the month
  rather than invent a sleeve return.
- No paid data, no broker keys in the repository. The live stage uses the
  broker's own statements as the primary record.

## Current status

- Ledger created **2026-10-20**, inception **2026-10-31**, zero observations.
- First scheduled run: **2026-11-01 09:00 Europe/Madrid**, for the October
  month-end (initialises the ledger; no return yet).
- First return observation: **2026-12-01**, for November 2026.
- Paper snapshot as of **2026-10-14** (latest cached data): V/MA long spread,
  z = −0.80; KO/PEP long spread, z = −1.43, recorded but not recommended.
