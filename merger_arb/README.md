# Merger arbitrage — deal tracker

*Buy the target, short the acquirer. The spread is the price of completion
risk. This is a live/paper tool, not a historical backtest.*

## Why no backtest

A credible merger-arb backtest needs three things: the target's price around the
announcement, the deal terms (cash, exchange ratio, expected close), and the
target's price through close or break. Free Yahoo data **drops delisted
targets** — HES, PXD, DFS, ATVI, XLNX, SPLK, MRO and ANSS all return 404 — so
the historical sample is exactly the set of deals that no longer exist. A
backtest built from the survivors would be a lie.

The honest options are (a) a paid M&A database (SDC, Capital IQ, Dealogic), or
(b) a manually curated deal set from SEC filings. This tool is the part that can
be built now and used live: the schema, the spread math, the break-risk
scorecard and an append-only paper ledger.

## Mechanics

| Structure | Position | Deal value per target share |
|---|---|---|
| Cash | Buy target; hold T-bills | `cash_per_share` |
| Stock | Buy target; short acquirer | `exchange_ratio × acquirer_price` |
| Mixed | Buy target; short acquirer | `cash + exchange_ratio × acquirer_price` |

The target usually trades below the deal value. The gap is the gross spread:
the return if the deal closes. Annualised, it is compensation for the risk that
it does not close.

**A stock deal is not a pure arbitrage.** You are long the target and short the
acquirer; the spread can move with the acquirer's price, the deal's probability,
and the market's risk appetite. A break can cost the entire spread plus the
target's fall back to its pre-announcement price.

## The risks that matter

- **Regulatory**: antitrust, CFIUS, sector regulators. Horizontal overlaps and
  long reviews are the usual killers.
- **Financing**: committed financing, cash on hand, debt covenants.
- **Shareholder vote**: required for stock deals; activist opposition.
- **Material adverse change (MAC)**: the escape hatch; read the definition.
- **Timing**: long-stop date, ticking fees, outside dates; a long delay lowers
  the annualised return.
- **Correlation**: deals break together in crises. A basket of 10 is not 10
  independent bets.

## Entry rules (pre-registered)

A deal is a candidate only if all of these hold:

1. annualised gross spread **≥ 8%**;
2. break downside **≥ −20%** (pre-announcement price vs current target price);
3. risk points **≤ 12** (four categories, 1 low to 5 high);
4. status is **pending**;
5. both target and acquirer prices are available.

Position size:

```
position_pct = min(10%, 1% risk budget / |break downside|)
```

So a −10% break gets 10%; a −20% break gets 5%; never more than 10% in one
deal. Gross exposure across all deals is capped at 40%. Hold 10–20 deals; do not
concentrate in one regulator or one sector.

Exit: at close, at the long-stop date, if the annualised spread falls below
~2%, or if the risk score deteriorates (a second request, a financing hole, a
proxy fight).

## The deal file

`deals.csv` columns:

```
deal_id,target,acquirer,structure,cash_per_share,exchange_ratio,
announce_date,expected_close,status,pre_announce_price,
regulatory_risk,financing_risk,shareholder_risk,timing_risk,notes
```

- `structure`: `cash`, `stock` or `mixed`.
- `cash_per_share`: cash component; 0 for a pure stock deal.
- `exchange_ratio`: acquirer shares per target share; 0 for a cash deal.
- `pre_announce_price`: the target's last close before the announcement; this
  is the break-downside anchor.
- Risk fields: 1 = low, 5 = high.
- `status`: `pending`, `closed`, `broken`, or `draft` (draft rows are skipped).

Source the terms from the merger agreement (SEC exhibit 2.1), the 8-K, the
DEFM14A/proxy, and the joint press release. Do not use a news summary for the
exchange ratio; read the filing.

## Run

```bash
cd "/Users/efren/Desktop/quant_finance/l'Observatori/merger_arb"
../inercia/.venv/bin/python3 src/run.py              # deals.csv
../inercia/.venv/bin/python3 src/run.py --paper      # append qualifying deals
../inercia/.venv/bin/python3 -m unittest discover -s tests -v
```

Outputs: `output/merger_arb.csv`, `output/merger_arb.json`,
`output/paper_ledger.csv` (append-only).

## Current state

The deal file is empty. That is deliberate: inventing terms would produce a
pretty table and a false strategy. The next step is to populate 10–20 live
deals, run the tracker daily, and paper-trade the qualifying ones for a quarter.
Only after that does a historical backtest (with a proper deal database) make
sense.

## Caveats

- No orders, no broker, no short-borrow check. A real stock deal needs the
  acquirer to be shortable at a sane borrow.
- The spread math ignores dividends, financing, taxes and the borrow cost on the
  short leg. Add them to the live ledger, not to the model.
- Annualising a 3-month spread assumes the deal closes on the expected date;
  delays are the norm, not the exception.
- This is research, not investment advice.
