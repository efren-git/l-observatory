# PLAN — l'Observatori hardening (2026-10-19)

_Status: approved by Efren. Phase 1 (inercia) complete 2026-10-19. Phase 2
(cartograf) complete 2026-10-19. Phase 3 (combined book) is next._

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

## Phase 2 — cartograf (in progress)

- [x] shared excess-return handling (net-long vs self-financing);
- [x] stock sleeve labelled upward-biased and excluded from the book;
- [x] per-month live-name masking (inception dates) inside the cross-sections —
      implemented 2026-10-19; BAB's 2008–2010 score was 95–97% phantom names, now
      masked before scoring, normalisation and carry ranking;
- [x] fix the FX-carry double count (FX ETF total return plus explicit rate
      differential);
- [x] lag FRED monthly averages two months (publication-safe);
- [x] trial registry and DSR for the core book and overlay parameters;
- [x] synthetic smoke test;
- [x] re-run chapters 1-10; README now agrees with the JSONs, including the
      SVXY warm-up regression found during reconciliation
      (see cartograf/AUDIT-2026-10-19.md).

Phase 2 result: the mask repriced BAB 0.17 -> 0.10, the equal-weight book
0.66 -> 0.58, and the core book 0.72 -> 0.61. The 60/40 overlay still works
(0.77 -> 0.88), but the standalone core no longer clears SPY on Sharpe. Details in
`cartograf/AUDIT-2026-10-19.md` §5.

## Phase 3 — combined book (pre-specified 2026-10-19)

Goal: one book that combines the surviving sleeves without double-counting.

**Overlap audit first.**

- **Trend appears in both projects.** Use one implementation (inercia's, longer
  history); do not add a second trend sleeve.
- **Carry appears in both.** Cartograf's cross-asset carry failed (0.08, and it
  lowers a 60/40). Use inercia's carry only; test cartograf's as a separate
  variant, never both at once.
- BAB and gated VRP are cartograf-only.

**Frequency and windows.**

- Monthly returns: the proper VRP is monthly, and daily smoothing creates
  artificial autocorrelation.
- Window A: 2008-01 → 2026-10 without proper VRP (legacy SVXY, labelled).
- Window B: 2009-11 → 2026-10 with gated VRP (VIX3M starts 2009-09-18).
- Report both; never mix them in one statistic.

**Pre-specified variants (three, no grid).**

1. Equal-weight the non-overlapping survivors: inercia trend + inercia carry +
   cartograf BAB + cartograf gated VRP.
2. Inverse-vol of the same four (trailing 63 days, shifted one day).
3. 60/40 + 20% and 30% of variant 1 (one fixed family, not a search).

**Rules.**

- 5 bps per unit turnover (10 bps for vol ETFs); costs are charged in weights.
- A sleeve that is not live is flat, not backfilled.
- Benchmarks: SPY and 60/40; excess columns only for net-long series.
- Register every variant; report DSR with all trials and final variants.
- Success is an out-of-sample improvement in the 60/40's Sharpe and max
  drawdown, not standalone CAGR. If the combined book does not beat SPY
  standalone, say so.

**Acceptance.** One script regenerates the combined book and its metrics; a
synthetic smoke test; README chapter 11 with the honest result.

## Non-goals

- No live trading.
- No paid data.
- No silent deletion of failed results.
