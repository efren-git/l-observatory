"""Diagnostic: SVXY proxy vs the proper gated VRP in the core book.

Run after: ./.venv/bin/python3 src/run.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    metrics = json.loads((ROOT / "output" / "metrics.json").read_text())
    vrp = json.loads((ROOT / "output" / "vrp_metrics.json").read_text())
    out = {
        "legacy_svxy_core_common_sample": metrics["books"].get("core_legacy_svxy_common_sample"),
        "proper_gated_vrp_core": metrics["books"].get("core_proper_vrp"),
        "vrp_B_common": vrp.get("B_common_window"),
        "vrp_C_svxy_common": vrp.get("C_svxy_proxy_common_window"),
        "note": "The two core rows use the same 2009-11+ sample. The difference is "
                "the VRP implementation, not the sample.",
    }
    (ROOT / "diagnostics" / "vrp_proxy_diagnostic.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
