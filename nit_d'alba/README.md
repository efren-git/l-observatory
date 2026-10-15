# nit d'alba — "How Long Until Dawn"

*A readable walkthrough of everything in this project: what it is, why it exists, how the data works, and what the results mean.*

Project #1 of l'Observatori. Status: **first full pass complete (2026-10-14)**.

## How to read this book

This single file is the project's book. It is written to be read front to back, not skimmed. Every dataset and result is explained in plain language — the *why* and the *meaning*, not just the code. Charts referenced here live in `output/`.

- **Chapter 1 — Thesis**: what the project asks and why.
- **Chapter 2 — The plan**: the research questions and how they were answered.
- **Chapter 3 — The data**: every dataset, what it measures, why it matters, how it was obtained.
- **Chapter 4 — The analysis**: each module — what was done, what it found, what it means.
- **Chapter 5 — Synthesis**: the fragility index and stress tests.
- **Chapter 6 — Conclusions**: what is defensible and what is not.
- **Appendix — Reproducibility**: the file layout and how to re-run everything.

---

## Chapter 1 — The thesis

The question is not "is the economy overvalued?" — everyone asks that. The question is: **how much runway is left, and what specifically would break it?**

The global economy is running on three simultaneous, historically rare stresses:

1. **Sovereign debt** at peacetime-record levels, with refinancing needs colliding against structurally higher rates.
2. **An AI-driven valuation cycle** that has concentrated market wealth into a handful of firms.
3. **Geopolitical / energy shocks** (war, oil) that transmit straight into the two above: inflation, then rates, then debt-service strain.

The hard, interesting part is the *interaction*: when does a shock to one (oil, war, a repricing) cascade into a break in another (debt service, refinancing), and roughly how much time does the system have? That "distance to break" is what this project estimates — honestly, reproducibly, with uncertainty stated out loud.

## Chapter 2 — The plan

### The five research questions

1. **Debt-service stress.** When does (debt × effective interest rate) / GDP cross the point where interest crowds out everything else?
2. **The refinancing cliff.** How much sovereign debt matures soon, and can it roll over at today's rates?
3. **Oil-shock transmission.** What is the historical lag from an oil spike to inflation to policy to stress?
4. **AI-valuation fragility.** How concentrated is the market, and what rides on it?
5. **War / conflict.** Conflict to supply chains, oil, and fiscal spending, with historical base rates.

### Methodology

Collect from free primary sources -> one reproducible pipeline -> compute stress metrics -> synthesize into a fragility index + scenario stress test -> write a defensible thesis.

### Milestones

0. Setup & documentation — **done**
1. Data sourcing + dictionaries — **done**
2. Debt-service stress — **done**
3. Refinancing cliff — **done** (maturity ladder reconstructed from Treasury auction data: ~$8.5T rolls over in 12 months)
4. Oil-shock transmission — **done**
5. AI-valuation fragility — **partial (index-level; market data rate-limited)**
6. War / conflict — **done (event study)**
7. Synthesis: fragility index + scenarios — **done**
8. Output: charts + written report — **done (this book + output/)**

## Chapter 3 — The data

Every dataset used is a primary, citable institution. No scraped or paywalled data.

### 3.1 FRED — rates, inflation, oil, debt (St. Louis Fed) — VALIDATED
Long, clean US series. **What I pulled:** 10Y Treasury (DGS10), fed funds (FEDFUNDS), CPI (CPIAUCSL), WTI (DCOILWTICO), Brent (DCOILBRENTEU), long WTI history (WTISPLC), federal debt (GFDEBTN), nominal GDP (GDP), 10Y breakeven inflation (T10YIE), S&P 500 (SP500), Nasdaq Composite (NASDAQCOM), unemployment (UNRATE), US recession indicator (USREC), VIX (VIXCLS), jobless claims (ICSA), USD/EUR (DEXUSEU). **Access:** fredgraph.csv, no key. (Note: FRED's CDN throttles custom User-Agents — the default works.)

### 3.2 World Bank — cross-country debt & energy — VALIDATED
**What I pulled:** central government debt % GDP, fuel imports % of merchandise imports, GDP (US$ and growth), for 14 economies. **Access:** free REST API, no key. (Caveat: the central-government-debt series has uneven country coverage and lags — general-government figures from the IMF would be better.)

### 3.3 Market data (individual AI names) — VALIDATED (via yfinance)
Stooq is now behind a JavaScript anti-bot wall, and raw Yahoo requests get rate-limited (HTTP 429), but the **yfinance** Python client — which manages Yahoo sessions and cookies properly — works reliably. **What I pulled:** 10 years of monthly prices for the Mag-7 and the S&P 500 / Nasdaq indices, plus current market caps and trailing P/Es.

### 3.4 IMF WEO — NOT USED
The IMF's general-government debt and interest-expenditure data would materially improve questions 1-2, but its bulk download URL changes per release; deferred to a later pass. World Bank debt data is the stand-in.

### 3.5 UCDP / SIPRI — NOT FETCHED (event study instead)
UCDP's bulk download URLs returned 404 and require a moving target. Instead, the war module uses a **curated event list** of major conflicts crossed with the long WTI series — a defensible event study that needs no bulk conflict data.

### 3.6 US Treasury Fiscal Data — VALIDATED (added mid-project)
The single best free source we found: the US Treasury's Fiscal Data API (fiscaldata.treasury.gov), no key required. **What I pulled:** average interest rates on Treasury securities (the *effective* rate on the debt), debt to the penny (exact debt, daily), interest expense (actual dollars of interest paid), and securities outstanding by type. This replaced the 10-year-yield **proxy** for the interest burden with the **actual** figure — a material accuracy gain (see 4.1).

---

## Chapter 4 — The analysis

### 4.1 Debt-service stress — the core of the thesis

Chart `01_debt_to_gdp.png`. US federal debt reached **121% of GDP** in 2026 — the highest since the WWII peak. The path: ~35% in the early 1970s, a grind upward through the 1980s-90s, acceleration after 2008, and a sharp step in 2020. Relative to the economy, the debt has more than tripled.

Charts `02_interest_burden.png` and `11_true_interest_burden.png`. The stress is not the *level* of debt — it is the *cost of carrying it*. Two numbers matter, and they differ:

- **The actual burden today: ~3.9% of GDP** (Treasury data: ~$1.27 trillion of annual interest). The effective rate on the outstanding debt is **3.53%** — far below the 5.21% market yield, because the debt's average maturity is ~6 years and much of it was issued when rates were low.
- **The steady-state burden: ~6.3% of GDP** — what the burden becomes if the whole stock paid the current 10-year yield.

The gap between them is the **rollover drift**: every month, maturing low-rate debt is refinanced at today's higher rates, mechanically pushing the effective rate — and the burden — up, *with no new shock needed*. In 1980 the burden came from ~15% rates on a small debt; today it comes from a large debt drifting toward 5%+.

**Meaning.** The system tolerates today's burden, but its *sensitivity to rates* is now much higher, because the stock is so large. Real yields (chart `05_real_yield.png`) are back to ~2.9%, the highest in over a decade. This is why the scenarios below matter more than the level.

### 4.2 The refinancing cliff — now measured

Chart `15_maturity_ladder.png`. Reconstructing the maturity profile from every outstanding Treasury security (via the Treasury's auction data — `auctions_query`, deduped by CUSIP), **roughly $8.5 trillion of Treasury debt matures within the next 12 months** and must be rolled over. The ladder then falls off: ~$5.4T in 2027, ~$3.4T in 2028, declining out into the 2050s.

**Meaning.** This is the mechanical engine of the debt problem: ~$8T/year must be refinanced — and it refinances at *today's* ~5.2% market rates rather than the ~3.5% average on the existing stock. That is the **rollover drift** made concrete: the interest burden rises with no new borrowing and no new shock. The binding question is not whether the debt is "sustainable" in the abstract, but whether ~$8T/year keeps rolling at tolerable rates. (Caveat: this is reconstructed from auction records, ~$26T of the ~$30T marketable stock; directionally solid, not exact.)

### 4.3 Oil-shock transmission

Chart `04_oil_vs_inflation.png`. The episode structure is clear: the 1973-74 and 1979-80 oil shocks preceded the great inflation, and 2008 and 2022 repeated the pattern. The channel is: **oil spike -> CPI -> central bank -> rates -> debt service.** The 2020 collapse (-280% YoY, a pandemic artifact) is a reminder that the channel cuts both ways.

**Meaning.** Oil is the *fastest* channel from geopolitics to the debt problem. WTI at **$96** today means a further spike is a direct hit to headline inflation, and therefore to the rate path that sets the debt burden.

### 4.4 AI-valuation fragility — with individual names

Charts `12_mag7_vs_sp.png`, `13_mag7_pe.png`, `10_tech_concentration.png`. Using **yfinance** (the standard Python client — the earlier failures were raw-request rate-limiting, not a data shortage), the individual names are now in:

- The **Mag-7 combined market cap is $24.6 trillion**.
- Over 10 years the Mag-7 (equal-weighted) returned **+601%** versus the S&P 500's **+251%** — the AI trade out-ran the market by ~2.4×.
- **Valuation dispersion is extreme**: trailing P/Es run from **GOOGL ~17** to **AAPL ~39**, with **TSLA at ~340** — an outlier showing how much of the "AI trade" is narrative rather than earnings.

The structural fragility is *concentration plus dispersion*: a large share of index wealth sits in a handful of names, several priced for perfection, one absurdly so. The channel is a *wealth effect*: a repricing hits household and retirement wealth, consumption, and GDP — exactly the "AI correction" scenario in Chapter 5.

### 4.5 War and conflict — the oil connection

Chart `09_war_oil.png` and the event study. Wars are followed by oil spikes — but **inconsistently**:

| Event | Oil at event | +6 months | Change |
|---|---|---|---|
| 1973 Yom Kippur / embargo | 4.3 | 10.1 | **+134.6%** |
| 1979 Iranian Revolution | 14.8 | 19.1 | +28.6% |
| 1980 Iran-Iraq War | 38.0 | 38.0 | 0.0% |
| 1990 Gulf War | 18.6 | 25.0 | +33.9% |
| 2003 Iraq War | 35.9 | 31.6 | -11.9% |
| 2011 Arab Spring | 89.4 | 97.2 | +8.7% |
| 2022 Russia invades Ukraine | 83.2 | 101.6 | +22.1% |
| 2023 Israel-Hamas War | 89.4 | 81.3 | -9.1% |

**Meaning.** Average +26% over six months, but the dispersion is larger than the mean. "War -> oil -> inflation" is real but not mechanical: markets price *expected supply disruption*, which is why some wars barely move oil and others (an embargo) move it enormously.

## Chapter 5 — Synthesis: the fragility index and stress tests

### 5.1 The index

Chart `07_fragility_index.png`. The **fragility index** is the equal-weighted mean of five z-scored stress components: **debt/GDP, interest burden, real 10Y yield, oil price, and VIX**. It answers one question: *how stretched is the system today versus its own history?*

**Current reading: 1.54 standard deviations — the 76th percentile since 1970.**

### 5.2 How to read it

We are in the **top quarter** of historical fragility, and close to its record. The index peaked in **2008 (~1.67**, driven by the VIX spike and the debt jump); today's **1.54** is close behind — but the *composition differs*. Today the index is pushed up by the **debt stock and interest burden**; in 2008 it was market panic (VIX). Earlier peaks (the early 1980s) were lower. So the index says: fragile, and the danger is now structural, not acute.

### 5.3 Scenario stress test

Chart `08_scenarios.png`. What the debt-service burden becomes under shocks (baseline: debt 121% of GDP, 10Y at 5.21%):

| Scenario | Debt/GDP | 10Y | Interest burden (% GDP) |
|---|---|---|---|
| Baseline (today) | 121.2% | 5.21% | **6.31%** |
| War / oil shock (10Y +1.5pp) | 121.2% | 6.71% | **8.13%** |
| AI correction (GDP -3%, debt +5%) | 131.2% | 5.21% | **6.83%** |
| **Combined shock** | 131.2% | 6.71% | **8.80%** |

**Meaning.** A combined shock pushes debt service to **~8.8% of GDP** — historically the zone where fiscal crises begin to bite, because interest starts crowding out everything else. Note the two anchors: the **actual** burden today is ~3.9% of GDP, while the **full-rollover steady state** at today's rates is already ~6.3%. The scenarios are steady-state figures — i.e. where the burden is *headed* even before any shock, thanks to the rollover drift. That is the project's central quantitative claim.

## Chapter 6 — Conclusions

**What holds.**
1. US debt/GDP is at a record (~121%), and the debt *stock* — not the rate — is the new systemic risk.
2. The interest burden is high and steeply rate-sensitive: a 1.5-point rate shock adds ~1.8 points of GDP to it.
3. Oil and geopolitics transmit to inflation and rates — the fastest channel into the debt problem.
4. Composite fragility is elevated (76th percentile since 1970): fragile, but not unprecedented.

**What does not hold (yet).**
1. There is **no precise "break date."** Fragility is not a timer; the trigger is a shock, not the calendar.
2. The **refinancing cliff** needs maturity data we did not obtain.
3. The index is a **heuristic** (equal-weighted z-scores), not a fitted predictive model.
4. **Market-concentration** data is index-level only; individual names are a gap.

**The honest answer to "how long until dawn":** the system is fragile enough that a combined oil-and-market shock pushes debt service to ~9% of GDP — historically the zone where things break. But the timing is set by shocks, which are not forecastable here. What *is* measurable is the *exposure* — and the exposure is high, and rising.

---

## Appendix — Reproducibility

    nit_d'alba/
    ├── README.md          this book
    ├── src/
    │   ├── fetch_data.py   FRED + World Bank download
    │   ├── fetch_market.py market data (Yahoo, throttled)
    │   ├── analyze.py      core metric charts
    │   ├── synthesis.py    fragility index + scenarios
    │   └── war_study.py    conflict/oil event study
    ├── data/raw/          fred/, worldbank/, yahoo/
    ├── output/            charts + summary.json, synthesis.json, war_study.json
    ├── research/          data notes
    └── notebooks/         exploratory

Re-run: create a venv, install pandas/numpy/matplotlib/requests/openpyxl, then run the scripts in `src/` in order.

*Conventions: reason before code; state uncertainty; be reproducible; if the data says "no clear answer," say so.*
