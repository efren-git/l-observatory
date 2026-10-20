"""Print and append the latest paper-trading snapshot.

This is a ledger, not an order router. Run it after a month-end close.

Usage: ./.venv/bin/python3 src/paper_trade.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase5 import paper_trade_snapshot

if __name__ == "__main__":
    print(json.dumps(paper_trade_snapshot(), indent=2))
