"""run.py - cartograf: test several published return patterns on free data, honestly.

Sleeves (each one grounded in a documented result):
  1. trend   - time-series momentum, multi-horizon           (Moskowitz-Ooi-Pedersen 2012)
  2. xsmom   - cross-sectional momentum, 12-1                (Jegadeesh & Titman 1993)
  3. value   - cross-asset long-horizon reversal             (Asness-Moskowitz-Pedersen 2013)
  4. bab     - betting against beta / defensive              (Frazzini & Pedersen 2014)
  5. vrp     - volatility risk premium, term-structure gated (classic short-vol)

Combination: equal-weight, inverse-vol, and Hierarchical Risk Parity (Lopez de Prado 2016).
Everything walk-forward, monthly, cost-aware.  Run:  ./.venv/bin/python3 src/run.py
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from fetch_data import UNIVERSE  # noqa: E402
from engine import (month_end_dates, weights_to_returns, perf, vol_target,  # noqa: E402
                    scale_weights_to_target, hrp_weights, drawdown)
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

OUT = os.path.join(ROOT, "output")
os.makedirs(OUT, exist_ok=True)

START = "2008-01-01"   # value needs 5y of prices; keeps the sample honest
COST = 5.0             # bps per unit turnover (ETFs)
COST_VOL = 10.0        # vol ETFs trade wider
TARGET = 0.10          # 10% vol target per sleeve / book


def load():
    px = pd.read_csv(os.path.join(ROOT, "data", "raw", "prices.csv"), parse_dates=["Date"]).set_index("Date")
    px = px.sort_index()
    tradable = [t for t in UNIVERSE if t in px.columns]
    R = px[tradable].pct_change().fillna(0.0)
    return px, R, tradable


def group_map(cols):
    g = {}
    for t, grp in UNIVERSE.items():
        if t in cols:
            g.setdefault(grp, []).append(t)
    return {k: v for k, v in g.items() if len(v) >= 2}


def group_z(df, groups):
    out = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for _, cols in groups.items():
        sub = df[cols]
        mu, sd = sub.mean(axis=1), sub.std(axis=1)
        out[cols] = sub.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)
    return out.fillna(0.0)


def xs_targets(score, me, groups):
    z = group_z(score, groups)
    w = z.copy()
    for _, cols in groups.items():
        denom = w[cols].abs().sum(axis=1).replace(0, np.nan)
        w[cols] = w[cols].div(denom, axis=0)
    w = w / max(len(groups), 1)
    return w.reindex(me).fillna(0.0)


def main():
    px, R, tradable = load()
    me = month_end_dates(R.index)
    me = me[me >= pd.Timestamp(START)]
    R = R.loc[R.index >= pd.Timestamp("2007-01-01")]   # warm-up for signals
    px = px.loc[R.index]
    groups = group_map(tradable)
    results, sleeve_daily, meta = {}, {}, {}

    # ---------- 1. trend (time-series momentum) ----------
    sigs = [np.sign(px / px.shift(h) - 1) for h in (21, 63, 126, 252)]
    sig = sum(sigs) / 4.0
    vol = R.rolling(63).std() * np.sqrt(252)
    w = (sig * (TARGET / vol.clip(lower=0.05))).reindex(me).fillna(0.0)
    w = scale_weights_to_target(w, R, TARGET)
    net, to, _ = weights_to_returns(R, w, COST)
    sleeve_daily["trend"] = net
    meta["trend"] = dict(turnover=round(to / (len(R) / 252), 2))

    # ---------- 2. cross-sectional momentum (12-1) ----------
    mom = (px.shift(21) / px.shift(252) - 1)
    w = scale_weights_to_target(xs_targets(mom, me, groups), R, TARGET)
    net, to, _ = weights_to_returns(R, w, COST)
    sleeve_daily["xsmom"] = net
    meta["xsmom"] = dict(turnover=round(to / (len(R) / 252), 2))

    # ---------- 3. value (cross-asset 5y reversal) ----------
    val = -(px / px.shift(1260) - 1)
    w = scale_weights_to_target(xs_targets(val, me, groups), R, TARGET)
    net, to, _ = weights_to_returns(R, w, COST)
    sleeve_daily["value"] = net
    meta["value"] = dict(turnover=round(to / (len(R) / 252), 2))

    # ---------- 4. betting against beta (equities) ----------
    eq = [t for t in tradable if UNIVERSE[t].startswith("equity")]
    spy = R["SPY"]
    beta = pd.DataFrame({t: R[t].rolling(252).cov(spy) / spy.rolling(252).var() for t in eq})
    score = -(beta.sub(1.0))
    score = score.div(vol[eq].clip(lower=0.05))            # risk-adjust the tilt
    wb = score.copy()
    wb = wb.div(wb.abs().sum(axis=1).replace(0, np.nan), axis=0)
    w = scale_weights_to_target(wb.reindex(me).fillna(0.0), R, TARGET)
    net, to, _ = weights_to_returns(R, w, COST)
    sleeve_daily["bab"] = net
    meta["bab"] = dict(turnover=round(to / (len(R) / 252), 2))

    # ---------- 5. volatility risk premium (term-structure gated) ----------
    contango = (px["^VIX3M"] / px["^VIX"]) > 1.02
    wv = pd.DataFrame(0.0, index=me, columns=tradable)
    wv["SVXY"] = contango.reindex(me).fillna(False).astype(float)
    wv = scale_weights_to_target(wv, R, TARGET)
    net, to, _ = weights_to_returns(R, wv, COST_VOL)
    sleeve_daily["vrp"] = net
    meta["vrp"] = dict(turnover=round(to / (len(R) / 252), 2),
                       exposure=round(float(contango.reindex(me).mean()), 3))

    sleeves = pd.DataFrame(sleeve_daily).dropna(how="all")
    sleeves = sleeves.loc[sleeves.index >= pd.Timestamp(START)].fillna(0.0)

    # ---------- combination ----------
    cols = list(sleeves.columns)
    equal = sleeves.mean(axis=1)
    trailing_vol = sleeves.rolling(63).std() * np.sqrt(252)
    ivw = (1.0 / trailing_vol.replace(0, np.nan)).shift(1)
    ivw = ivw.div(ivw.sum(axis=1), axis=0)
    invvol = (sleeves * ivw).sum(axis=1)

    # HRP on trailing 36m of compounded monthly sleeve returns, re-estimated each January
    monthly = (1 + sleeves).resample("ME").prod() - 1.0
    hrp_ret = pd.Series(0.0, index=sleeves.index)
    w_cur = pd.Series(1.0 / len(cols), index=cols)
    hrp_diag = {}
    for i, d in enumerate(sleeves.index):
        if d.month == 1:
            hist = monthly.loc[:d].dropna().tail(36)
            if len(hist) >= 18:
                w_new = hrp_weights(hist).reindex(cols).fillna(0.0)
                if float(w_new.sum()) > 1e-6:
                    w_cur = w_new / w_new.sum()
                    hrp_diag[str(d.date())] = {c: round(float(v), 3) for c, v in w_cur.items()}
        hrp_ret.iloc[i] = float((sleeves.loc[d, cols] * w_cur).sum())

    book = vol_target(hrp_ret)[0]
    book_ew = vol_target(equal)[0]

    # ---------- benchmarks ----------
    bench = pd.DataFrame({
        "SPY": R["SPY"],
        "60/40": 0.6 * R["SPY"] + 0.4 * R["IEF"],
    }).loc[sleeves.index]

    # ---------- report ----------
    report = {"sleeves": {}, "book": {}, "benchmarks": {}, "meta": meta,
              "corr": sleeves.corr().round(3).to_dict(), "hrp_weights_by_year": hrp_diag,
              "start": str(sleeves.index[0].date()),
              "end": str(sleeves.index[-1].date())}
    for c in cols:
        report["sleeves"][c] = perf(sleeves[c])
    book_iv = vol_target(invvol)[0]
    core = sleeves[["trend", "bab", "vrp"]].mean(axis=1)   # the three survivors, equal weight
    book_core = vol_target(core)[0]
    report["sleeves"]["_equal_book"] = perf(book_ew)
    report["sleeves"]["_invvol_book"] = perf(book_iv)
    report["sleeves"]["_hrp_book"] = perf(book)
    report["sleeves"]["_core_book"] = perf(book_core)
    report["sleeve_corr_to_spy"] = {c: round(float(sleeves[c].corr(R["SPY"].reindex(sleeves.index))), 3) for c in cols}
    for c in ["SPY", "60/40"]:
        report["benchmarks"][c] = perf(bench[c])

    # 60/40 + 30% book
    report["book"]["corr_core_vs_spy"] = round(float(book_core.corr(bench["SPY"])), 3)
    for name, series in (("60/40+30 equal", book_ew), ("60/40+30 invvol", book_iv), ("60/40+30 hrp", book), ("60/40+30 core", book_core)):
        mix = 0.7 * bench["60/40"] + 0.3 * series
        report["book"][name] = perf(mix)
    report["book"]["corr_equal_vs_spy"] = round(float(book_ew.corr(bench["SPY"])), 3)
    report["book"]["corr_equal_vs_6040"] = round(float(book_ew.corr(bench["60/40"])), 3)
    report["book"]["corr_invvol_vs_spy"] = round(float(book_iv.corr(bench["SPY"])), 3)
    report["book"]["corr_hpr_vs_spy"] = round(float(book.corr(bench["SPY"])), 3)
    report["book"]["corr_equal_vs_hrp"] = round(float(book_ew.corr(book)), 3)

    ann = {}
    for name, series in (("SPY", bench["SPY"]), ("60/40", bench["60/40"]), ("book_equal", book_ew)):
        ann[name] = (1 + series).groupby(series.index.year).prod().sub(1).round(4).to_dict()
    report["annual"] = ann

    # ---------- Ken French equity-factor cross-check (the academic factor zoo) ----------
    def rd(name):
        df = pd.read_csv(os.path.join(ROOT, "data", "raw", name), index_col=0, parse_dates=True)
        df.columns = [c.strip() for c in df.columns]
        return df

    def perf_m(m):
        m = m.dropna()
        if len(m) < 24:
            return {}
        eq = (1 + m).cumprod()
        years = len(m) / 12
        vol = float(m.std() * np.sqrt(12))
        return dict(CAGR=round(float(eq.iloc[-1] ** (1 / years) - 1), 4), Vol=round(vol, 4),
                    Sharpe=round(float(m.mean() * 12 / vol), 3),
                    MaxDD=round(float((eq / eq.cummax() - 1).min()), 4))

    f5, fm = rd("ff_ff5.csv"), rd("ff_ffmom.csv")
    cut = pd.Timestamp("2008-01-01")
    ffr = {}
    for col in [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA"] if c in f5.columns]:
        s = f5[col]  # already decimal (fetch_data divides percent by 100)
        ffr[col] = {"1963-2026": perf_m(s), "2008-2026": perf_m(s[s.index >= cut])}
    if "Mom" in fm.columns:
        s = fm["Mom"]  # already decimal
        ffr["MOM"] = {"1963-2026": perf_m(s), "2008-2026": perf_m(s[s.index >= cut])}
    report["french_factors"] = ffr

    with open(os.path.join(OUT, "metrics.json"), "w") as f:
        json.dump(report, f, indent=2)

    # ---------- charts ----------
    plt.style.use("dark_background")
    fig, ax = plt.subplots(figsize=(11, 6))
    for name, series in (("SPY", bench["SPY"]), ("60/40", bench["60/40"]),
                         ("book (HRP)", book), ("equal-weight", book_ew)):
        ax.plot((1 + series).cumprod(), label=f"{name}  (Sharpe {perf(series).get('Sharpe')})")
    ax.set_yscale("log"); ax.legend(); ax.set_title("cartograf - growth of 1 (net of costs)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_equity.png"), dpi=110); plt.close(fig)

    fig, ax = plt.subplots(figsize=(11, 5))
    for name, series in (("SPY", bench["SPY"]), ("60/40", bench["60/40"]), ("book (HRP)", book)):
        ax.plot(drawdown(series)[0], label=name)
    ax.legend(); ax.set_title("cartograf - drawdowns")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_drawdown.png"), dpi=110); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 7))
    c = sleeves.corr()
    im = ax.imshow(c, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(c))); ax.set_xticklabels(c.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(c))); ax.set_yticklabels(c.columns)
    for i in range(len(c)):
        for j in range(len(c)):
            ax.text(j, i, f"{c.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im); ax.set_title("cartograf - sleeve correlations (daily)")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "03_corr.png"), dpi=110); plt.close(fig)

    yrs = sorted({int(y) for y in ann["SPY"]})
    fig, ax = plt.subplots(figsize=(11, 5))
    idx = np.arange(len(yrs)); wdt = 0.4
    ax.bar(idx - wdt / 2, [ann["SPY"][y] for y in yrs], wdt, label="SPY")
    ax.bar(idx + wdt / 2, [ann["book_equal"][y] for y in yrs], wdt, label="book (equal-weight)")
    ax.set_xticks(idx); ax.set_xticklabels(yrs, rotation=60)
    ax.axhline(0, color="grey", lw=0.7); ax.legend(); ax.set_title("cartograf - annual returns")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "04_annual.png"), dpi=110); plt.close(fig)

    labels = list(ffr)
    fig, ax = plt.subplots(figsize=(10, 5))
    idx = np.arange(len(labels))
    ax.bar(idx - 0.2, [ffr[k]["1963-2026"].get("Sharpe", 0) for k in labels], 0.4, label="1963-2026")
    ax.bar(idx + 0.2, [ffr[k]["2008-2026"].get("Sharpe", 0) for k in labels], 0.4, label="2008-2026")
    ax.set_xticks(idx); ax.set_xticklabels(labels); ax.axhline(0, color="grey", lw=0.7)
    ax.legend(); ax.set_ylabel("Sharpe")
    ax.set_title("cartograf - equity factors: did the published edge survive?")
    fig.tight_layout(); fig.savefig(os.path.join(OUT, "05_factors.png"), dpi=110); plt.close(fig)

    print(json.dumps(report, indent=2)[:1500])


if __name__ == "__main__":
    main()
