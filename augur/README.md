# augur — "Can You Predict the Market?"

*A readable walkthrough of everything in this project: what it is, why it exists, how the data works, and what the results mean.*

Project #2 of l'Observatori. Status: **complete (first pass, 2026-10-15)**.

## How to read this book

One file, written to be read front to back. Every dataset and result is explained in plain language — the *why* and the *meaning*, not just the code. Charts live in `output/`.

## Chapter 1 — The thesis

Predicting stock prices is the most common — and most misguided — machine-learning finance project. The naive version ("an LSTM that predicts tomorrow's price") is everywhere, and it is almost always wrong, for three reasons: it leaks the future, it predicts *price levels* (which just drift upward and look impressive on a chart), and it never benchmarks against the trivial answer.

This project does it honestly. The question is not "can a model draw a smart-looking price line?" but: **can anything predict next-period returns out-of-sample, better than the dumb baseline?** The expected, defensible answer is that daily direction is near-random — but *some* things are genuinely predictable: **volatility clusters** (calm follows calm, storms follow storms), and possibly medium-term momentum. Proving *what is and isn't predictable* is the deliverable — not a fake accuracy score.

## Chapter 2 — The plan

### Research questions

1. Can we predict the **sign** of the next day's return better than chance, **out-of-sample**?
2. Which features carry any signal — technical, macro, cross-asset?
3. Is **volatility** predictable even where direction is not?
4. Does a signal-based strategy beat **buy-and-hold** on a risk-adjusted basis?

### Methodology

- **Data:** daily prices (yfinance) plus macro series (FRED, reused from nit d'alba).
- **Features:** lagged returns, realized volatility, moving averages, momentum, RSI, VIX, 10-year yield, oil.
- **Target:** next-day return sign (classification) and return (regression).
- **Models:** logistic regression, random forest / gradient boosting.
- **Validation:** **walk-forward**, strictly out-of-sample, no lookahead — the only honest way.
- **Benchmarks:** coin flip (50%), always-long, buy-and-hold.

### Milestones

0. Setup & documentation — *in progress*
1. Data + feature engineering
2. Baselines + models
3. Walk-forward evaluation
4. Honest verdict
5. Report + charts

## Chapter 3 — The data

### 3.1 yfinance — prices
Daily open/high/low/close/volume for a basket of liquid names and indices (the tool proven in nit d'alba — the reliable free route to Yahoo). *Status: to fetch.*

### 3.2 FRED — macro features
Reused from nit d'alba: 10-year yield, VIX, oil, inflation. These give the model context beyond price history. *Status: to fetch.*

## Chapter 4 — The analysis

### 4.1 The setup (no lookahead)

We predict the sign of the **next** day's SPY return from features known **today**. Validation is **walk-forward**: train on everything up to day t, predict the next 63 days, roll forward, retrain each quarter. That gives **2,640 strictly out-of-sample days (2016–2026)** — the only honest way to test a trading model.

Features: six lagged returns; realized volatility (5/10/20d); momentum (5/10/20d); the gap to the 20/50/200-day moving averages; RSI(14); and macro context (10-year yield + its change, VIX + its change, oil return).

### 4.2 Direction is not predictable

Chart `02_accuracy.png`.

| Model | Out-of-sample accuracy | AUC |
|---|---|---|
| Majority baseline (always "up") | **55.1%** | — |
| Logistic regression | 54.5% | 0.499 |
| Gradient boosting | 54.9% | 0.515 |

Both models land **below the dumb baseline**, and the AUC — the model's ability to rank up-days above down-days — is **~0.50, i.e. a coin flip**. The models learned nothing about direction that survives out-of-sample. The AUC near 0.5 is the killer statistic: it says the signal is indistinguishable from noise.

### 4.3 And the strategy does not beat buy-and-hold

Chart `01_strategy_vs_bh.png`. The long/flat strategy guided by the model returned **232%** out-of-sample versus buy-and-hold's **238%**. Its Sharpe (0.95) edges buy-and-hold's (0.89) — but that comes from *being out of the market* on some days (lower volatility), not from picking winners. The return is lower and the Sharpe edge is inside the noise.

### 4.4 But volatility IS predictable

The one genuine, stable signal: 20-day realized volatility correlates **0.50** with the next day's absolute return. Calm follows calm; storms follow storms. This is **volatility clustering** — and unlike direction, it is real, persistent, and tradeable (vol-targeting, options, risk management).

## Chapter 5 — Verdict

- **Can you predict direction?** No — AUC ~0.50, accuracy below the baseline.
- **Which features carry signal?** None for direction; the technical and macro features all failed to predict the sign.
- **Is volatility predictable?** Yes — a 0.50 correlation, stable across the sample.
- **Does it beat buy-and-hold?** No. It matches at best.

The honest answer to "Can You Predict the Market?": you can predict its **temperature** (volatility), not its **direction**. Anyone claiming a directional model with high accuracy is either leaking the future or predicting the wrong thing.

## Chapter 6 — Conclusions

**What holds.** (1) Daily direction is ~unpredictable from standard features. (2) Any directional "edge" found here is noise. (3) Volatility is genuinely predictable. (4) Benchmarks are essential — without the majority baseline, 54.9% accuracy would look like a win.

**What this does not show.** It does not prove markets are perfectly efficient — other features, horizons, or cross-sectional methods might work. It does not test intraday or alternative data. And the backtest ignores transaction costs, which would make the strategy *worse*, not better.

**The real lesson.** The value of an ML-finance project is the *honesty of its evaluation*, not the accuracy number. A leaked, benchmark-free model can show 90% "accuracy" and be worthless.

---

## Appendix — Reproducibility

    augur/
    ├── README.md     this book
    ├── data/raw/     price + macro data
    ├── src/          fetch, features, models, evaluation
    └── output/       charts, metrics

*Conventions: reason before code; state uncertainty; be reproducible; if the data says "no edge," say so.*
