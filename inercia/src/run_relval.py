"""Run the relative-value lab.

Usage: ./.venv/bin/python3 src/run_relval.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.relval import run

if __name__ == "__main__":
    out = run()
    print("relval_metrics.json written")
    print(out["portfolio"])
    print("active pairs mean", out["active_pairs"])
