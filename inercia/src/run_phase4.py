"""Run the Phase 4 robustness checks.

Usage: ./.venv/bin/python3 src/run_phase4.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase4 import run

if __name__ == "__main__":
    run()
