"""Run the Phase 5 pairs/hedge research and paper-trading snapshot.

Usage: ./.venv/bin/python3 src/run_phase5.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase5 import run

if __name__ == "__main__":
    run()
