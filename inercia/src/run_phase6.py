"""Run the pre-registered Phase 6 core parameter study.

Usage: ./.venv/bin/python3 src/run_phase6.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.phase6 import run

if __name__ == "__main__":
    run()
