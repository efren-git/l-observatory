"""Entry point. Implementation: cartograf.pipeline.run_network."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cartograf.pipeline import run_network


if __name__ == "__main__":
    run_network()
