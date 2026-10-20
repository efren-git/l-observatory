"""Append the latest completed months to the forward paper ledger.

Usage: ./.venv/bin/python3 src/forward_ledger.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.forward import update_ledger

if __name__ == "__main__":
    import json
    print(json.dumps(update_ledger(), indent=2))
