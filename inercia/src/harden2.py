"""Deprecated entry point. Prefer: python src/run.py tilt."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_tilt


if __name__ == "__main__":
    run_tilt()
