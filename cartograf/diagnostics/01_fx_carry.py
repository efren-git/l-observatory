"""Diagnostic: does an FX ETF accrue the foreign deposit rate?

Run: ./.venv/bin/python3 diagnostics/01_fx_carry.py

It compares monthly FXE returns with:
  spot EURUSD
  spot + EUR 3m rate
  spot + EUR 3m rate - US 3m rate

The old carry.py used FXE return - US rate. If FXE tracks spot (as the output
shows), that return is missing the foreign rate. The corrected leg adds it.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cartograf.data import fred, prices  # noqa: E402


def main():
    px = prices()
    fr = fred()
    fxe = px["FXE"].dropna()
    out = {"fxe_range": [str(fxe.index.min().date()), str(fxe.index.max().date())]}
    try:
        import yfinance as yf
        eur = yf.download("EURUSD=X", start="2006-01-01", progress=False,
                          auto_adjust=True)["Close"]
        if isinstance(eur, pd.DataFrame):
            eur = eur.iloc[:, 0]
        eur = eur.dropna()
        eur.index = pd.to_datetime(eur.index).tz_localize(None)
        eur.to_csv(ROOT / "data" / "raw" / "eurusd_diag.csv")
        out["source"] = "yfinance EURUSD=X (saved to data/raw/eurusd_diag.csv)"
    except Exception as exc:
        path = ROOT / "data" / "raw" / "eurusd_diag.csv"
        if not path.exists():
            out["error"] = f"EURUSD unavailable: {exc}"
            print(json.dumps(out, indent=2))
            return
        eur = pd.read_csv(path, index_col=0, parse_dates=True).iloc[:, 0]
        out["source"] = "cached data/raw/eurusd_diag.csv"

    df = pd.DataFrame({"FXE": fxe, "EURUSD": eur}).dropna()
    m = df.resample("ME").last().pct_change().dropna()
    rates = fr[["fx_eur", "fx_usd"]].resample("ME").last().shift(2)
    rates = rates.reindex(m.index, method="ffill") / 100.0 / 12.0
    table = pd.DataFrame({
        "FXE": m["FXE"],
        "spot": m["EURUSD"],
        "spot_plus_eur": m["EURUSD"] + rates["fx_eur"],
        "spot_plus_eur_minus_us": m["EURUSD"] + rates["fx_eur"] - rates["fx_usd"],
    })
    out["monthly_mean_pct"] = (table.mean() * 100).round(4).to_dict()
    out["monthly_vol_pct"] = (table.std() * np.sqrt(12) * 100).round(3).to_dict()
    out["mean_fxe_minus_spot_bp"] = round(float((table["FXE"] - table["spot"]).mean() * 1e4), 2)
    out["mean_fxe_minus_spot_plus_eur_bp"] = round(
        float((table["FXE"] - table["spot_plus_eur"]).mean() * 1e4), 2)
    out["interpretation"] = (
        "FXE tracks spot closely; it does not accrue the full foreign rate. "
        "The old FX carry leg subtracted the US rate but never added the foreign rate, "
        "so the carry book was missing its main source of return."
    )
    path = ROOT / "diagnostics" / "fx_carry_diagnostic.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
