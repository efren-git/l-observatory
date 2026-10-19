# PLAN — l'Observatori hardening (2026-10-19)

_Status: approved by Efren. Phase 1 (inercia refactor) in progress._

## Decisions taken

1. **Excess-return convention.** Subtract the risk-free rate only from net-long
   benchmarks (SPY, 60/40). Self-financing long/short sleeves are reported raw.
   Every affected table shows both raw and excess columns.
2. **Refactor order.** Refactor `inercia` first, then apply the same shared
   conventions to `cartograf`.
3. **Survivorship.** No free point-in-time S&P membership exists. The stock
   sleeve uses an inception-date universe and is labelled **upward-biased**;
   it is excluded from the combined book.
4. **Deflated Sharpe trials.** Report the DSR two ways: every variant in the
   code/JSONs, and only the final published variants.
5. **CI data.** Keep real data out of git. Use small synthetic fixtures for the
   smoke backtest.

## Phase 1 — inercia refactor (this phase)

Goal: one implementation of every shared concept; scripts become thin entry
points; every number in the README is reproducible from one run.

- [x] Create `src/inercia/` package: config, data, stats, signals, backtest,
      engines, pipeline.
- [x] Canonical backtest: monthly rebalance, one-day lag, gross-normalised
      weights, volatility target, explicit turnover and costs.
- [x] Fix the `sleeve.py` turnover bug: `ws = wd.mul(scale, axis=1)` aligned
      the scale Series to ticker columns, produced all-NaN weights, and made
      costs exactly zero. Correct axis is 0.
- [x] Remove full-sample volatility scaling from the book helpers (look-ahead).
- [x] Lag FRED monthly-average policy rates by two months before they are used
      in FX carry (publication-safe; the old code used the current month's
      average from day one).
- [x] Report fixed (in-sample) and expanding walk-forward book weights side by
      side.
- [x] Add a trial registry and Deflated Sharpe Ratio with both trial counts.
- [x] Add `tests/` synthetic smoke test; no real data committed.
- [x] Update `README.md` to the regenerated numbers.

Acceptance: `./.venv/bin/python3 src/run.py` regenerates every chart and JSON
in `output/`; `python -m unittest discover -s tests` passes; the README agrees
with the JSONs.

## Phase 2 — cartograf (next)

Apply the same conventions to the cartograf sleeves and books:

- shared excess-return handling (net-long vs self-financing);
- inception-date ETF universe; stock sleeve labelled and excluded;
- fix the FX-carry double count (FX ETF total return plus explicit rate
  differential);
- trial registry and DSR for the core book and overlay parameters;
- synthetic smoke test.

## Phase 3 — combined book

Only after Phases 1–2: test one book combining cartograf's core + gated VRP
with inercia's trend + carry. Treat every parameter choice as a trial.

## Non-goals

- No live trading.
- No paid data.
- No silent deletion of failed results.
