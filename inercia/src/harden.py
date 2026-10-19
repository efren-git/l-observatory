"""Deprecated entry point. Prefer: python src/run.py harden."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_harden


if __name__ == "__main__":
    run_harden()
