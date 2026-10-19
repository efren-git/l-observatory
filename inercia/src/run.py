"""Run one inercia stage, or the whole pipeline.

Usage:
    ./.venv/bin/python3 src/run.py all
    ./.venv/bin/python3 src/run.py momentum
    ./.venv/bin/python3 src/run.py finalbook
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from inercia.pipeline import STAGES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", nargs="?", default="all", choices=sorted(STAGES))
    args = parser.parse_args()
    STAGES[args.stage]()


if __name__ == "__main__":
    main()
