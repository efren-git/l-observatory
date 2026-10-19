"""Run every cartograf stage.

Usage: ./.venv/bin/python3 src/run_all.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cartograf.pipeline import run_all


if __name__ == "__main__":
    run_all()
