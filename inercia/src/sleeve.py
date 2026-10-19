"""Deprecated entry point. Prefer: python src/run.py sleeve."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import run_sleeve


if __name__ == "__main__":
    run_sleeve()
