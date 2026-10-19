"""Deprecated entry point. Prefer: python src/run.py finalbook."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_finalbook


if __name__ == "__main__":
    run_finalbook()
