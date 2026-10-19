"""Deprecated entry point. Prefer: python src/run.py momentum."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_momentum


if __name__ == "__main__":
    run_momentum()
