# cartograf — "How Much of the Literature Actually Survives?"

*A readable walkthrough of everything in this project: what it asks, why, how the data
works, and what the results mean.*

Project #4 of l'Observatori. Status: **refactored and re-audited 2026-10-19; corrected 2026-10-20** — five published return
patterns tested on free data, walk-forward, net of costs, plus an equity-factor cross-check, plus
three follow-ups: **network momentum** (§8), a **proper volatility-risk-premium** test (§9) and
**cross-asset carry** (§10).

> **2026-10-20 correction.** The numbers in Chapters 5–10 are the pre-fix run. A month-end
> alignment bug in the VRP/core series and a turnover-denominator bug were fixed. Corrected
> headline: gated VRP Sharpe **0.90 → 1.18**; core (trend+BAB+VRP) **0.66 → 0.85**; 60/40+30%
> core overlay **1.24** monthly / **1.26** daily, DSR **0.985**; BAB **0.10 → −0.08** after requiring a full beta
> window. Full before/after tables and caveats: `AUDIT-2026-10-20.md`. Treat the body tables as
> the historical record, not the current numbers.

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
| trend | 6.8% | 12.1% | **0.61** | −22.0% | 0.04 | 17.4× |
| xsmom | 0.6% | 10.8% | 0.11 | −40.2% | 0.16 | 8.9× |
| value | −2.1% | 9.5% | **−0.18** | −55.8% | −0.07 | 5.1× |
| bab | 0.5% | 12.1% | 0.10 | −38.4% | −0.05 | 3.6× |
| vrp | 2.5% | 11.2% | 0.28 | −43.0% | 0.36 | 0.6× |

Three of the five are **weak or negative**. Cross-sectional momentum barely clears zero;
cross-asset value actually *loses* money; betting-against-beta is a shadow of its published
self. Only trend is clearly real — and even it is not a return-maximiser (SPY made 11.3% a
year against trend's 6.8%).

The BAB row is the one that moved in this audit. Before the live-name mask, 95–97% of its
2008–2010 score came from ETFs that had not listed yet: the zero-filled return panel made
them look riskless. Masked, the sleeve is weaker (0.10) and now negatively correlated with
SPY. See AUDIT §5.

Book-construction note: a sleeve that is not live yet (SVXY before 2011; BAB's style ETFs
before their listings) is held **flat at zero return**, not backfilled with another sleeve.
That is the conservative choice, and it is why the 2008–2011 books look diluted.

But look at the last two columns. Trend is essentially **uncorrelated with stocks (0.04)**,
and value is **negatively** correlated with almost everything (−0.38 to xsmom, −0.26 to trend
and vrp). A sleeve can be a bad standalone strategy and a good portfolio ingredient. That is
the whole game.

### 5.2 Combining them — and a nice negative

| Book | CAGR | Vol | Sharpe | Max DD | corr to SPY |
|---|---|---|---|---|---|
| equal-weight (all 5) | 5.9% | 11.0% | 0.58 | −30.1% | 0.20 |
| inverse-vol | 5.6% | 10.8% | 0.56 | −29.1% | 0.23 |
| **HRP** | 3.2% | 11.1% | **0.34** | −44.2% | 0.21 |
| **core: trend+bab+vrp** | 6.2% | 10.9% | **0.61** | −20.3% | 0.19 |

Two honest lessons:

- **HRP lost to naive equal weight** (0.34 vs 0.58). HRP is a *risk* allocator and blind to
  expected return; in 2020 it had loaded ~29% on the losing value sleeve and paid for it
  badly that year. With only five sleeves and a 36-month window, the elegant method is worse
  than the dumb one. (This is Harvey–Liu–Zhu in miniature: sophistication is not edge.)
- **Dropping the two failures helped relative to equal weight, not versus SPY.** The core
  book of the three survivors — trend, bab, vrp — scores Sharpe **0.61**, above equal weight
  (0.58) and with a much smaller drawdown (−20%), but essentially at SPY's 0.64. The
  proper-VRP version in §9 is 0.66. There is no standalone alpha claim left here.

### 5.3 The point: what the book is for

| Portfolio | CAGR | Vol | Sharpe | Sortino | Max DD |
|---|---|---|---|---|---|
| SPY | 11.3% | 19.7% | 0.64 | 0.78 | −51.9% |
| 60/40 | 8.4% | 11.4% | 0.77 | 0.97 | −30.8% |
| 60/40 + 30% equal book | 7.9% | 9.2% | 0.87 | 1.09 | −18.6% |
| **60/40 + 30% core book** | 8.0% | 9.2% | **0.88** | **1.10** | −18.9% |

Adding a 30% sleeve of the core book turns a 0.77-Sharpe, −31%-drawdown 60/40 into a
**0.88-Sharpe, −19%-drawdown** portfolio, giving up 0.4 points of CAGR (8.0% vs 8.4%).

That is the honest, defensible claim. It is not "beat the S&P 500". It is "improve the
risk-adjusted return of a normal portfolio", which is a much lower and much more honest bar.

### 5.4 Crisis behaviour

Annual returns of the equal-weight book vs SPY:

| Year | SPY | book |
|---|---|---|
| 2008 | −36.8% | **+10.9%** |
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
  the best daily book (core with the SVXY proxy) made 6.2%/yr at Sharpe 0.61, and the
  proper-VRP core in §9 made 6.6%/yr at 0.66 on a shorter sample.
- **Did anything survive?** Yes, three things: **trend** (Sharpe 0.61, uncorrelated),
  a weak **volatility risk premium** (0.28), and a weak **defensive/BAB** tilt (0.10,
  weaker still once phantom pre-listing names are removed).
- **What died?** Cross-sectional momentum (0.11), cross-asset value (−0.18), and — on the
  long history — the classic size, value and momentum equity factors.
- **What is the book actually worth?** A 30% allocation lifts a 60/40 from Sharpe 0.77 to
  **0.88** and nearly halves the drawdown; the gated-VRP overlay in §9 reaches **1.12**.
  That is the honest product: **diversification and crisis insurance**, not alpha.
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
| trend alone | 6.7% | 12.1% | 0.60 | −26.3% |
| network momentum alone | 2.9% | 12.2% | 0.29 | −37.3% |
| **trend + network (50/50)** | 7.7% | 11.8% | **0.69** | −27.4% |
| SPY (same window) | 11.8% | 19.7% | 0.67 | −51.5% |

Cleaner version: **60/40 + 30% sleeve** → Sharpe 0.94 (trend alone) vs **0.97 (trend + network)**.

**Verdict — a small, honest positive, and no more.** The network signal is weak on its own
(0.29) and highly correlated with plain trend (0.42), so blending two correlated signals buys
+0.09 Sharpe standalone and +0.03 at the portfolio level. The average lead-lag correlation kept
is 0.115 — real, but small. Nothing was tuned, so this is *suggestive, not proven*: with one
lookback, one `k`, and one blend, a +0.09 improvement in Sharpe is well inside the noise.

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
| **A. always-on** short variance | −3.0% | 24.0% | **0.05** | −64.0% | −63.5% |
| **B. contango-gated** | 9.3% | 10.7% | **0.90** | −27.0% | −27.0% |
| C. SVXY proxy (old) | 0.5% | 9.2% | 0.10 | −19.1% | −14.7% |
| SPY (same window) | 13.5% | 14.6% | 0.94 | −24.4% | −12.5% |
| 60/40 (same window) | 8.5% | 9.0% | 0.95 | −20.7% | −7.4% |

*A starts after its 24-month vol warm-up (2005); B, C and the benchmarks from the **common window 2009-11 → 2026-09**
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

## Chapter 10 — Follow-up: cross-asset carry, done properly

Carry (Koijen, Moskowitz, Pedersen & Vrugt 2018) is *the return to an asset if its price does not
change* — the interest you earn, the dividend you collect, the yield above cash. It is one of the
three pillars of managed futures, alongside momentum and value, so it deserves a proper test.

Three asset classes, each ranked **cross-sectionally** (long the highest carry, short the lowest),
monthly, vol-targeted, net of 5 bps:

| Class | Carry measured as | Data |
|---|---|---|
| bonds | Treasury yield at the ETF's tenor **minus** 3-month cash | FRED curve (SHY→2y, IEF→7y, TLT→30y) |
| equities | trailing-12m dividend yield **minus** 3-month cash | Yahoo dividend history (14 ETFs) |
| FX | foreign 3-month rate **minus** US 3-month rate | FRED G10 interbank rates (EUR/JPY/GBP/AUD/CAD/CHF) |

**Commodity carry is not tested.** It needs futures curves — the roll yield is the carry — and
those are not free. Saying so is the honest option; a bad proxy would be worse than nothing.

Results (2007-01 → 2026-10, the window where all three classes are live):

| Book | CAGR | Vol | Sharpe | Max DD | Worst year |
|---|---|---|---|---|---|
| bond carry | 2.4% | 9.8% | **0.29** | −23.5% | −11.9% |
| equity carry | −6.0% | 10.2% | **−0.56** | −78.0% | −23.6% |
| FX carry | 2.7% | 10.1% | 0.32 | −31.8% | −21.5% |
| **carry book (all three)** | 0.3% | 10.5% | **0.08** | −37.3% | −20.9% |
| SPY | 11.0% | 19.5% | 0.63 | −55.2% | −36.8% |
| 60/40 | 8.4% | 11.2% | 0.77 | −31.4% | −16.7% |

**Verdict — it does not survive here, and the reasons are informative.**

- **Equity carry is a disguised value bet, and value died.** Long high-dividend, short low-dividend
  meant long value/REITs and short growth — the single worst trade of 2007–2026. Sharpe −0.56.
- **FX carry only looks alive after the fix (0.32).** The old code subtracted the US rate but never
  added the foreign one, so it was measuring spot, not carry; FXE tracks spot to 2.6 bp/month.
  Crediting the foreign deposit rate turns 0.01 into 0.32 — but with a −32% drawdown (2008 and
  2015) and no useful correlation to the rest. It is a measurement repair, not a new edge.
- The combined book is **uncorrelated with equities (−0.02)** and now slightly positive (0.08),
  but that is not enough: adding 20–30% of it to a 60/40 still *lowers* the Sharpe
  (0.77 → 0.76 → 0.74). Uncorrelated and barely positive is not diversifying; it is just a
  second, weaker way to be long risk.

**The honest conclusion.** On free data, over this window, with these instruments, the classic
carry factor does not deliver. Three caveats matter: this uses spot ETFs rather than futures (the
proper instrument for carry); commodities — historically a third of managed-futures carry — are
untested; and one 19-year window is one observation. But the failure of the equity leg is not a
technicality: it is the same momentum/value decay that killed the factors in §5.5, showing up
again under a different name.

## Appendix — Reproducibility

    cartograf/
    ├── README.md                this book
    ├── data/raw/                prices.csv (yfinance), ff_*.csv (Ken French),
    │                            cboe_vix_term.csv (CBOE)                  [git-ignored]
    ├── src/fetch_data.py        downloads everything (free, no keys)
    ├── src/engine.py            backtest plumbing (no-lookahead, costs, HRP)
    ├── src/run.py               the five sleeves + combination + report  -> metrics.json
    ├── src/network_momentum.py  §8 lead-lag network                     -> network_metrics.json
    ├── src/vrp.py               §9 the volatility risk premium          -> vrp_metrics.json
    └── src/carry.py             §10 cross-asset carry                   -> carry_metrics.json
    output/                      01_equity 02_drawdown 03_corr 04_annual 05_factors
                                 06_network 07_vrp 08_carry  (+ the metrics files)

Run: `./.venv/bin/python3 src/fetch_data.py` then `./.venv/bin/python3 src/run.py`.

**Known caveats, stated plainly.** ETFs are used as futures proxies (roll yield is not
modelled; commodity carry is untested). The SVXY series embeds a leverage change in 2018. The
sample (2008–2026) is one regime and is short. No parameter was optimised, which is a strength
(no overfitting) and a weakness (no attempt to tune). And every sleeve here is a *published*
idea — if the literature is right (McLean & Pontiff 2016), the best of them is already partly
arbitraged away.

*Conventions: reason before code; state uncertainty; be reproducible; if the data says "no
edge," say so.*
