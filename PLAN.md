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

## Phase 3 — combined book (pre-specified 2026-10-19; complete 2026-10-20)

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

**Result (2026-10-20).** Implemented in `inercia/src/inercia/phase3.py`,
run with `inercia/src/run_phase3.py`, written up in `inercia/PHASE3.md`.

- Window B (2009-11+, gated VRP): 60/40 + 30% equal **1.18 Sharpe / −14.5%
  MaxDD**; inverse-vol **1.23 / −15.1%**; 60/40 **1.10 / −20.5%**. The
  pre-specified overlay improves both Sharpe and drawdown.
- Window A (2008-01+, legacy SVXY): overlay **0.86** vs 60/40 **0.86**; only the
  drawdown improves (−19.7% vs −27.6%). The legacy proxy is not enough.
- The standalone book does not beat the 60/40 (equal 0.88, inverse-vol 1.09).
- BAB is a drag; the no-BAB inverse-vol overlay is 1.27 / −14.8%, but that is a
  post-audit sensitivity, not the pre-specified claim.
- DSR 0.972–0.984 with 61 trials; bootstrap CI 0.72–1.83.

## Phase 4 — robustness (added and completed 2026-10-20)

Phase 3 fixed the book; Phase 4 tests whether it survives. No parameters are
changed.

- Contiguous pre-specified folds: worst 2019–2023 at 0.86–0.89; 2024–2026 at
  1.65–1.71.
- VRP cost stress 5/10/25 bps/month: sleeve Sharpe 1.18 / 1.14 / 1.00; the 30%
  overlay 1.18 / 1.18 / 1.16.
- Combined-book cost stress 5/10/25 bps: overlay 1.18 / 1.18 / 1.18.
- 6-block, 2-held-out combinatorial sample-split (15 splits): mean 1.18–1.26,
  min 0.49–0.54, 100% positive.
- Post-hoc 24-month holdout: 1.46–1.51; not blind.
- Overlay-size sensitivity 20/30/40%: monotone; 40% looks better in-sample, so
  do not re-optimise the 30% choice after seeing it.

Implementation: `inercia/src/inercia/phase4.py`, `src/run_phase4.py`,
`inercia/PHASE4.md`, `output/phase4_metrics.json`.

## Phase 5 — pairs, hedging, paper trading (added 2026-10-20)

Test whether a simple pairs/stat-arb sleeve can improve or hedge the Phase 3
book, and start a forward paper-trading ledger.

- KO/PEP fails: ADF −0.77, half-life 1,029 days, default Sharpe −0.095.
- Fixed eight-pair screen: V/MA is the only cointegrated pair (ADF −5.25,
  half-life 63 days), default Sharpe 0.073.
- 12-variant grid per pair: best V/MA 0.19, best KO/PEP 0.21, both in-sample;
  worst −0.24 / −0.21. 103 total trials.
- 20% V/MA hedge: Phase 3 overlay Sharpe 1.183 → 1.199, MaxDD −14.5% → −11.1%,
  CAGR 8.33% → 6.66%. A preference trade, not alpha.
- Paper ledger: `output/paper_trade.json`, `paper_trade_log.csv`; no orders.

Implementation: `inercia/src/inercia/pairs.py`, `src/inercia/phase5.py`,
`src/run_phase5.py`, `src/paper_trade.py`, `inercia/PHASE5.md`.

## Phase 6 — pre-registered core parameter study (added 2026-10-20)

12 one-factor variants, fixed before the run; selection 2005-01→2018-12,
holdout 2019-01→latest; select by selection Sharpe; DSR with 115 trials.

- Best selection: `lb_6_12` (trend 6/12): selection 0.947, holdout **0.330**,
  full 0.693, full MaxDD −19.6%.
- Base: selection 0.871, holdout 0.146, full 0.581, MaxDD −23.9%.
- Holdout DSR **0.048**; bootstrap −0.208 to 0.992. Not significant after
  deflation.
- Cost stress on `lb_6_12`: full/holdout 0.693/0.330 at 5 bps, 0.608/0.232 at
  10 bps, 0.351/−0.061 at 25 bps.
- Verdict: no parameter change is justified; keep the base, treat `lb_6_12` as
  a forward-test candidate.

Implementation: `inercia/src/inercia/phase6.py`, `src/run_phase6.py`,
`inercia/PHASE6.md`, `output/phase6_metrics.json`.

## Phase 7 — tail hedges (added and completed 2026-10-20)

Pre-registered before the run: four fixed hedges on the 60/40 + 30% Phase 3
overlay (short 5%/10% SPY, long 5% VIX spot, short 5% SVXY), selection
2005–2018 (effectively 2009-11+), holdout 2019+, 5/10/25 bps, DSR at 119 trials.

- short SPY 5%: holdout Sharpe 1.095 vs 1.079, MaxDD −13.25% vs −14.46%;
  marginal Sharpe **−0.915** (t −3.77), hit rate 33.8%, bootstrap −1.37…−0.49.
- short SPY 10%: holdout 1.113, MaxDD −12.04%; same marginal stream, scaled.
- short SVXY 5%: holdout 1.116, MaxDD −13.47%; marginal Sharpe −0.571 (t −2.21),
  convexity −1.39 pp.
- long VIX spot 5%: looks best (holdout 1.746) but is not investable; it earns
  the arithmetic mean of a mean-reverting index's percentage changes and ignores
  futures roll.
- Vol-matched drawdown: every investable hedge is worse than proportional. This
  is de-risking, not convexity.
- Verdict: no hedge is adopted; the base stays. The pre-registered rule was too
  weak because it scored the hedged portfolio, not the hedge.

Implementation: `inercia/src/inercia/phase7.py`, `src/run_phase7.py`,
`inercia/PHASE7.md`, `output/phase7_metrics.json`, `output/14_phase7.png`.

## Non-goals

- No live trading.
- No paid data.
- No silent deletion of failed results.
