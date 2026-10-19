"""Entry point. Implementation: cartograf.pipeline.run_vrp."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cartograf.pipeline import run_vrp


if __name__ == "__main__":
    run_vrp()
