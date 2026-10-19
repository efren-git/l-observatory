# Diagnostics

These scripts reproduce the evidence behind `AUDIT-2026-10-19.md`. They are
deliberately separate from the production pipeline: the point is to be able to
see how each error was detected, not just the final numbers.

Run from the cartograf folder:

```bash
./.venv/bin/python3 diagnostics/01_fx_carry.py
./.venv/bin/python3 diagnostics/02_vrp_proxy.py
./.venv/bin/python3 diagnostics/03_warmup.py
./.venv/bin/python3 diagnostics/04_trials.py
```

- `01_fx_carry.py` — compares FXE with spot EURUSD and with spot + foreign rate.
  It shows that FXE tracks spot, so the old FX leg was missing the foreign rate.
- `02_vrp_proxy.py` — compares the legacy SVXY core and the proper gated VRP core
  on the same 2009-11+ sample.
- `03_warmup.py` — shows the old 63-day zero-scale warm-up and the corrected
  unit-scale warm-up.
- `04_trials.py` — prints the trial registry and both Deflated Sharpe Ratios.

The JSON files next to the scripts are written by the scripts; they are safe to
regenerate and are small enough to commit.
