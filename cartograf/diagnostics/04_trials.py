"""Diagnostic: trial registry and Deflated Sharpe Ratio.

Run after: ./.venv/bin/python3 src/run.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    metrics = json.loads((ROOT / "output" / "metrics.json").read_text())
    out = {
        "trial_registry": metrics.get("trial_registry"),
        "n_trials_all": metrics.get("n_trials_all"),
        "n_trials_final_published": metrics.get("n_trials_final_published"),
        "deflated_sharpe_all_trials": metrics.get("deflated_sharpe_all_trials"),
        "deflated_sharpe_final_variants": metrics.get("deflated_sharpe_final_variants"),
        "frequency": metrics.get("deflated_sharpe_frequency"),
    }
    (ROOT / "diagnostics" / "trials_diagnostic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
