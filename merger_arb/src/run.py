"""Run the merger-arbitrage tracker.

Usage:
  ./.venv/bin/python3 src/run.py                 # deals.csv
  ./.venv/bin/python3 src/run.py deals.example.csv
  ./.venv/bin/python3 src/run.py --paper         # append qualifying deals
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from merger_arb import paper_snapshot, run

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else str(Path(__file__).resolve().parents[1] / "deals.csv")
    if "--paper" in sys.argv:
        led = paper_snapshot(path)
        print(led.tail(20).to_string(index=False))
    else:
        out = run(path)
        print(f"as_of {out['as_of']}  deals {len(out['deals'])}")
        for d in out["deals"]:
            print(f"{d['deal_id']:12s} {d['target']:6s} {d['structure']:5s} "
                  f"spread={d['gross_spread']} ann={d['annualised']} "
                  f"break={d['break_downside']} risk={d['risk_tier']} -> {d['signal']}")
