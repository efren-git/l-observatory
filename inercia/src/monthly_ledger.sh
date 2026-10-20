#!/bin/zsh
# Monthly paper-ledger job. Runs after the month-end close on the 1st.
# Append-only log; no orders, no broker.
set -u

ROOT="/Users/efren/Desktop/quant_finance/l'Observatori"
LOG="$ROOT/inercia/output/ledger_cron.log"

{
  echo "=== $(date '+%Y-%m-%d %H:%M:%S %Z') ==="
  cd "$ROOT/inercia" || { echo "FATAL: no inercia dir"; exit 1; }
  ./.venv/bin/python3 src/fetch_data.py || { echo "FATAL: inercia fetch"; exit 10; }

  cd "$ROOT/cartograf" || { echo "FATAL: no cartograf dir"; exit 1; }
  ./.venv/bin/python3 src/fetch_data.py --force || { echo "FATAL: cartograf fetch"; exit 11; }

  cd "$ROOT/inercia" || { echo "FATAL: no inercia dir"; exit 1; }
  ./.venv/bin/python3 src/forward_ledger.py || { echo "FATAL: forward ledger"; exit 12; }
  ./.venv/bin/python3 src/paper_trade.py || { echo "FATAL: paper trade"; exit 13; }

  echo "ok"
} >> "$LOG" 2>&1
