# inercia — "A Strategy That Actually Survives"

*A readable walkthrough of everything in this project: what it is, why it exists, how the data works, and what the results mean.*

Project #3 of l'Observatori. Status: **complete, refactored 2026-10-19; corrected 2026-10-20**. The refactor
consolidated a dozen duplicated scripts into one shared library, fixed a turnover
bug, removed a look-ahead in the volatility scaling, and made the FX-carry timing
publication-safe. Every number below comes from one run and agrees with
`output/*.json`.

> **2026-10-20 correction.** Sortino now uses downside deviation; annual Worst/Best exclude
> partial years; the drawdown/regime/tilt overlays pay 5 bps per unit of exposure change; a
> monthly-rebalanced 60/40 and an overlay DSR/bootstrap were added. Corrected headline: book
> **0.581**; 10%-target book **0.546**; 60/40+30% overlay **0.895** daily / **1.036** monthly;
> overlay DSR **0.987**. Full before/after tables and the cost-stress table:
> `AUDIT-2026-10-20.md`. The body is the historical record.

## How to read this book

One file, read front to back. Every dataset and result is explained in plain
language — the *why* and the *meaning*, not just the code.

## Chapter 1 — The thesis

Most "AI trading strategies" are curve-fit noise. They overfit a backtest, ignore
transaction costs, leak the future, and never compare against the dumb benchmark.
An experienced quant starts the other way around: from **evidence that a return
pattern is real and has an economic reason to persist**, then tests it under
conditions as hostile as the market itself.

The single most robust anomaly in finance is **momentum** — the tendency of what
has been rising to keep rising — in two forms:

- **Cross-sectional momentum (XS):** rank assets by past return; buy the winners,
  sell/avoid the losers. (Jegadeesh & Titman, 1993.)
- **Time-series momentum (trend / TSMOM):** each asset long when its own trend is
  up, flat/short when down. (Moskowitz, Ooi & Pedersen, 2012.)

This project builds a momentum strategy the professional way — literature-grounded,
walk-forward tested, cost-aware — and reports honestly what survives.

## Chapter 2 — The plan

### Research questions

1. Does momentum survive **out-of-sample and after costs** in the 2010s–2020s
   (the period when many anomalies decayed)?
2. **Cross-sectional vs time-series** momentum — which is more robust, and do they
   combine?
3. Does **volatility targeting** improve risk-adjusted returns and tame the
   strategy's crashes?
4. How bad is the **momentum crash** risk (2009, 2020) and can it be mitigated?

### Methodology

- **Universe:** 63 liquid ETFs across US sectors, industries, countries, government
  bonds, credit, commodities, gold, REITs and FX. A separate 498-name US stock
  universe is used only for the cross-sectional equity sleeve, which is labelled
  survivorship-biased and kept out of the combined book.
- **Signals:** time-series momentum (multi-horizon ensemble) and cross-sectional
  momentum (12-1 month).
- **Construction:** volatility-scaled weights; portfolio-level volatility target.
- **Costs:** explicit per-trade cost; turnover reported and charged. 5 bps for
  ETFs, 10 bps for single-name equities.
- **Validation:** sub-period stability, crisis windows, honest benchmarks, and a
  Deflated Sharpe Ratio with an explicit trial count.
- **Discipline:** anything from Harvey-Liu-Zhu (multiple testing) is treated as a
  hurdle, not a formality.

## Chapter 3 — What the literature actually says

Momentum is not folklore; it is one of the best-documented facts in asset pricing.
The project is built on these results:

- **Jegadeesh & Titman (1993)** — US stocks ranked on 3–12 month returns: winners
  beat losers by ~1%/month. The founding XS-momentum result.
- **Carhart (1997)** — momentum is a distinct factor (the 4th, after
  market/size/value).
- **Moskowitz, Ooi & Pedersen (2012)** — time-series momentum across 58 futures:
  1–12 month trends predict continued returns, in *every* asset class.
- **Hurst, Ooi & Pedersen (2017)** — trend-following worked for over a **century**
  across asset classes.
- **Asness, Moskowitz & Pedersen (2013)** — value and momentum work *everywhere*
  and are **negatively correlated** (a key combination insight).
- **Daniel & Moskowitz (2016); Barroso & Santa-Clara (2015)** — momentum **crashes**
  in sharp market rebounds; volatility-scaling fixes most of it.
- **Moreira & Muir (2017)** — scaling exposure by inverse volatility raises
  risk-adjusted returns.
- **McLean & Pontiff (2016)** — anomalies **decay ~58% after publication** — so
  out-of-sample testing is mandatory.
- **Harvey, Liu & Zhu (2016)** — with hundreds of factors tried, the significance
  bar must rise; most "discoveries" are false.
- **Bailey & López de Prado (2014)** — the Deflated Sharpe Ratio corrects a
  backtest's Sharpe for the number of trials that produced it.

**The honest reading:** momentum is real, but (a) it decays, (b) it crashes, and
(c) it is cost-sensitive. Any credible strategy must confront all three.

## Chapter 4 — The strategy (design)

**Core idea.** Combine the two forms of momentum, scale risk so no single asset or
regime dominates, and control the crash.

1. **Signals.**
   - TS momentum: average of the sign of 1/3/6/12-month returns (an ensemble,
     more stable than any single lookback).
   - XS momentum: rank by 12-1 month return (skip the most recent month — the
     standard reversal adjustment).
2. **Positions.** Volatility-scaled (each position sized to a common risk),
   long/short by signal, gross exposure normalised to one before the portfolio
   volatility target.
3. **Risk overlay.** Portfolio volatility target (~10%); scale down after
   high-vol regimes and cap leverage at 3×. A second, optional target is applied
   to the book; both versions are reported.
4. **Costs.** A fixed per-trade cost; turnover tracked; results shown both gross
   and net.

## Chapter 5 — The test

Tested on 63 liquid ETFs, monthly rebalanced, 5 bps costs, 10% volatility target,
2004–2026. Signals need 12 months of history, so the first live month is 2005.
Benchmarks: SPY buy-and-hold and a 60/40 SPY/IEF portfolio.

### 5.1 The honest standalone result

| Portfolio | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| **Strategy (net)** | 5.3% | 10.5% | **0.547** | −26.4% |
| Strategy (gross) | 6.3% | 10.5% | 0.636 | −24.0% |
| SPY buy & hold | 10.9% | 18.6% | 0.649 raw / **0.539 excess** | −55.2% |
| 60/40 (SPY/IEF) | 8.29% | 10.73% | 0.796 raw / **0.606 excess** | −31.4% |

Standalone, the strategy's Sharpe (0.547) sits **below** the 60/40's 0.796. It is
not a return-maximiser. Its correlation to SPY is **0.123** — almost zero. That
near-zero correlation is the whole story. Costs are real: at 18.9× annual turnover
and 5 bps, the drag is about **0.94%/yr**.

The excess-return convention matters here. SPY and 60/40 are net-long, so their
excess Sharpe subtracts the T-bill rate. The trend and carry sleeves are
self-financing long/short books; subtracting T-bills from them would be
double-counting. They are reported raw.

### 5.2 The real edge: crisis alpha

Chart `04_annual.png`. Look at the two worst years for stocks: in **2008** the
strategy returned **+8.2%** while SPY fell **−36.8%**, and in **2022** it returned
**+6.2%** while SPY fell **−18.2%**. That is **crisis alpha** — trend-following
goes short sustained declines (in equities *and* bonds) and captures the downside.
It is not a free lunch: 2023 was **−12.2%** while SPY rose 26.2%, as the strategy
was wrong-footed by a sharp rebound (the documented "momentum crash").

Sub-period Sharpes tell the decay story: 2005–07 **1.38**, 2008–09 **0.75**,
2010–19 **0.44**, 2020–26 **0.19**. The edge is real but weaker in the recent
decade.

### 5.3 The value: diversification, not domination

Chart `03_equity_final.png`. Add 30% of the strategy to a 60/40:

| | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| 60/40 alone | 8.29% | 10.73% | 0.796 | −31.4% |
| **60/40 + 30% strategy** | 7.62% | 8.51% | **0.905** | **−19.4%** |

A modest-Sharpe, near-uncorrelated return stream lifts the portfolio Sharpe to
0.905 and cuts the drawdown by about a third. That is what the strategy is *for*.

### 5.4 Going deeper: a second engine — carry

Trend's natural complement is **carry** (the other pillar of managed futures): get
paid to hold higher-yielding assets, funded by lower-yielding ones. Built for G10
currencies — long the high-yielders, short the low-yielders, including the
interest accrual itself, volatility-scaled.

Result: CAGR **1.35%**, Vol **9.17%**, Sharpe **0.192**, Max DD **−29.9%** — low,
but genuinely *uncorrelated* with trend (**0.033**). Turnover is 6.5×/yr.

The refactor made the rate timing publication-safe: FRED's `IR3TIB` series are
monthly averages, so they are now lagged **two months** before use. The old code
applied the current month's average from day one, which was a small look-ahead.

### 5.5 The book (trend + carry)

The historical headline is a fixed **74% trend / 26% carry** book. Two versions
are reported:

| Book | CAGR | Vol | Sharpe | Max DD | Worst year |
|---|---|---|---|---|---|
| **Unlevered 74/26 (headline)** | 4.57% | 8.21% | **0.585** | −23.9% | −8.4% |
| 74/26 with 10% vol target | 6.18% | 10.85% | 0.607 | −36.3% | −13.0% |
| Walk-forward weights, unlevered | 3.70% | 8.18% | 0.485 | −25.8% | −10.2% |
| Walk-forward weights, 10% target | 5.86% | 10.92% | 0.577 | −37.7% | −14.8% |

The difference is leverage, not alpha. Because trend and carry are nearly
uncorrelated, the 74/26 book only realizes about **8.2% vol**. Forcing it to 10%
requires an average **1.38×** leverage (max 3× in the cap), which scales returns
up but deepens the drawdown to −36%. The old README's −23% drawdown was the
unlevered book; the refactor now reports both instead of hiding the choice.

Walk-forward weights (expanding window, long-only, annual refit) give a lower
Sharpe: **0.485** unlevered. The latest walk-forward weight is about 82.6% trend /
17.4% carry. The fixed 74/26 was chosen in-sample and is counted as a trial.

The portfolio value of the unlevered book:

| | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| 60/40 alone | 8.29% | 10.73% | 0.796 | −31.4% |
| **60/40 + 30% book** | 7.32% | 8.29% | **0.894** | **−23.2%** |

A 0.894 Sharpe with a −23% drawdown, versus 0.796 / −31.4% for the 60/40 alone.
Again: the value is in the correlation, not the standalone return.

### 5.6 Two cautionary results

Two of the deeper tests failed, and reporting them matters:

- **Short-term reversal** (buy losers, sell winners) *lost* money — Sharpe
  **−0.247**, Max DD −53.6%. Asset-class ETFs **trend** at the one-month horizon;
  they do not mean-revert. Many apparent "edges" do not survive contact with the
  data.
- **Naive optimization** (a "tangency portfolio") prints a **0.585** Sharpe
  in-sample with weights 0.747 trend / 0.273 carry / −0.02 reversal. It looks
  reasonable now only because the canonical backtest and costs are applied; it is
  still an in-sample fit and is not a strategy. The old code's extreme
  "short reversal 3.9×" artifact is gone, but the lesson stands: in-sample
  tangency is not evidence.

### 5.7 Hardening the construction (regime-aware risk, drawdown control)

Three overlays on the **10%-target book**: (i) **drawdown control** (CPPI — cut
exposure as the drawdown deepens), (ii) **regime-volatility scaling** (de-risk when
short-window vol exceeds long-window vol), and (iii) a **regime tilt** toward trend
and away from carry when risk rises.

| Book | Sharpe | Sortino | Max DD | Worst year |
|---|---|---|---|---|
| Base (10% target) | 0.607 | 0.752 | −36.3% | −13.0% |
| + drawdown control | **0.662** | 0.763 | **−18.6%** | −4.1% |
| + regime scaling | 0.606 | 0.756 | −33.0% | −12.0% |
| + both (hardened) | 0.630 | 0.728 | **−18.3%** | −3.8% |

This is the honest lesson: drawdown control *did* improve Sharpe here (0.607 →
0.662) while cutting the drawdown in half, but it is still a preference trade, not
a free lunch. Regime scaling alone did nothing; combining it with drawdown control
gave up a little Sharpe versus drawdown control alone. There is no free Sharpe
hiding in the tail; there is only a choice of where to sit on the risk/return
frontier.

The regime **tilt** did not help: Sharpe 0.607 → 0.593 (k=0.3) → 0.557 (k=0.6) →
0.484 (k=1.0), with *worse* drawdowns. It was a reasonable hypothesis; the data
rejected it.

### 5.8 Finishing the sleeve hunt: a broad cross-sectional equity strategy

The classic high-Sharpe, low-correlation candidate is a **cross-sectional equity
strategy** on a broad universe (498 S&P 500 names, 2005–2026). Two price-based
factors (no fundamentals, so no look-ahead):

| Sleeve | CAGR | Vol | Sharpe | Max DD | Turnover |
|---|---|---|---|---|---|
| Cross-sectional momentum (12-1) | 0.72% | 10.44% | **0.121** | −30.6% | 11.4× |
| Low-volatility (long low / short high) | −8.53% | 10.40% | **−0.805** | −87.0% | 4.9× |
| 50/50 sleeve | −4.21% | 7.15% | **−0.566** | −61.5% | — |

**Both failed.** Cross-sectional momentum — the most celebrated factor in academic
finance — delivered roughly **zero** over 2006–2026 after 10 bps costs. The old
README reported +0.23 because the sleeve's turnover line was broken and costs were
never charged (see Chapter 7). Low-vol long/short was crushed by the 2020–21
high-beta melt-up. Given the chance, the optimizer assigns the sleeve zero weight.

There is a second, larger problem: the universe is **today's** S&P 500. Delisted
losers are absent, so the result is **upward-biased**. There is no free
point-in-time membership data. The sleeve is therefore reported separately and
**excluded from the combined book**; it is not evidence of a tradable edge.

**So the honest finish:** the book stays **trend + carry** (unlevered Sharpe
0.585). There is no free high-Sharpe sleeve sitting in broad public data — every
honestly-tested candidate failed. What *does* work is the portfolio: **60/40 + 30%
book → Sharpe 0.894, Sortino 1.16, Max DD −23.2%.**

## Chapter 6 — Conclusions

**What holds.** (1) Momentum/trend survives out-of-sample but modestly (Sharpe
≈ 0.55). (2) It is near-uncorrelated to equities (0.123). (3) It has genuine crisis
alpha — positive in 2008 *and* 2022. (4) Added to a 60/40 it raises Sharpe to 0.905
and cuts the drawdown to −19.4%. (5) The trend+carry book, unlevered, has Sharpe
0.585 and improves a 60/40 to 0.894 / −23.2%.

**What does not hold.** (1) It does **not** beat buy-and-hold or 60/40 standalone.
(2) It decays and struggles in choppy markets (2015–16, 2023) — the momentum-crash
risk is real. (3) At ~19× annual turnover it is cost-sensitive (5 bps ≈ 0.94%/yr
drag). (4) Forcing the book to a 10% vol target requires ~1.38× average leverage
and deepens the drawdown to −36%; the 10% label was doing more work than the old
README admitted. (5) Cross-sectional equity momentum and low-vol long/short both
failed after costs, and the stock universe is survivorship-biased.

**The lesson.** The value of a serious strategy is usually in its **correlation**,
not its standalone return. A naive "AI strategy" chases a high backtest accuracy
and ignores correlation and decay. The real work — the thing an experienced quant
does — is building a return stream that is *robust* and *uncorrelated*, then using
it to improve the portfolio. Trend-following is not a money printer; it is
insurance that pays when you need it.

**On multiple testing.** Counting every variant actually run in this project gives
**26 trials**. The Deflated Sharpe Ratio for the final book is **0.769** under that
count, and **0.987** if only the two final published variants are counted. Both are
reported; the all-trials number is the honest one. The gap is the cost of the
search.

## Chapter 7 — The 2026-10-19 refactor (what changed and why)

The old project had ten scripts that re-implemented the same loading, signal,
backtest and statistics code. They disagreed with each other and with the README.
The refactor replaced them with one library; the old filenames remain as thin
wrappers so old commands still work.

What was fixed:

1. **Turnover bug in `sleeve.py`.** The code did `wd.mul(scale, axis=1)`; the
   scale is a date-indexed Series, so axis 1 aligned it to *ticker columns* and
   produced all-NaN weights. `turn.diff()` was therefore zero, costs were never
   charged, and `turnover_mom` printed 0.0. The correct axis is 0. The
   cross-sectional momentum Sharpe fell from +0.23 (cost-free) to +0.121 (10 bps).
2. **Full-sample volatility scaling.** `book.py` and `combo.py` scaled returns by
   `r.std()` over the whole sample — a look-ahead. The canonical backtest uses a
   rolling 60-day vol, shifted one day.
3. **FX-carry timing.** Monthly-average policy rates are lagged two months before
   use. The old code applied the current month's average from day one.
4. **One excess-return convention.** Net-long benchmarks get raw and excess
   columns; self-financing sleeves are raw. No more subtracting T-bills from a
   long/short book.
5. **Survivorship labelled.** The stock sleeve is explicitly marked upward-biased
   and excluded from the book.
6. **Trial registry and DSR.** `trials.json` records 26 trials and reports the DSR
   under both trial counts.
7. **Synthetic smoke tests.** No real data is committed; `tests/test_smoke.py`
   builds a synthetic panel and checks signals, costs, turnover and no-look-ahead.

The headline numbers that changed:

| Quantity | Old README | Refactored |
|---|---|---|
| Carry Sharpe | 0.19 (74/26) or 0.13 (85/15) | **0.192** (one definition) |
| Book Sharpe | 0.583 | **0.585** unlevered / 0.607 at 10% target |
| Book Max DD | −23.3% | **−23.9%** unlevered / −36.3% at 10% target |
| 60/40 + 30% book | 0.903 / −23% | **0.894 / −23.2%** |
| XS momentum Sharpe | +0.23 | **+0.121** after 10 bps costs |
| Equity sleeve Sharpe | −0.312 | **−0.566** after costs |
| Turnover (XS sleeve) | 0.0 (bug) | **11.4×/yr** |

## Chapter 11 — Phase 3: the combined book

The cross-project book is `PHASE3.md`; `src/run_phase3.py` regenerates it. It
uses inercia's trend and carry once, plus cartograf's BAB and gated VRP, at
monthly frequency. Window B (2009-11+, gated VRP): 60/40 + 30% equal **1.18
Sharpe / −14.5% MaxDD**, inverse-vol **1.23 / −15.1%**, versus the 60/40's
**1.10 / −20.5%**. Window A (2008-01+, legacy SVXY) does **not** improve Sharpe;
it only cuts the drawdown. The standalone book does not beat the 60/40, and BAB
is a drag. See `PHASE3.md` for the full tables and caveats.

## Chapter 12 — Phase 4: robustness

`PHASE4.md` holds the robustness checks for the Phase 3 book; `src/run_phase4.py`
regenerates them. The overlay is positive in every pre-specified fold (worst
2019–2023 at 0.86–0.89), survives VRP costs up to 25 bps/month at the portfolio
level, and is positive in all 15 block sample-splits (min 0.49–0.54). The
post-hoc 24-month holdout is 1.46–1.51, but it is not blind. The 30% size is not
special: 40% looks better in-sample, which is a warning against re-optimising it.

## Appendix — References & reproducibility

Selected references: Jegadeesh & Titman 1993; Carhart 1997; Moskowitz, Ooi &
Pedersen 2012; Asness, Moskowitz & Pedersen 2013; Barroso & Santa-Clara 2015;
Daniel & Moskowitz 2016; McLean & Pontiff 2016; Harvey, Liu & Zhu 2016; Moreira &
Muir 2017; Hurst, Ooi & Pedersen 2017; Bailey & López de Prado 2014.

### Run it

```bash
cd inercia
./.venv/bin/python3 src/run.py all          # every chart and JSON
./.venv/bin/python3 src/run.py finalbook    # one stage
./.venv/bin/python3 -m unittest discover -s tests -v
```

Legacy entry points (`src/strategy.py`, `src/book.py`, `src/sleeve.py`, …) are
one-line wrappers around the same pipeline.

### Layout

```
inercia/
├── README.md              this book
├── PLAN.md                the hardening plan and decisions
├── data/raw/              prices, FX, FRED rates, stock prices (git-ignored)
├── src/
│   ├── inercia/
│   │   ├── config.py      paths and defaults
│   │   ├── data.py        cached loaders, publication-safe rates
│   │   ├── stats.py       performance, vol target, drawdown, DSR
│   │   ├── signals.py     TS/XS momentum, reversal, carry z-score
│   │   ├── backtest.py    one canonical panel backtest
│   │   ├── engines.py     trend, carry, stock sleeves
│   │   └── pipeline.py    artifacts and charts
│   ├── run.py             recommended entry point
│   └── strategy*.py …     thin legacy wrappers
├── tests/                 synthetic smoke tests
└── output/                charts, metrics JSON, trials.json
```

### Data caveats

- ETFs enter at inception (first valid price); there is no backfilling.
- The stock universe is current S&P 500 membership — upward-biased.
- The local FRED cache ends at different dates per series (some 2026-01, some
  2026-08). Rates are forward-filled after the last observation; rerun
  `src/fetch_carry.py` for fresher data.
- FRED `IR3TIB` series are monthly averages; the pipeline lags them two months.
- No live trading. Research only.
