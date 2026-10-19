"""Deprecated entry point. Prefer: python src/run.py book."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_book


if __name__ == "__main__":
    run_book()
