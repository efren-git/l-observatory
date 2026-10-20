"""Run the Phase 7 tail-hedge study.

Usage: ./.venv/bin/python3 src/run_phase7.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase7 import run

if __name__ == "__main__":
    out = run()
    print("phase7_metrics.json written")
    for name, h in out["hedges"].items():
        print(name, h["stats"]["full"]["Sharpe"], h["stats"]["full"]["MaxDD"])
