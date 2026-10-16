# inercia — "A Strategy That Actually Survives"

*A readable walkthrough of everything in this project: what it is, why it exists, how the data works, and what the results mean.*

Project #3 of l'Observatori. Status: **complete (2026-10-15)** - trend + carry book, Sharpe 0.58; all candidate sleeves honestly tested.

## How to read this book

One file, read front to back. Every dataset and result is explained in plain language — the *why* and the *meaning*, not just the code.

## Chapter 1 — The thesis

Most "AI trading strategies" are curve-fit noise. They overfit a backtest, ignore transaction costs, leak the future, and never compare against the dumb benchmark. An experienced quant starts the other way around: from **evidence that a return pattern is real and has an economic reason to persist**, then tests it under conditions as hostile as the market itself.

The single most robust anomaly in finance is **momentum** — the tendency of what has been rising to keep rising — in two forms:

- **Cross-sectional momentum (XS):** rank assets by past return; buy the winners, sell/avoid the losers. (Jegadeesh & Titman, 1993.)
- **Time-series momentum (trend / TSMOM):** each asset long when its own trend is up, flat/short when down. (Moskowitz, Ooi & Pedersen, 2012.)

This project builds a momentum strategy the professional way — literature-grounded, walk-forward tested, cost-aware — and reports honestly what survives.

## Chapter 2 — The plan

### Research questions

1. Does momentum survive **out-of-sample and after costs** in the 2010s–2020s (the period when many anomalies decayed)?
2. **Cross-sectional vs time-series** momentum — which is more robust, and do they combine?
3. Does **volatility targeting** improve risk-adjusted returns and tame the strategy's crashes?
4. How bad is the **momentum crash** risk (2009, 2020) and can it be mitigated?

### Methodology

- **Universe:** a diversified set of liquid instruments across asset classes (equities US/developed/emerging, government bonds, commodities, gold, REITs, FX) — so the strategy is not a single-market bet.
- **Signals:** time-series momentum (multi-horizon) and cross-sectional momentum (12-1 month).
- **Construction:** volatility-scaled weights; a portfolio-level volatility target.
- **Costs:** explicit per-trade cost; turnover reported.
- **Validation:** walk-forward, sub-period stability, crisis windows, and honest benchmarks.
- **Discipline:** anything from Harvey-Liu-Zhu (multiple testing) is treated as a hurdle, not a formality.

### Milestones

0. Research + plan — *this chapter*
1. Multi-asset data
2. Backtest engine (costs, no lookahead)
3. Time-series momentum
4. Cross-sectional momentum
5. Vol targeting + crash protection
6. Combination + evaluation
7. Report

## Chapter 3 — What the literature actually says

Momentum is not folklore; it is one of the best-documented facts in asset pricing. The project is built on these results:

- **Jegadeesh & Titman (1993)** — US stocks ranked on 3–12 month returns: winners beat losers by ~1%/month. The founding XS-momentum result.
- **Carhart (1997)** — momentum is a distinct factor (the 4th, after market/size/value).
- **Moskowitz, Ooi & Pedersen (2012)** — time-series momentum across 58 futures: 1–12 month trends predict continued returns, in *every* asset class.
- **Hurst, Ooi & Pedersen (2017)** — trend-following worked for over a **century** across asset classes.
- **Asness, Moskowitz & Pedersen (2013)** — value and momentum work *everywhere* and are **negatively correlated** (a key combination insight).
- **Daniel & Moskowitz (2016); Barroso & Santa-Clara (2015)** — momentum **crashes** in sharp market rebounds; volatility-scaling fixes most of it.
- **Moreira & Muir (2017)** — scaling exposure by inverse volatility raises risk-adjusted returns.
- **McLean & Pontiff (2016)** — anomalies **decay ~58% after publication** — so out-of-sample testing is mandatory.
- **Harvey, Liu & Zhu (2016)** — with hundreds of factors tried, the significance bar must rise; most "discoveries" are false.

**The honest reading:** momentum is real, but (a) it decays, (b) it crashes, and (c) it is cost-sensitive. Any credible strategy must confront all three.

## Chapter 4 — The strategy (design)

**Core idea.** Combine the two forms of momentum, scale risk so no single asset or regime dominates, and control the crash.

1. **Signals.**
   - TS momentum: average of the sign of 1/3/6/12-month returns (an ensemble, more stable than any single lookback).
   - XS momentum: rank by 12-1 month return (skip the most recent month — the standard reversal adjustment).
2. **Positions.** Volatility-scaled (each position sized to a common risk), long/short by signal.
3. **Risk overlay.** Portfolio volatility target (~10%); scale down after high-vol regimes (this is the crash control).
4. **Costs.** A fixed per-trade cost; turnover tracked; results shown both gross and net.

## Chapter 5 — The test

Tested on 63 liquid ETFs across equities (US sectors, industries, 22 country funds), fixed income, commodities, metals, real estate and FX — monthly rebalanced, 5 bps costs, 10% volatility target, 2005–2026.

### 5.1 The honest standalone result

| Portfolio | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| **Strategy (net)** | 5.3% | 10.5% | **0.55** | −26% |
| SPY buy & hold | 10.9% | 18.6% | 0.65 | −55% |
| 60/40 (SPY/IEF) | 8.3% | 10.7% | **0.80** | −31% |

Standalone, the strategy's Sharpe (0.55) sits **below** the 60/40's 0.80. Momentum/trend is *not* a return-maximiser. But its correlation to SPY is **0.12** — almost zero. That near-zero correlation is the whole story.

### 5.2 The real edge: crisis alpha

Chart `04_annual.png`. Look at the two worst years for stocks: in **2008** the strategy returned **+8.2%** while SPY fell **−36.8%**, and in **2022** it returned **+6.2%** while SPY fell **−18.2%**. That is **crisis alpha** — trend-following goes short sustained declines (in equities *and* bonds) and captures the downside. It is not a free lunch: 2023 was −12.2% as the strategy was wrong-footed by a sharp rebound (the documented "momentum crash").

### 5.3 The value: diversification, not domination

Chart `03_equity_final.png`. Add 30% of the strategy to a 60/40:

| | Sharpe | Max DD |
|---|---|---|
| 60/40 alone | 0.80 | −31% |
| **60/40 + 30% strategy** | **0.91** | **−19%** |

A modest-Sharpe, near-uncorrelated return stream **lifts the portfolio Sharpe to 0.91 and nearly halves the drawdown**. That is what the strategy is *for*.

### 5.4 Going deeper: a second engine — carry

Trend's natural complement is **carry** (the other pillar of managed futures): get paid to hold higher-yielding assets, funded by lower-yielding ones. Built for G10 currencies — long the high-yielders, short the low-yielders, including the interest accrual itself, volatility-scaled.

Result: Sharpe **0.19** — low, but genuinely *uncorrelated* with trend (**0.03**).

### 5.5 The book (trend + carry)

Optimally weighted (74% trend / 26% carry), the combined book reaches Sharpe **0.58** — only modestly above trend alone (0.56). That is the honest arithmetic of combining engines: two uncorrelated streams give √(0.56² + 0.19²) ≈ 0.59, so a *weak* second engine can only add so much. The book's value is again the portfolio: **60/40 + 30% book → Sharpe 0.90, Max DD −23%**.

### 5.6 Two cautionary results

Two of the deeper tests failed, and reporting them matters:

- **Short-term reversal** (buy losers, sell winners) *lost* money — Sharpe **−0.52**. Asset-class ETFs **trend** at the one-month horizon; they do not mean-revert. Many apparent "edges" do not survive contact with the data.
- **Naive optimization** (a "tangency portfolio") printed a **0.67** Sharpe — by *shorting reversal 3.9×* and levering to 56% vol. That is not a strategy; it is a textbook over-optimization artifact (Harvey–Liu–Zhu in miniature). A real quant rejects it.

### 5.7 Hardening the construction (regime-aware risk, drawdown control)

Three overlays on the book: (i) **drawdown control** (CPPI - cut exposure as the drawdown deepens), (ii) **regime-volatility scaling** (de-risk when short-window vol exceeds long-window vol), and (iii) a **regime tilt** toward trend (crisis alpha) and away from carry (crash risk) when risk rises.

| Book | Sharpe | Sortino | Max DD | Worst year |
|---|---|---|---|---|
| Base | **0.67** | 0.84 | -22% | -9.7% |
| + drawdown control | 0.61 | 0.70 | -16% | -3.7% |
| + regime tilt (k=0.3) | 0.64 | 0.79 | -18% | -6.1% |

**The honest lesson - and it is the point of this whole exercise:** every overlay *reduced* Sharpe while reducing drawdowns. **Risk overlays are preference trades, not free lunches.** There is no free Sharpe hiding in the tail; there is only a choice of where to sit on the risk/return frontier. The base book is already near its efficient point - the overlays exist for an investor who would rather take a -16% drawdown than give up the ~0.06 of Sharpe it costs.

### 5.8 Finishing the sleeve hunt: a broad cross-sectional equity strategy

The classic high-Sharpe, low-correlation candidate is a **cross-sectional equity strategy** on a broad universe (498 S&P 500 names, 2005-2026). I built two price-based factors (no fundamentals, so no look-ahead):

| Sleeve | Sharpe | Corr to trend |
|---|---|---|
| Cross-sectional momentum (12-1) | -0.16 to +0.23 | 0.27 |
| Low-volatility (long low / short high) | -0.76 | ~0 |

**Both failed.** Cross-sectional momentum - the most celebrated factor in academic finance - delivered roughly **zero** over 2006-2026 (a clean decile run gives Sharpe -0.04): the documented **momentum decay**, plus the brutal 2009 and 2020-21 momentum crashes. Low-vol long/short was crushed by the 2020-21 high-beta melt-up (an -85% drawdown). Given the chance, the optimizer assigns the sleeve **zero weight**.

**So the honest finish:** the book stays **trend + carry** (Sharpe 0.58). There is no free high-Sharpe sleeve sitting in broad public data - every honestly-tested candidate failed. What *does* work is the portfolio: **60/40 + 30% book -> Sharpe 0.89, Sortino 1.16, Max DD -21%.**

## Chapter 6 — Conclusions

**What holds.** (1) Momentum/trend survives out-of-sample but modestly (Sharpe ≈ 0.55). (2) It is near-uncorrelated to equities (0.12). (3) It has genuine crisis alpha — positive in 2008 *and* 2022. (4) Added to a 60/40 it raises Sharpe to 0.91 and cuts the drawdown to −19%.

**What does not hold.** (1) It does **not** beat buy-and-hold or 60/40 standalone. (2) It decays and struggles in choppy markets (2015–16, 2023) — the momentum-crash risk is real. (3) At ~19× annual turnover it is cost-sensitive (5 bps cost ≈ 1.1%/yr drag).

**The lesson.** The value of a serious strategy is usually in its **correlation**, not its standalone return. A naive "AI strategy" chases a high backtest accuracy and ignores correlation and decay. The real work — the thing an experienced quant does — is building a return stream that is *robust* and *uncorrelated*, then using it to improve the portfolio. Trend-following is not a money printer; it is insurance that pays when you need it.

**On going deeper.** Adding engines helps only as much as their standalone quality and low correlation allow: carry (Sharpe 0.19, corr 0.03) lifted the book from 0.56 to just 0.58, and *hardening the construction* (drawdown control, regime scaling, regime tilt) did not raise the Sharpe either - every overlay traded return for a shallower drawdown. And the hunt for a high-Sharpe, uncorrelated sleeve ended honestly too: cross-sectional equity momentum (~0 Sharpe over the period) and low-vol long/short (-0.76) both failed. The final book is trend + carry at Sharpe 0.58; its value is proven at the portfolio level (60/40 + 30% book -> Sharpe 0.89, Sortino 1.16, Max DD -21%). The bigger lever is still the *portfolio* — the book as a 30% sleeve turns a 0.80-Sharpe 60/40 into a 0.90-Sharpe, −23%-drawdown portfolio. And two of the deeper ideas *failed* out-of-sample (reversal) or blew up under naive optimization (tangency) — which is exactly what honest research looks like.

---

## Appendix — References & reproducibility

Selected references (author, year, title): Jegadeesh & Titman 1993; Carhart 1997; Moskowitz, Ooi & Pedersen 2012; Asness, Moskowitz & Pedersen 2013; Barroso & Santa-Clara 2015; Daniel & Moskowitz 2016; McLean & Pontiff 2016; Harvey, Liu & Zhu 2016; Moreira & Muir 2017; Hurst, Ooi & Pedersen 2017.

    inercia/
    ├── README.md     this book
    ├── research/     notes and sources
    ├── data/raw/     prices
    ├── src/          engine, signals, evaluation
    └── output/       charts, metrics

*Conventions: reason before code; state uncertainty; be reproducible; if the strategy fails out-of-sample, that is the finding.*
