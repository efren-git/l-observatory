# Relative-value lab — the literal "buy one, short the other" test

*Pre-registered 2026-10-20. Question: does a diversified, walk-forward-selected
basket of economically linked ETF pairs make money after costs? Short answer:
no. The implementation is in `src/inercia/relval.py`; the numbers are in
`output/relval_metrics.json`.*

## What was tested

- **27 fixed pairs**: sector/industry, country, bond, commodity, style and FX
  links (XLE/XOP, XLF/KRE, IEF/TLT, LQD/HYG, GLD/SLV, SPY/IWM, FXE/UUP, …).
  The list was written before the run and was not expanded afterwards.
- **Rolling hedge ratio** (252 days) and **spread z-score** (60 days), both
  lagged one day.
- **Entry** at |z| > 2.0, **exit** at |z| < 0.5, **time stop** at 60 days.
- **Quarterly selection**: a pair may trade only if, on the trailing 252 days,
  the Engle-Granger residual has ADF t < −2.86 and a half-life < 63 days.
  At most 8 pairs, ranked by ADF t, equal weight.
- **Costs**: 5 bps per leg per turn, 50 bps/year short borrow.
- **Portfolio**: 10% volatility target, 60-day estimate, shifted one day.
- **Trials**: 27 pairs. The walk-forward is one strategy, not 84 independent
  bets.

## Result

| Portfolio | CAGR | Vol | Sharpe | MaxDD | DSR (27 trials) |
|---|---:|---:|---:|---:|---:|
| Relative-value basket | **−2.1%** | 5.1% | **−0.39** | **−43.8%** | 0.0001 |
| SPY | 10.9% | 18.9% | 0.64 | −55.2% | — |
| 60/40 | 8.3% | 10.9% | 0.79 | −31.4% | — |

The realised volatility is 5.1%, below the 10% target, so the loss is not a
leverage artefact. The basket lost money with *less* risk than the target.

## Where the money went

The per-pair contributions are almost all negative or zero:

| Best contributions | CAGR contribution | Standalone Sharpe |
|---|---:|---:|
| XLV/XBI | +0.07% | −0.04 |
| ITB/XHB | +0.07% | −0.13 |
| XLY/XRT | +0.06% | −0.09 |
| EWA/EWC | +0.03% | 0.27 |

| Worst contributions | CAGR contribution | Standalone Sharpe |
|---|---:|---:|
| EWI/EWP | −0.12% | −0.35 |
| XLE/XOP | −0.12% | −0.15 |
| LQD/HYG | −0.09% | −0.45 |
| XLF/KRE | −0.08% | −0.42 |
| SHY/IEF | −0.05% | −1.36 |

The best standalone pair in the whole list (EWA/EWC, Sharpe 0.27) is not enough
to pay for the rest. Most pairs lose after costs and borrow.

## Why it fails

1. **Cointegration is unstable.** A pair that passes the ADF screen on the
   trailing 252 days often breaks in the next quarter. The screen is a
   description of the past, not a guarantee.
2. **The spread is not a risk premium.** Unlike trend or volatility selling,
   there is no economic reason the residual must revert; it can trend for
   years. The stop-loss turns a slow divergence into a realised loss.
3. **Costs and borrow dominate.** A market-neutral pair earns a few basis
   points per trade; 5 bps per leg and 50 bps/year borrow consume most of it.
   The gross edge has to be large to survive.
4. **The selection is a multiple-testing machine.** 27 pairs × 84 quarters is
   a lot of chances to find a spurious fit. The DSR is 0.0001, which is the
   honest way of saying "nothing here."
5. **ETF pairs are crowded.** This is the most accessible version of stat arb,
   and the easy version is exactly the one that gets competed away.

This is consistent with Phase 5: V/MA was the only cointegrated pair in a fixed
eight-pair screen, and its default Sharpe was 0.073; KO/PEP was negative. A
broader, walk-forward basket does not rescue the idea.

## What this means

- **Do not trade the ETF-pair basket.** It is not a small positive with a
  caveat; it is a negative after honest costs.
- **"Buy one asset, short the other" is not automatically arbitrage.** If the
  two legs have no contractual link, the spread is a directional bet on their
  difference, and it can diverge.
- **The relative-value ideas that do have an edge are contractual or
  event-driven**, not statistical: merger arbitrage (the deal spread is the
  price of completion risk), convertible arbitrage (the bond's embedded
  option), and capital-structure trades. Those need deal/bond data and legal
  work, not just prices.

## Next

1. **Merger arbitrage** — buy the target, short the acquirer in a stock deal;
   the spread is a real risk premium, and the strategy is research-intensive,
   not latency-intensive. Needs a deal dataset (SEC 8-K/DEFM14A, press
   releases) and a break-risk model.
2. **Post-earnings announcement drift** — slower than HFT, but needs earnings
   dates and surprise data; the effect has decayed in large caps.
3. **Insider buying** — SEC Form 4 is free; the anomaly is slow and
   well-documented, but parsing and survivorship are work.
4. **Risk premia** — trend, gated VRP, carry. Already built; the reliable but
   boring path.

## Reproduce

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/inercia"
./.venv/bin/python3 src/run_relval.py
```

Outputs: `output/relval_metrics.json`, `output/15_relval.png`.
