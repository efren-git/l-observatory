"""Artifacts for cartograf: the five sleeves, books, VRP, carry, network."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .backtest import month_end_dates, turnover_annual
from .books import core_book, equal_book, hrp_book, invvol_book, mix_with_benchmark
from .config import COST, COST_VOL, OUT, START, TARGET
from .data import factor, prices, risk_free_daily, risk_free_monthly, survivorship_note
from .sleeves import (
    bab, carry_legs, monthly_to_daily, network_sleeves, trend, universe_setup,
    value, vrp_monthly, vrp_svxy, xsmom,
)
from .stats import (
    annual_returns, bootstrap_sharpe, deflated_sharpe, drawdown, perf, perf_m,
    sharpe_daily, vol_target, vol_target_m,
)

EXCESS_CONVENTION = {
    "net_long_benchmarks": ["SPY", "60/40"],
    "self_financing_sleeves": "raw; T-bills are not subtracted from a funded long/short book",
    "reported": "raw and excess columns where a risk-free rate applies",
}

TRIAL_REGISTRY = {
    "sleeves": 5,
    "combination_books": 4,
    "core_selection_legacy_proper": 2,
    "network_parameters": 3,
    "vrp_variants": 3,
    "carry_legs": 3,
    "carry_book": 1,
    "hrp_window": 1,
    "vol_target": 1,
}
N_TRIALS_ALL = sum(TRIAL_REGISTRY.values())
N_TRIALS_FINAL = 2


def _save_json(name, obj):
    with open(OUT / name, "w") as f:
        json.dump(obj, f, indent=2)


def _savefig(name):
    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(OUT / name, dpi=110)
    plt.close(fig)


def _dark():
    plt.style.use("dark_background")


def _curve(curves, title, name):
    fig, ax = plt.subplots(figsize=(11, 6))
    for label, s in curves.items():
        ax.plot((1 + s.fillna(0)).cumprod(), label=label)
    ax.set_yscale("log")
    ax.legend()
    ax.set_title(title)
    _savefig(name)


def _factor_crosscheck():
    def rd(name):
        d = factor(name)
        d.columns = [c.strip() for c in d.columns]
        return d
    f5, fm = rd("ff_ff5.csv"), rd("ff_ffmom.csv")
    cut = pd.Timestamp("2008-01-01")
    out = {}
    for col in [c for c in ["Mkt-RF", "SMB", "HML", "RMW", "CMA"] if c in f5.columns]:
        s = f5[col]
        out[col] = {"1963-2026": perf_m(s), "2008-2026": perf_m(s[s.index >= cut])}
    if "Mom" in fm.columns:
        s = fm["Mom"]
        out["MOM"] = {"1963-2026": perf_m(s), "2008-2026": perf_m(s[s.index >= cut])}
    return out


def run_main() -> dict:
    px, R, tradable, me, groups = universe_setup()
    sleeve_daily, meta = {}, {}

    net, to = trend(px, R, tradable, me, groups)
    sleeve_daily["trend"] = net
    meta["trend"] = {"turnover": to}

    net, to = xsmom(px, R, tradable, me, groups)
    sleeve_daily["xsmom"] = net
    meta["xsmom"] = {"turnover": to}

    net, to = value(px, R, tradable, me, groups)
    sleeve_daily["value"] = net
    meta["value"] = {"turnover": to}

    net, to = bab(R, tradable, me, groups)
    sleeve_daily["bab"] = net
    meta["bab"] = {"turnover": to}

    net, to, exposure = vrp_svxy(px, R, tradable, me)
    sleeve_daily["vrp_svxy"] = net
    meta["vrp_svxy"] = {"turnover": to, "exposure": round(exposure, 3)}

    sleeves = pd.DataFrame(sleeve_daily).dropna(how="all")
    sleeves = sleeves.loc[sleeves.index >= pd.Timestamp(START)].fillna(0.0)
    cols = list(sleeves.columns)

    # Proper VRP is monthly. Combine it with monthly trend and BAB, not with a
    # daily-smoothed version: spreading a monthly return across 21 days creates
    # artificial autocorrelation and flatters daily-vol-based combinations.
    vrp_df = vrp_monthly()
    monthly_base = (1 + sleeves[["trend", "bab"]]).resample("ME").prod() - 1
    # Align by month period: monthly_base is calendar month-end, vrp_df is the
    # last trading day. Exact-timestamp concat silently drops months whose last
    # calendar day is a weekend.
    monthly_base.index = monthly_base.index.to_period("M")
    vrp_monthly_b = vrp_df["B"].rename("vrp").copy()
    vrp_monthly_b.index = vrp_monthly_b.index.to_period("M")
    df_core_m = pd.concat([monthly_base, vrp_monthly_b], axis=1).dropna()
    df_core_m.index = df_core_m.index.to_timestamp(how="end").normalize()
    core_proper, core_scale = vol_target_m(df_core_m.mean(axis=1), TARGET)

    equal = equal_book(sleeves)
    invvol = invvol_book(sleeves)
    hrp, hrp_diag = hrp_book(sleeves)
    core_legacy = core_book(sleeves, ("trend", "bab", "vrp_svxy"))

    bench = pd.DataFrame({
        "SPY": R["SPY"],
        "60/40": 0.6 * R["SPY"] + 0.4 * R["IEF"],
    }).loc[sleeves.index]
    rf = risk_free_daily(sleeves.index)

    report = {
        "window": [str(sleeves.index[0].date()), str(sleeves.index[-1].date())],
        "sleeves": {},
        "books": {},
        "benchmarks": {},
        "meta": meta,
        "corr": sleeves.corr().round(3).to_dict(),
        "hrp_weights_by_year": hrp_diag,
        "start": str(sleeves.index[0].date()),
        "end": str(sleeves.index[-1].date()),
        "excess_convention": EXCESS_CONVENTION,
        "survivorship": survivorship_note(),
        "trial_registry": TRIAL_REGISTRY,
        "n_trials_all": N_TRIALS_ALL,
        "n_trials_final_published": N_TRIALS_FINAL,
    }
    for c in cols:
        report["sleeves"][c] = perf(sleeves[c])
    report["sleeves"]["vrp_gated_monthly"] = perf_m(vrp_df["B"])
    report["sleeve_corr_to_spy"] = {
        c: round(float(sleeves[c].corr(R["SPY"].reindex(sleeves.index))), 3)
        for c in cols
    }

    books = {
        "equal": (equal, bench),
        "invvol": (invvol, bench),
        "hrp": (hrp, bench),
        "core_legacy_svxy": (core_legacy, bench),
    }
    for name, (series, b) in books.items():
        report["books"][name] = {
            "stats": perf(series),
            "corr_to_spy": round(float(series.corr(b["SPY"])), 3),
            "60_40_plus_30": perf(mix_with_benchmark(b["60/40"], series, 0.3),
                                  rf_daily=risk_free_daily(b.index)),
        }

    bench_m = (1 + bench[["SPY", "60/40"]]).resample("ME").prod() - 1
    core_mix = 0.7 * bench_m["60/40"] + 0.3 * core_proper

    # Benchmark convention: the daily-rebalanced 60/40 above is the continuity
    # series. A monthly-rebalanced 60/40 (the way most funds actually run) has a
    # different Sharpe; report it separately rather than letting one convention
    # decide the conclusion.
    px_m = prices()[["SPY", "IEF"]].resample("ME").last().pct_change()
    sixty40_m_rebal = 0.6 * px_m["SPY"] + 0.4 * px_m["IEF"]
    core_mix_mr = (0.7 * sixty40_m_rebal.reindex(core_proper.index) + 0.3 * core_proper).dropna()

    def _claim(s: pd.Series, label: str) -> dict:
        s = s.dropna()
        sr = float(s.mean() / s.std()) if s.std() > 0 else 0.0
        return {
            "label": label,
            "stats": perf_m(s, rf_monthly=risk_free_monthly(s.index)),
            "dsr_all_trials": deflated_sharpe(
                sr, N_TRIALS_ALL, len(s), float(s.skew()), float(s.kurtosis() + 3)
            ),
            "bootstrap": bootstrap_sharpe(s, n_boot=2000, block=6, periods=12),
        }

    report["benchmarks_monthly"] = {
        "SPY": perf_m(px_m["SPY"], rf_monthly=risk_free_monthly(px_m.index)),
        "60_40_monthly_rebal": perf_m(
            sixty40_m_rebal, rf_monthly=risk_free_monthly(sixty40_m_rebal.index)
        ),
        "note": "monthly-rebalanced 60/40 (SPY/IEF), no rebalancing costs; "
                "the daily-rebalanced series is in benchmarks",
    }
    report["books"]["core_proper_vrp"] = {
        "stats": perf_m(core_proper),
        "corr_to_spy": round(float(core_proper.corr(bench_m["SPY"])), 3),
        "60_40_plus_30": perf_m(core_mix, rf_monthly=risk_free_monthly(core_mix.index)),
        "60_40_plus_30_monthly_rebal": perf_m(
            core_mix_mr, rf_monthly=risk_free_monthly(core_mix_mr.index)
        ),
        "leverage_mean": round(float(core_scale.mean()), 3),
        "leverage_max": round(float(core_scale.max()), 3),
        "frequency": "monthly",
    }
    report["claims"] = {
        "core_60_40_plus_30_daily_bench": _claim(core_mix, "60/40 daily-rebalanced + 30% core"),
        "core_60_40_plus_30_monthly_bench": _claim(core_mix_mr, "60/40 monthly-rebalanced + 30% core"),
    }

    # Like-for-like: the legacy SVXY core on the same 2009-11+ sample. Without
    # this, the proper-VRP improvement is confounded with a shorter, calmer sample.
    core_legacy_m = (1 + core_legacy).resample("ME").prod() - 1
    core_legacy_m = core_legacy_m.reindex(core_proper.index).dropna()
    legacy_mix = 0.7 * bench_m["60/40"] + 0.3 * core_legacy_m
    report["books"]["core_legacy_svxy_common_sample"] = {
        "stats": perf_m(core_legacy_m),
        "corr_to_spy": round(float(core_legacy_m.corr(bench_m["SPY"])), 3),
        "60_40_plus_30": perf_m(legacy_mix, rf_monthly=risk_free_monthly(legacy_mix.index)),
        "frequency": "monthly",
        "note": "same sample as core_proper_vrp; isolates the VRP proxy change",
    }

    for c in ["SPY", "60/40"]:
        report["benchmarks"][c] = perf(bench[c], rf_daily=rf)

    ann = {}
    for name, series in (("SPY", bench["SPY"]), ("60/40", bench["60/40"]),
                         ("book_equal", equal), ("book_core", core_proper)):
        ann[name] = (1 + series).groupby(series.index.year).prod().sub(1).round(4).to_dict()
    report["annual"] = ann
    report["french_factors"] = _factor_crosscheck()
    report["core_proper"] = {
        "weights": {"trend": 1 / 3, "bab": 1 / 3, "vrp_gated": 1 / 3},
        "window": [str(core_proper.index[0].date()), str(core_proper.index[-1].date())],
        "note": "equal-weight the three survivors; VRP is the proper gated series, not SVXY",
    }

    sr = float(core_proper.mean() / core_proper.std())
    n_obs = int(core_proper.dropna().shape[0])
    skew = float(core_proper.skew())
    kurt = float(core_proper.kurtosis() + 3)
    report["deflated_sharpe_all_trials"] = deflated_sharpe(sr, N_TRIALS_ALL, n_obs, skew, kurt)
    report["deflated_sharpe_final_variants"] = deflated_sharpe(sr, N_TRIALS_FINAL, n_obs, skew, kurt)
    report["deflated_sharpe_frequency"] = "monthly"

    _save_json("metrics.json", report)

    _dark()
    _curve({"SPY": bench["SPY"], "60/40": bench["60/40"],
            "equal-weight": equal, "core (proper VRP)": core_proper},
           "cartograf - growth of 1 (net of costs)", "01_equity.png")

    fig, ax = plt.subplots(figsize=(11, 5))
    for name, series in (("SPY", bench["SPY"]), ("60/40", bench["60/40"]),
                         ("equal-weight", equal), ("core (proper VRP)", core_proper)):
        ax.plot(drawdown(series)[0], label=name)
    ax.legend()
    ax.set_title("cartograf - drawdowns")
    _savefig("02_drawdown.png")

    fig, ax = plt.subplots(figsize=(8, 7))
    c = sleeves.corr()
    im = ax.imshow(c, vmin=-1, vmax=1, cmap="RdBu_r")
    ax.set_xticks(range(len(c)))
    ax.set_xticklabels(c.columns, rotation=45, ha="right")
    ax.set_yticks(range(len(c)))
    ax.set_yticklabels(c.columns)
    for i in range(len(c)):
        for j in range(len(c)):
            ax.text(j, i, f"{c.iloc[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(im)
    ax.set_title("cartograf - sleeve correlations (daily)")
    _savefig("03_corr.png")

    yrs = sorted({int(y) for y in ann["SPY"]})
    fig, ax = plt.subplots(figsize=(11, 5))
    idx = np.arange(len(yrs))
    wdt = 0.4
    ax.bar(idx - wdt / 2, [ann["SPY"].get(y, 0) for y in yrs], wdt, label="SPY")
    ax.bar(idx + wdt / 2, [ann["book_equal"].get(y, 0) for y in yrs], wdt,
           label="book (equal-weight)")
    ax.set_xticks(idx)
    ax.set_xticklabels(yrs, rotation=60)
    ax.axhline(0, color="grey", lw=0.7)
    ax.legend()
    ax.set_title("cartograf - annual returns")
    _savefig("04_annual.png")

    labels = list(report["french_factors"])
    fig, ax = plt.subplots(figsize=(10, 5))
    idx = np.arange(len(labels))
    ax.bar(idx - 0.2, [report["french_factors"][k]["1963-2026"].get("Sharpe", 0) for k in labels], 0.4, label="1963-2026")
    ax.bar(idx + 0.2, [report["french_factors"][k]["2008-2026"].get("Sharpe", 0) for k in labels], 0.4, label="2008-2026")
    ax.set_xticks(idx)
    ax.set_xticklabels(labels)
    ax.axhline(0, color="grey", lw=0.7)
    ax.legend()
    ax.set_ylabel("Sharpe")
    ax.set_title("cartograf - equity factors: did the published edge survive?")
    _savefig("05_factors.png")
    return report


def run_network() -> dict:
    res = network_sleeves()
    R = res["R"]
    spy = R["SPY"].reindex(res["own"].index)
    bench = (0.6 * R["SPY"] + 0.4 * R["IEF"]).reindex(res["own"].index)
    rf = risk_free_daily(spy.index)
    rep = {
        "window": [str(res["own"].index[0].date()), str(res["own"].index[-1].date())],
        "params": {"window_weeks": 156, "top_k": 5, "blend": 0.5},
        "avg_lead_corr_kept": res["avg_lead_corr"],
        "trend_only": perf(res["own"]),
        "network_only": perf(res["network"]),
        "trend_plus_network": perf(res["combined"]),
        "SPY": perf(spy, rf_daily=rf),
        "corr_own_vs_net": round(float(res["own"].corr(res["network"])), 3),
        "corr_comb_vs_spy": round(float(res["combined"].corr(spy)), 3),
        "turnover": res["turnover"],
        "excess_convention": EXCESS_CONVENTION,
    }
    for name, s in (("trend_only", res["own"]), ("trend+network", res["combined"])):
        rep[f"60/40+30 {name}"] = perf(mix_with_benchmark(bench, s, 0.3), rf_daily=rf)
    _save_json("network_metrics.json", rep)

    _dark()
    _curve({"trend only": res["own"], "network only": res["network"],
            "trend + network": res["combined"], "SPY": spy},
           "cartograf - network momentum vs plain trend", "06_network.png")
    return rep


def run_vrp() -> dict:
    df = vrp_monthly()
    common = df.index[df["K3"].notna()]
    a = df["A"].reindex(common)
    b = df["B"].reindex(common)
    c = df["C"].reindex(common)
    px = prices()
    # common is a last-trading-day index; align the calendar month-end price
    # series to it by period rather than by exact timestamp.
    m_px = px[["SPY", "IEF"]].resample("ME").last().pct_change()
    m_px.index = m_px.index.to_period("M")
    m_px = m_px.reindex(pd.PeriodIndex(common, freq="M"))
    m_px.index = common
    bench = 0.6 * m_px["SPY"] + 0.4 * m_px["IEF"]
    rf = risk_free_monthly(common)

    rep = {
        "vix3m_from": str(px.index[0].date()) if False else str(df["K3"].dropna().index[0].date()),
        "window": [str(df.index[0].date()), str(df.index[-1].date())],
        "n_months": int(len(df)),
        "premium": {
            "mean_implied_vol": round(float(df["K"].mean()), 2),
            "mean_realized_vol": round(float(df["RV"].mean()), 2),
            "mean_pnl_vol_points": round(float(df["pnl"].mean()), 3),
            "pct_months_implied_gt_realized": round(float((df["K"] > df["RV"]).mean()), 3),
        },
        "contango_fraction": round(float(df["contango"].mean()), 3),
        "A_always_on": perf_m(df["A"]),
        "B_contango_gated": perf_m(df["B"]),
        "C_svxy_proxy": perf_m(df["C"]),
        "common_window": [str(common[0].date()), str(common[-1].date())],
        "A_common_window": perf_m(a),
        "B_common_window": perf_m(b),
        "C_svxy_proxy_common_window": perf_m(c),
        "SPY_common": perf_m(m_px["SPY"], rf_monthly=rf.reindex(m_px.index)),
        "60_40_common": perf_m(bench, rf_monthly=rf.reindex(bench.index)),
        "excess_convention": EXCESS_CONVENTION,
    }
    for name, s in (("A_always_on", a), ("B_contango_gated", b)):
        mix = (0.7 * bench + 0.3 * s.reindex(bench.index).fillna(0.0)).dropna()
        rep[f"60/40+30 {name}"] = perf_m(mix, rf_monthly=rf.reindex(mix.index))
        sr = float(mix.mean() / mix.std()) if mix.std() > 0 else 0.0
        rep[f"60/40+30 {name}_dsr_all_trials"] = deflated_sharpe(
            sr, N_TRIALS_ALL, len(mix), float(mix.skew()), float(mix.kurtosis() + 3)
        )
        rep[f"60/40+30 {name}_bootstrap"] = bootstrap_sharpe(
            mix, n_boot=2000, block=6, periods=12
        )
    crisis = {}
    for d in ["2008-10-31", "2018-02-28", "2020-03-31"]:
        ts = pd.Timestamp(d)
        if ts in df.index:
            crisis[d] = {"A": round(float(df["A"].get(ts, np.nan)), 4),
                         "B": round(float(df["B"].get(ts, np.nan)), 4),
                         "SPY": round(float(m_px["SPY"].get(ts, np.nan)), 4)}
    rep["crisis_months"] = crisis
    _save_json("vrp_metrics.json", rep)

    _dark()
    _curve({"A always-on": a, "B contango-gated": b, "SPY": m_px["SPY"],
            "60/40": bench},
           "cartograf - volatility risk premium (common window)", "07_vrp.png")
    return rep


def run_carry() -> dict:
    res = carry_legs()
    combined = res["combined"]
    carry_book = res["carry_book"]
    R = res["inputs"]["R"]
    spy = R["SPY"].reindex(combined.index)
    bench = (0.6 * R["SPY"] + 0.4 * R["IEF"]).reindex(combined.index)
    rf = risk_free_daily(combined.index)
    rep = {
        "window": [str(combined.index[0].date()), str(combined.index[-1].date())],
        "turnover_x_yr": res["turnover"],
        "sleeves": {
            "bond_carry": perf(res["bond"]),
            "equity_carry": perf(res["equity"]),
            "fx_carry": perf(res["fx"]),
            "carry_book": perf(carry_book),
        },
        "corr": {
            "carry_vs_spy": round(float(carry_book.corr(spy)), 3),
            "carry_vs_6040": round(float(carry_book.corr(bench)), 3),
            "bond_vs_fx": round(float(res["bond"].corr(res["fx"])), 3),
            "bond_vs_eq": round(float(res["bond"].corr(res["equity"])), 3),
            "eq_vs_fx": round(float(res["equity"].corr(res["fx"])), 3),
        },
        "benchmarks": {
            "SPY": perf(spy, rf_daily=rf),
            "60/40": perf(bench, rf_daily=rf),
        },
        "fx_convention": "FX ETF return + publication-lagged foreign rate - US rate; "
                         "the old code subtracted the US rate but never added the foreign rate",
        "excess_convention": EXCESS_CONVENTION,
    }
    for frac in (0.2, 0.3):
        rep[f"60/40+{int(frac*100)} carry"] = perf(
            mix_with_benchmark(bench, carry_book, frac), rf_daily=rf)
    rep["annual"] = {
        k: (1 + v).groupby(v.index.year).prod().sub(1).round(4).to_dict()
        for k, v in (("carry", carry_book), ("SPY", spy))
    }
    _save_json("carry_metrics.json", rep)

    _dark()
    _curve({"carry book": carry_book, "bond carry": res["bond"],
            "equity carry": res["equity"], "fx carry": res["fx"],
            "SPY": spy, "60/40": bench},
           "cartograf - cross-asset carry", "08_carry.png")
    return rep


def run_all() -> dict:
    out = {}
    for name, fn in (("main", run_main), ("network", run_network),
                     ("vrp", run_vrp), ("carry", run_carry)):
        print(f"[cartograf] {name} ...", flush=True)
        out[name] = fn()
    print("[cartograf] done", flush=True)
    return out


STAGES = {"main": run_main, "network": run_network, "vrp": run_vrp,
          "carry": run_carry, "all": run_all}
