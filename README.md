# l'Observatori

> Catalan: "the observatory." A laboratory of finance and quantitative research.

This folder holds every project Laika builds. Each project lives in its own subfolder, named in the same poetic spirit — a night before dawn, watched until it breaks into light.

## Projects

| Project | Folder | Status |
|---|---|---|
| How Long Until Dawn | nit_d'alba/ | Complete — macro fragility engine |
| Can You Predict the Market? | augur/ | Complete — ML, honest verdict |
| A Strategy That Actually Survives | inercia/ | Complete — refactored 2026-10-19; corrected 2026-10-20 |
| How Much of the Literature Actually Survives? | cartograf/ | Complete — 5 edges + network momentum + proper VRP; corrected 2026-10-20 |

> **2026-10-20 correction.** Both books were re-run after fixing a turnover
> denominator and a month-end alignment bug. The corrected headline and the
> before/after tables are in `HANDOVER-2026-10-20.md`,
> `cartograf/AUDIT-2026-10-20.md` and `inercia/AUDIT-2026-10-20.md`. The body
> chapters remain the historical record.
>
> **Phase 3 is complete.** The cross-project book is `inercia/PHASE3.md`; on
> Window B (2009-11+) a 30% allocation lifts the 60/40 from 1.10 to 1.18–1.23
> Sharpe and cuts the drawdown to about −15%. Window A (legacy SVXY) only cuts
> the drawdown. Standalone, the book does not beat the 60/40.

## How work is done here

Every project is documented as a single readable book — never a code dump, never a separate log. Each project has one README that explains everything in order:

- what the project asks and why (thesis)
- how it will be answered (plan)
- every dataset, what it measures, and why it matters (data)
- what was done, what it found, and what it means (analysis + results)

Code is written last, and only after the reasoning and the meaning are recorded.

## Naming

- **l'Observatori** — the container, "the observatory."
- **nit_d'alba** — project #1, "the night before dawn."
