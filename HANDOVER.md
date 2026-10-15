# Handover — l'Observatori (quant-finance projects)

_Saved 2026-10-15. A structured handover of the conversation that created this folder._

## Context

- **Who.** Efren Felio (gateway owner) with **Laika** (OpenClaw agent), over webchat, on a MacBook Air (macOS). Efren is a data-science student; invests personally (semiconductors); wants to move into **quant**. He is risk-averse, works with ~EUR 50 of side-project capital, values honest/realistic results over hype, and wants Laika to *do the work*, not advise.
- **The ask.** Build "crazy" finance/quant projects autonomously, in a Desktop folder, no rush. He was deciding between a DeepSeek coding harness in VSCode vs letting OpenClaw build.
- **Where it landed.** A container `l'Observatori` ("the observatory") at `/Users/efren/Desktop/quant_finance/l'Observatori/`, holding self-contained projects. **Three are complete:** `nit_d'alba`, `augur`, `inercia`.
- **Working convention.** Each project is documented as a single readable "book" (its `README.md`): thesis -> plan -> data -> analysis -> results *and their meaning*. Plan first; reasoning before code.

## Decisions made

1. **Tooling.** Use **OpenClaw** (agentic), not the DeepSeek harness — it can research, write, run, and iterate end-to-end.
2. **Structure.** Container `l'Observatori`; each project its own subfolder, named in the same poetic vein.
3. **Documentation.** One book-file per project (**README**); explicitly **no separate journal** (Efren preferred one readable file over a chronological log).
4. **Method.** Plan first; reason before code; state uncertainty; be reproducible; report honest negatives.
5. **File-access lock.** A hard lock needs a Docker sandbox (Docker not installed) -> using **behavioral confinement** only (project folder + Laika's own workspace).
6. **Network.** Shell network enabled (`tools.exec.mode="full"`) so data pipelines run without per-command approval.
7. **Project 1 — `nit_d'alba` ("How Long Until Dawn").** Macro fragility: sovereign debt + AI valuations + oil + war, framed as "how long until the economy breaks."
8. **Project 2 — `augur` ("Can You Predict the Market?").** Honest ML stock prediction.
9. **Project 3 — `inercia` ("A Strategy That Actually Survives").** Literature-grounded momentum/trend + carry strategy.
10. **Data (free only).** FRED, World Bank, US Treasury Fiscal Data API, yfinance/Yahoo.
11. **Testing discipline.** Walk-forward / out-of-sample, transaction costs, benchmarks, reject naive optimization.

## Results at a glance

- **nit_d'alba.** US debt ~121% of GDP; *true* interest burden ~3.9% of GDP (effective rate 3.53%, ~$1.27T/yr); ~$8.5T of Treasury debt rolls over in 12 months; fragility index **1.54 (76th pct since 1970)**; combined oil+market shock -> interest burden **8.8% of GDP**; Mag-7 combined cap **$24.6T** (+601% vs S&P +251%, 10y). 15 charts.
- **augur.** Daily direction is **not** predictable (AUC ~0.50; accuracy below the majority baseline). **Volatility is** predictable (corr 0.50).
- **inercia.** Trend + carry book: standalone **Sharpe ~0.58-0.67**, correlation to SPY **0.12**, real **crisis alpha** (2008 +8.2%, 2022 +6.2%). Portfolio value: **60/40 + 30% book -> Sharpe 0.89, Max DD -21%**. Honest failures: short-term reversal (-0.52), low-vol long/short (-0.76), cross-sectional equity momentum (~0), and risk overlays (they trade return for a shallower drawdown).

## Constraints

- **Platform.** macOS; Python **3.14.5** on the gateway host, **3.9.6** on the node.
- **Data.** Free sources only; no paid providers.
- **FRED** throttles custom User-Agents -> must use the default UA.
- **Yahoo** raw HTTP 429s -> must use the `yfinance` client.
- **Stooq** is behind a JavaScript anti-bot wall.
- **Kalshi** is US-restricted (unavailable to Efren).
- **Filesystem lock** needs Docker (not installed) -> behavioral confinement only.
- **Efren.** Risk-averse, ~EUR 50 capital, honesty over hype, no rush; wants to see the reasoning, not just code.
- **Memory.** `MEMORY.md` loads only in main sessions; `USER.md` holds durable preferences.

## Open questions

- **Next step:** a fourth project, or consolidate / clean up the workspace?
- **Lock:** keep behavioral confinement, or install Docker for a hard filesystem lock?
- **Data gaps:** UCDP/SIPRI conflict data and IMF WEO general-government debt would strengthen `nit_d'alba`.
- **inercia:** is the ~0.58-0.67 standalone Sharpe plateau acceptable, or chase other edges (e.g., a volatility-risk-premium proxy)?
- **Persistence:** should these projects be put under version control (git) / published anywhere?
