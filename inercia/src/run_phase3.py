"""Run the Phase 3 combined book and write its metrics/chart.

Usage: ./.venv/bin/python3 src/run_phase3.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase3 import run

if __name__ == "__main__":
    run()
