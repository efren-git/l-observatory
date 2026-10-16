# cartograf — "How Much of the Literature Actually Survives?"

*A readable walkthrough of everything in this project: what it asks, why, how the data
works, and what the results mean.*

Project #4 of l'Observatori. Status: **complete (2026-10-16)** — five published return
patterns tested on free data, walk-forward, net of costs, plus an equity-factor cross-check, plus
two follow-ups: **network momentum** (§8) and a **proper volatility-risk-premium** test (§9).

## How to read this book

One file, front to back. Every dataset and every number is explained in plain language.
Charts live in `output/`; the raw numbers in `output/metrics.json`.

- `inercia` asked *"does momentum survive?"* and answered yes, modestly.
- `cartograf` asks the wider question: **of the return patterns the literature claims are
  real, which ones are still alive in 2008–2026, on instrument we can actually trade, after
  costs?** — and then: does the survivors' *book* beat what you already own?

The honest answer is: most of them are dead or weak; two are useful; and the whole thing is
worth less as a return engine than as **insurance and diversification**.

## Chapter 1 — The thesis

A quantitative-fiance reading list hands you a pile of "edges": momentum, value, carry,
low-volatility, betting-against-beta, the volatility risk premium. Each has a famous paper.
Each was true once. The trap is to believe all of them at once, backtest them with hindsight,
and add them together into a fantasy Sharpe.

The professional move is the opposite: take each claim, implement the *dumbest faithful
version* of it, test it out-of-sample after realistic costs, and throw away everything that
does not survive. What is left is a short list — and the short list is usually disappointing.
That disappointment *is* the result.

So the deliverable here is not "a strategy that beats the S&P 500." It is a **map**: which
published edges are real, how they behave in a crisis, how they correlate with each other and
with equities, and what they are actually good for.

## Chapter 2 — The plan

Five sleeves, one per published pattern:

1. **trend** — time-series momentum, multi-horizon (Moskowitz, Ooi & Pedersen 2012).
2. **xsmom** — cross-sectional momentum, 12-1 (Jegadeesh & Titman 1993).
3. **value** — cross-asset long-horizon reversal, 5-year (Asness, Moskowitz & Pedersen 2013).
4. **bab** — betting against beta / defensive equity (Frazzini & Pedersen 2014).
5. **vrp** — the volatility risk premium, gated by the VIX term structure.

Then three ways to combine them — equal weight, inverse-volatility, and **Hierarchical Risk
Parity** (López de Prado 2016) — because *how* you combine weak signals matters as much as
which ones you pick.

Rules that never bend:

- **No lookahead.** A signal computed at a month-end is applied from the *next* trading day.
- **Costs are real.** 5 bps per unit turnover (10 bps for the vol ETFs); turnover is reported.
- **Volatility targeting is done in the weights, not by rescaling returns afterwards** — so
  the trading costs reflect the portfolio you would actually hold.
- **Benchmarks are mandatory.** SPY buy-and-hold and a 60/40 (SPY/IEF).
- **Negatives are reported.** A sleeve that loses money is a finding, not an embarrassment.

## Chapter 3 — What the literature actually says

The classical results are the backbone (and are cited in `inercia` too): Jegadeesh & Titman
(1993) on momentum; Moskowitz, Ooi & Pedersen (2012) on time-series momentum across 58
futures; Asness, Moskowitz & Pedersen (2013) that value and momentum work "everywhere" and
are negatively correlated; Frazzini & Pedersen (2014) on betting against beta; López de Prado
(2016) on HRP. Two papers frame the *skepticism*: McLean & Pontiff (2016) — anomalies decay
~58% after publication — and Harvey, Liu & Zhu (2016) — with hundreds of factors tested, most
"discoveries" are false.

From arXiv `q-fin` (the archive at arxiv.org/archive/q-fin), the recent literature is largely
about *pricing, risk, market microstructure and machine learning*, not about free money. The
papers that actually informed the design:

- **Lempérière et al., "Two centuries of trend following" (1404.3274)** — trend is anomalous
  across four asset classes with a t-stat ≈ 5 since 1960: the case for trend as a *persistent*
  effect, not a data-mined one.
- **"Optimal trend following portfolios" (2201.06635)** — a theory note: the optimal trend
  portfolio decomposes into a few basic components; useful for sanity, not a recipe.
- **"Follow the Leader: Enhancing Systematic Trend-Following Using Network Momentum"
  (2501.07135, 2025)** — lead-lag "momentum spillover" between markets. Interesting; noted as
  the most promising *new* direction (see Chapter 7).
- **"Schur Complementary Allocation" (2411.05807)** — unifies HRP and minimum-variance; it
  confirms that hierarchical methods are *heuristics*, which is exactly what our result shows.

The honest reading: the *robust* literature (multi-asset, out-of-sample, cost-aware) points to
trend and carry as the durable engines, value/momentum as real-but-decayed, and everything
ML-flavoured as needing far more discipline than it usually gets.

## Chapter 4 — The data (all free, no keys)

| Source | What it gives | Why it matters |
|---|---|---|
| **Yahoo Finance via `yfinance`** | adjusted daily closes, 39 ETFs + 5 context indices | the tradable universe |
| **Ken French Data Library** | monthly equity factor returns (Mkt-RF, SMB, HML, RMW, CMA, MOM) | the academic factor zoo, for a long-history cross-check |
| **VIX term structure** (`^VIX`, `^VIX3M`) | implied-vol curve | gates the volatility-risk-premium sleeve |

The ETF universe spans equities (US, developed, EM, styles), fixed income (Treasuries, TIPS,
IG, HY, EM debt), commodities, metals, FX and REITs — so a sleeve is a *multi-asset* bet, not
a disguised long-equity position. Data is re-fetched by `src/fetch_data.py`; raw CSVs are kept
out of git (they are large and reproducible).

## Chapter 5 — The test

Window: **2008-01-02 → 2026-10-15** (5-year value needs history; the start is honest, not
cherry-picked). Monthly rebalance, daily P&L, all sleeves scaled to a **10% volatility target**.

### 5.1 The five sleeves

| Sleeve | CAGR | Vol | Sharpe | Max DD | corr to SPY | Turnover /yr |
|---|---|---|---|---|---|---|
| trend | 6.8% | 12.1% | **0.61** | −22.0% | 0.04 | 20.9× |
| xsmom | 0.6% | 10.8% | 0.11 | −40.2% | 0.16 | 10.7× |
| value | −2.7% | 9.0% | **−0.26** | −55.8% | −0.14 | 5.2× |
| bab | 1.3% | 10.7% | 0.17 | −36.4% | 0.10 | 4.0× |
| vrp | 2.4% | 11.2% | 0.27 | −43.0% | 0.36 | 1.3× |

Three of the five are **weak or negative**. Cross-sectional momentum barely clears zero;
cross-asset value actually *loses* money; betting-against-beta is a shadow of its published
self. Only trend is clearly real — and even it is not a return-maximiser (SPY made 11.3% a
year against trend's 6.8%).

But look at the last two columns. Trend is essentially **uncorrelated with stocks (0.04)**,
and value is **negatively** correlated with almost everything (−0.36 to xsmom, −0.23 to trend
and vrp). A sleeve can be a bad standalone strategy and a good portfolio ingredient. That is
the whole game.

### 5.2 Combining them — and a nice negative

| Book | CAGR | Vol | Sharpe | Max DD | corr to SPY |
|---|---|---|---|---|---|
| equal-weight (all 5) | 6.4% | 11.0% | 0.62 | −30.1% | 0.23 |
| inverse-vol | 4.9% | 10.4% | 0.52 | −29.1% | 0.28 |
| **HRP** | 3.6% | 11.2% | **0.37** | −48.0% | 0.21 |
| **core: trend+bab+vrp** | 7.5% | 11.0% | **0.72** | −20.3% | 0.26 |

Two honest lessons:

- **HRP lost to naive equal weight** (0.37 vs 0.62). HRP is a *risk* allocator and blind to
  expected return; in 2020 it had loaded ~29% on the losing value sleeve and paid for it
  (−24% that year). With only five sleeves and a 36-month window, the elegant method is worse
  than the dumb one. (This is Harvey–Liu–Zhu in miniature: sophistication is not edge.)
- **Dropping the two failures helped.** The "core" book of the three survivors — trend, bab,
  vrp — is the best of all: Sharpe **0.72**, max drawdown −20%.

### 5.3 The point: what the book is for

| Portfolio | CAGR | Vol | Sharpe | Sortino | Max DD |
|---|---|---|---|---|---|
| SPY | 11.3% | 19.7% | 0.64 | 0.78 | −51.9% |
| 60/40 | 8.4% | 11.4% | 0.77 | 0.97 | −30.8% |
| 60/40 + 30% equal book | 8.0% | 9.3% | 0.88 | 1.11 | −18.8% |
| **60/40 + 30% core book** | 8.4% | 9.4% | **0.90** | **1.14** | −19.2% |

Adding a 30% sleeve of the core book turns a 0.77-Sharpe, −31%-drawdown 60/40 into a
**0.90-Sharpe, −19%-drawdown** portfolio — *without* giving up return (CAGR 8.4% vs 8.4%).

That is the honest, defensible claim. It is not "beat the S&P 500". It is "improve the
risk-adjusted return of a normal portfolio", which is a much lower and much more honest bar.

### 5.4 Crisis behaviour

Annual returns of the equal-weight book vs SPY:

| Year | SPY | book |
|---|---|---|
| 2008 | −36.8% | **+13.2%** |
| 2018 | −4.6% | −17.5% |
| 2020 | +18.3% | −13.9% |
| 2022 | −18.2% | **+15.5%** |

The book is genuinely good in slow crises (2008, 2022) and genuinely bad in sharp reversals
(2020's rebound, 2018's vol spike). That is the known shape of trend + short-vol: it is
insurance that pays in a long downturn and costs you in a violent recovery.

### 5.5 Cross-check: the academic equity factors, 1963 → 2026

Using Ken French's monthly factor returns, the same "does it survive?" question applied to
the classic factors (Sharpe, 1963–2026 vs 2008–2026):

| Factor | 1963–2026 | 2008–2026 | Verdict |
|---|---|---|---|
| Mkt-RF | 0.47 | 0.67 | alive |
| SMB (size) | 0.21 | **−0.00** | dead |
| HML (value) | 0.34 | **−0.04** | dead since 2007 |
| RMW (profitability) | 0.38 | **0.38** | alive |
| CMA (investment) | 0.41 | 0.06 | faded |
| MOM (momentum) | 0.45 | 0.02 | dead (and −78% max DD) |

This is the "factor zoo" in one table: the factors published *before* the data-mining critique
(value, size, momentum) have largely stopped paying, while the ones added in the 2010s
(profitability) still work — and the market itself keeps paying.

## Chapter 6 — Verdict

- **Did we beat the S&P 500?** No. Nothing here does. SPY returned 11.3%/yr at Sharpe 0.64;
  the best book made 7.5%/yr at Sharpe 0.72.
- **Did anything survive?** Yes, three things: **trend** (Sharpe 0.61, uncorrelated),
  a weak **volatility risk premium** (0.27), and a weak **defensive/BAB** tilt (0.17).
- **What died?** Cross-sectional momentum (0.11), cross-asset value (−0.26), and — on the
  long history — the classic size, value and momentum equity factors.
- **What is the book actually worth?** A 30% allocation lifts a 60/40 from Sharpe 0.77 to
  **0.90** and nearly halves the drawdown. That is the honest product: **diversification and
  crisis insurance**, not alpha.
- **Did the sophisticated combiner help?** No. HRP was *worse* than equal weight. Simple beat
  clever.

## Chapter 7 — What I would try next (and why it is uncertain)

- ~~**Network momentum** (arXiv 2501.07135)~~ — **done, see §8.**
- ~~**Volatility risk premium done properly**~~ — **done, see §9.**
- **Cross-asset carry** (the other half of managed futures, done in `inercia`) — combining
  `cartograf`'s core with `inercia`'s trend+carry book is the obvious next experiment, since
  both point to the same lesson: the value is in the correlation, not the standalone return.

## Chapter 8 — Follow-up: network momentum (arXiv 2501.07135)

The paper's idea: markets do not trend in isolation — there is *momentum spillover*, a lead-lag
relationship where one market's trend shows up in another's a little later. So: estimate a
**directed lead-lag network** and let each market also follow the trend of the markets that tend
to *lead* it.

Implementation (reduced but faithful): from a trailing **3 years of weekly returns**, compute the
lead-lag correlation matrix `corr(r_j[t], r_i[t+1])`; each market then follows its **5 strongest
positive leaders**, weighted by that correlation. Its signal is `0.5 × own trend + 0.5 × leaders'
trend`. Same universe, same vol target, same costs, same window as §5.

| Variant | CAGR | Vol | Sharpe | Max DD |
|---|---|---|---|---|
| trend alone | 5.2% | 10.7% | 0.53 | −26.3% |
| network momentum alone | 2.3% | 10.8% | 0.26 | −37.3% |
| **trend + network (50/50)** | 6.0% | 10.5% | **0.61** | −27.4% |
| SPY (same window) | 11.4% | 18.5% | 0.68 | −55.2% |

Cleaner version: **60/40 + 30% sleeve** → Sharpe 0.95 (trend alone) vs **0.97 (trend + network)**.

**Verdict — a small, honest positive, and no more.** The network signal is weak on its own
(0.26) and highly correlated with plain trend (0.42), so blending two correlated signals buys
+0.08 Sharpe standalone and +0.02 at the portfolio level. The average lead-lag correlation kept
is 0.115 — real, but small. Nothing was tuned, so this is *suggestive, not proven*: with one
lookback, one `k`, and one blend, a +0.08 improvement in Sharpe is well inside the noise.

## Chapter 9 — Follow-up: the volatility risk premium, done properly

§5 used SVXY, a crude proxy. Done properly: the premium is **implied variance minus subsequently
realized variance**, from CBOE's own indices (VIX = 30-day implied, VIX3M = 3-month implied) and
SPY realized vol. The tradable sleeve is the standard variance-swap P&L per unit of vega,
`(K² − RV²) / (2K)`, in vol points.

**The premium is real** (2003–2026, 200 months):

| | |
|---|---|
| mean implied vol | 19.0 |
| mean realized vol | 15.6 |
| mean P&L | **+1.83 vol points / month** |
| months with implied > realized | **81.5%** |

So insurers of volatility are paid — most of the time. The problem is the other times.

| Sleeve | CAGR | Vol | Sharpe | Max DD | Worst month |
|---|---|---|---|---|---|
| **A. always-on** short variance | −2.6% | 22.5% | **0.05** | −64.0% | −63.5% |
| **B. contango-gated** | 9.3% | 10.7% | **0.90** | −27.0% | −27.0% |
| C. SVXY proxy (old) | 0.5% | 9.2% | 0.10 | −19.1% | −14.7% |
| SPY (same window) | 13.5% | 14.6% | 0.94 | −24.4% | −12.5% |
| 60/40 (same window) | 8.5% | 9.0% | 0.95 | −20.7% | −7.4% |

*A is measured from 2003; B, C and the benchmarks from the **common window 2009-11 → 2026-09**
(VIX3M only starts in 2009).*

Three honest lessons:

1. **Harvesting the premium blindly does not work.** Always-on short variance has a Sharpe of
   0.05: October 2008 and March 2020 hand back years of premium in one month (−63.5% worst month).
2. **Gating turns it into a real sleeve.** Trading only when the curve slopes up (VIX < VIX3M,
   64.5% of months) gives Sharpe **0.90** — flat in March 2020 and, by construction, out of the
   worst of the tail.
3. **The "proper" measurement mattered enormously.** The crude SVXY proxy scored 0.10; the actual
   variance-swap implementation scores 0.90. A bad proxy can hide a real premium.

And the portfolio effect: **60/40 + 30% gated VRP → Sharpe 1.12, max drawdown −14.4%** — the
best single addition found anywhere in this project.

**Caveats, stated plainly.** There is no 2008 test for B (the 3-month index only starts in 2009),
so its calm-crisis record is partly an artefact of the sample. It is one regime. 5 bps/month is
optimistic for a variance position. And the gate did *not* save February 2018 (−10.3%): when the
spike comes while the curve still slopes up, the protection is not there.

## Appendix — Reproducibility

    cartograf/
    ├── README.md                this book
    ├── data/raw/                prices.csv (yfinance), ff_*.csv (Ken French),
    │                            cboe_vix_term.csv (CBOE)                  [git-ignored]
    ├── src/fetch_data.py        downloads everything (free, no keys)
    ├── src/engine.py            backtest plumbing (no-lookahead, costs, HRP)
    ├── src/run.py               the five sleeves + combination + report  -> metrics.json
    ├── src/network_momentum.py  §8 lead-lag network                     -> network_metrics.json
    └── src/vrp.py               §9 the volatility risk premium          -> vrp_metrics.json
    output/                      01_equity 02_drawdown 03_corr 04_annual 05_factors
                                 06_network 07_vrp  (+ the three metrics files)

Run: `./.venv/bin/python3 src/fetch_data.py` then `./.venv/bin/python3 src/run.py`.

**Known caveats, stated plainly.** ETFs are used as futures proxies (roll yield is not
modelled; commodity carry is untested). The SVXY series embeds a leverage change in 2018. The
sample (2008–2026) is one regime and is short. No parameter was optimised, which is a strength
(no overfitting) and a weakness (no attempt to tune). And every sleeve here is a *published*
idea — if the literature is right (McLean & Pontiff 2016), the best of them is already partly
arbitraged away.

*Conventions: reason before code; state uncertainty; be reproducible; if the data says "no
edge," say so.*
