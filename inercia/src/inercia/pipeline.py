"""Reproducible analyses and artifacts for inercia.

Every public run_* function regenerates the charts and JSON files that belong to
that stage. run_all() regenerates everything. Scripts in src/ are thin wrappers.
"""
from __future__ import annotations

import json
from functools import lru_cache

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import COST_BPS, OUT, STOCK_COST_BPS
from .data import prices, risk_free_daily, stocks, survivorship_note
from .engines import (
    carry_returns,
    reversal_returns,
    stock_sleeve,
    trend_returns,
)
from .stats import (
    annual_returns,
    bootstrap_sharpe,
    deflated_sharpe,
    drawdown_control,
    perf,
    perf_m,
    sharpe_daily,
    vol_target,
)

EXCESS_CONVENTION = {
    "net_long_benchmarks": ["SPY", "60/40"],
    "self_financing_sleeves": "reported raw; subtracting T-bills would be double-counting",
    "reported": "raw and excess columns where a risk-free rate applies",
}


def _save_json(name: str, obj) -> None:
    with open(OUT / name, "w") as f:
        json.dump(obj, f, indent=2)


def _save_fig(name: str) -> None:
    fig = plt.gcf()
    fig.tight_layout()
    fig.savefig(OUT / name)
    plt.close(fig)


def _curve_plot(curves: dict, title: str, name: str) -> None:
    eq = pd.DataFrame({k: (1 + v).cumprod() for k, v in curves.items()}).dropna()
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for c in eq.columns:
        ax.plot(eq.index, eq[c], lw=1.7, label=c)
    ax.set_yscale("log")
    ax.set_title(title)
    ax.set_ylabel("growth of $1")
    ax.legend()
    _save_fig(name)


@lru_cache(maxsize=1)
def _trend():
    return trend_returns(prices(), cost_bps=COST_BPS)


@lru_cache(maxsize=1)
def _trend_gross():
    return trend_returns(prices(), cost_bps=0.0)


@lru_cache(maxsize=1)
def _carry():
    return carry_returns()


@lru_cache(maxsize=1)
def _benchmarks():
    ret = prices().pct_change()
    spy = ret["SPY"].fillna(0.0)
    sixty40 = 0.6 * ret["SPY"].fillna(0.0) + 0.4 * ret["IEF"].fillna(0.0)
    rf = risk_free_daily(ret.index)
    return spy, sixty40, rf


@lru_cache(maxsize=1)
def _monthly_6040():
    """Monthly-rebalanced 60/40 (SPY/IEF), the way most funds run it."""
    ret = prices().pct_change()
    spy_m = (1 + ret["SPY"].fillna(0.0)).resample("ME").prod() - 1
    ief_m = (1 + ret["IEF"].fillna(0.0)).resample("ME").prod() - 1
    return 0.6 * spy_m + 0.4 * ief_m, spy_m


@lru_cache(maxsize=1)
def _sleeves() -> pd.DataFrame:
    trend, _ = _trend()
    carry, _, _ = _carry()
    return pd.DataFrame({"trend": trend, "carry": carry}).dropna()


def fixed_book(df: pd.DataFrame, weights: dict) -> pd.Series:
    return sum(df[k] * w for k, w in weights.items())


def walkforward_weights(df: pd.DataFrame, min_obs: int = 756,
                        refit: str = "YE") -> pd.DataFrame:
    """Expanding-window, long-only mean-variance weights, applied out of sample."""
    rows = {}
    for d in df.resample(refit).last().index:
        hist = df.loc[:d]
        if len(hist) < min_obs:
            continue
        mu = hist.mean().values
        cov = hist.cov().values
        try:
            w = np.linalg.solve(cov, mu)
        except np.linalg.LinAlgError:
            w = mu
        w = np.clip(np.asarray(w, dtype=float), 0.0, None)
        if not np.isfinite(w).all() or w.sum() <= 0:
            w = np.ones(df.shape[1])
        rows[d] = w / w.sum()
    if not rows:
        eq = np.ones(df.shape[1]) / df.shape[1]
        return pd.DataFrame([eq] * len(df), index=df.index, columns=df.columns)
    wf = pd.DataFrame.from_dict(rows, orient="index", columns=df.columns).sort_index()
    return wf.reindex(df.index, method="ffill").shift(1).fillna(1.0 / df.shape[1])


def run_momentum() -> dict:
    trend, diag = _trend()
    gross, _ = _trend_gross()
    spy, sixty40, rf = _benchmarks()
    res = {
        "strategy_net": perf(trend),
        "strategy_gross": perf(gross),
        "spy_buy_hold": perf(spy, rf=rf),
        "sixty_forty": perf(sixty40, rf=rf),
        "annual_turnover": diag["annual_turnover"],
        "annual_cost_drag": diag["annual_cost_drag"],
        "corr_to_spy": round(float(trend.corr(spy)), 3),
        "subperiods": {
            "2004_2007": perf(trend.loc["2004-01-01":"2007-12-31"]),
            "2008_2009": perf(trend.loc["2008-01-01":"2009-12-31"]),
            "2010_2019": perf(trend.loc["2010-01-01":"2019-12-31"]),
            "2020_2026": perf(trend.loc["2020-01-01":"2026-12-31"]),
        },
        "excess_convention": EXCESS_CONVENTION,
    }
    _save_json("metrics.json", res)
    _curve_plot({"Strategy (net)": trend, "SPY buy & hold": spy, "60/40": sixty40},
                "inercia: momentum strategy vs benchmarks (log scale)", "01_equity.png")
    dd = (1 + trend).cumprod()
    dd = dd / dd.cummax() - 1
    fig, ax = plt.subplots(figsize=(11, 3.5))
    ax.fill_between(dd.index, dd.values, 0, color="#c0392b", alpha=0.6)
    ax.set_title("Strategy drawdown")
    ax.set_ylabel("drawdown")
    _save_fig("02_drawdown.png")
    return res


def run_variants() -> dict:
    px = prices()
    ret = px.pct_change()
    spy = ret["SPY"].fillna(0.0)
    variants = {}
    for freq in ["ME", "QE"]:
        for use_xs in [False, True]:
            for cb in [False, True]:
                key = f"freq={freq} xs={use_xs} classbal={cb}"
                net, diag = trend_returns(px, use_xs=use_xs, class_bal=cb,
                                          rebalance=freq, cost_bps=COST_BPS)
                d = perf(net)
                d["turnover"] = diag["annual_turnover"]
                d["cost_drag"] = diag["annual_cost_drag"]
                d["corr_spy"] = round(float(net.corr(spy)), 3)
                variants[key] = d
    _save_json("variants.json", variants)
    return variants


def run_riskalloc() -> dict:
    px = prices()
    ret = px.pct_change()
    spy = ret["SPY"].fillna(0.0)
    ief = ret["IEF"].fillna(0.0)
    sixty40 = 0.6 * spy + 0.4 * ief
    res = {}
    series = {}
    for wname in ["gross", "class"]:
        for xs in [False, True]:
            net, diag = trend_returns(px, use_xs=xs, class_bal=(wname == "class"),
                                      cost_bps=COST_BPS)
            key = f"w={wname} xs={xs}"
            d = perf(net)
            d["turnover"] = diag["annual_turnover"]
            d["corr_spy"] = round(float(net.corr(spy)), 3)
            res[key] = d
            series[key] = net
    bestkey = max(series, key=lambda k: res[k]["Sharpe"])
    best = series[bestkey]
    for w_trend in [0.0, 0.2, 0.3, 0.4]:
        res[f"combo_60_40_plus_{int(w_trend * 100)}trend"] = perf(
            (1 - w_trend) * sixty40 + w_trend * best
        )
    out = {"variants": res, "best": bestkey,
           "excess_convention": EXCESS_CONVENTION}
    _save_json("riskalloc.json", out)
    return out


def run_final() -> dict:
    trend, diag = _trend()
    spy, sixty40, rf = _benchmarks()
    combo = 0.7 * sixty40 + 0.3 * trend
    res = {
        "strategy": perf(trend),
        "spy": perf(spy, rf=rf),
        "sixty40": perf(sixty40, rf=rf),
        "combo_60_40_plus_30": perf(combo, rf=rf),
        "corr_strategy_spy": round(float(trend.corr(spy)), 3),
        "annual_turnover": diag["annual_turnover"],
        "excess_convention": EXCESS_CONVENTION,
    }
    _save_json("final_metrics.json", res)
    _curve_plot({"Strategy": trend, "SPY": spy, "60/40": sixty40,
                 "60/40 + 30% strategy": combo},
                "inercia strategy vs benchmarks (log scale)", "03_equity_final.png")
    ann = pd.DataFrame({"strategy": trend, "SPY": spy}).dropna()
    table = annual_returns(ann["strategy"]), annual_returns(ann["SPY"])
    years = sorted(set(table[0].index) | set(table[1].index))
    fig, ax = plt.subplots(figsize=(11, 4.5))
    x = np.arange(len(years))
    wt = 0.4
    ax.bar(x - wt / 2, [table[0].get(y, 0) * 100 for y in years], wt,
           label="Strategy", color="#8e44ad")
    ax.bar(x + wt / 2, [table[1].get(y, 0) * 100 for y in years], wt,
           label="SPY", color="#2c3e50")
    ax.set_xticks(x)
    ax.set_xticklabels([str(y)[:4] for y in years], rotation=45)
    ax.axhline(0, color="grey", lw=0.8)
    ax.set_ylabel("annual return %")
    ax.set_title("Annual returns: strategy vs SPY")
    ax.legend()
    _save_fig("04_annual.png")
    return res


def run_carry() -> dict:
    carry, cdiag, cmeta = _carry()
    trend, _ = _trend()
    df = pd.DataFrame({"trend": trend, "carry": carry}).dropna()
    combo = 0.5 * vol_target(df["trend"])[0] + 0.5 * vol_target(df["carry"])[0]
    res = {
        "carry": perf(df["carry"]),
        "trend": perf(df["trend"]),
        "combo_50_50": perf(combo),
        "corr_trend_carry": round(float(df["trend"].corr(df["carry"])), 3),
        "carry_meta": cmeta,
        "carry_turnover": cdiag["annual_turnover"],
        "excess_convention": EXCESS_CONVENTION,
    }
    _save_json("carry_metrics.json", res)
    _curve_plot({"Carry": df["carry"], "Trend": df["trend"], "50/50 combo": combo},
                "Two uncorrelated engines: carry vs trend vs combo (log)",
                "05_carry_combo.png")
    return res


def run_combo() -> dict:
    trend, _ = _trend()
    carry, _, _ = _carry()
    rev, _ = reversal_returns(prices())
    df = pd.DataFrame({"trend": trend, "carry": carry, "reversal": rev}).dropna()
    res = {
        "trend": perf(df["trend"]),
        "carry": perf(df["carry"]),
        "reversal": perf(df["reversal"]),
        "corr": df.corr().round(3).to_dict(),
    }
    eq3 = sum(vol_target(df[c])[0] for c in df.columns) / 3.0
    res["combo_equal_3"] = perf(eq3)
    mu = df.mean().values
    cov = df.cov().values
    try:
        w_tan = np.linalg.solve(cov, mu)
        w_tan = w_tan / w_tan.sum()
        tan = pd.Series(df.values @ w_tan, index=df.index)
        res["combo_tangency"] = perf(tan)
        res["tangency_weights"] = {k: round(float(v), 3) for k, v in zip(df.columns, w_tan)}
        res["tangency_in_sample"] = True
    except np.linalg.LinAlgError:
        res["combo_tangency"] = None
    _save_json("combo_metrics.json", res)
    _curve_plot({"Trend": df["trend"], "Carry": df["carry"],
                 "Reversal": df["reversal"], "Equal-risk combo": eq3},
                "inercia multi-engine book: trend, carry, reversal (log)",
                "06_engines.png")
    return res


def _book():
    """Return both the unlevered book and the 10%-vol-target version.

    The historical headline book is 74/26 with weights summing to one. Applying
    a second volatility target to that book levers it ~1.38x on average (because
    trend and carry are nearly uncorrelated) and deepens the drawdown. Both are
    reported; the unlevered version is the headline.
    """
    df = _sleeves()
    fixed = {"trend": 0.74, "carry": 0.26}
    raw = fixed_book(df, fixed)
    target, scale = vol_target(raw)
    wf = walkforward_weights(df)
    wf_raw = (wf * df).sum(axis=1)
    wf_target, _ = vol_target(wf_raw)
    return df, raw, target, wf, wf_raw, wf_target, scale


def run_book() -> dict:
    df, book, book_target, wf, book_wf, book_wf_target, scale = _book()
    spy, sixty40, rf = _benchmarks()
    combo = 0.7 * sixty40 + 0.3 * book
    res = {
        "trend": perf(df["trend"]),
        "carry": perf(df["carry"]),
        "corr_trend_carry": round(float(df["trend"].corr(df["carry"])), 3),
        "book_weights": {"trend": 0.74, "carry": 0.26},
        "book_weights_note": "fixed 74/26 selected in-sample; headline book is unlevered",
        "book": perf(book),
        "book_target_vol": perf(book_target),
        "book_walkforward": perf(book_wf),
        "book_walkforward_target_vol": perf(book_wf_target),
        "leverage_mean": round(float(scale.mean()), 3),
        "leverage_max": round(float(scale.max()), 3),
        "book_weights_walkforward_latest": {
            k: round(float(v), 3) for k, v in wf.iloc[-1].items()
        },
        "sixty40": perf(sixty40, rf=rf),
        "combo_60_40_plus_30_book": perf(combo, rf=rf),
        "excess_convention": EXCESS_CONVENTION,
    }
    _save_json("book_metrics.json", res)
    _curve_plot({"Trend": df["trend"], "Carry": df["carry"],
                 "Book (trend+carry)": book, "60/40 + 30% book": combo},
                "inercia book: trend + carry, and its portfolio value", "07_book.png")
    return res


def run_harden() -> dict:
    df, book_unlev, book, _, _, _, _ = _book()
    book_dd_gross = drawdown_control(book, 0.20, cost_bps=0.0)
    book_dd = drawdown_control(book, 0.20, cost_bps=5.0)
    sv = book.rolling(20).std() * np.sqrt(252.0)
    lv = book.rolling(252).std() * np.sqrt(252.0)
    regime = np.clip((lv / sv).shift(1), 0.4, 1.2)
    book_reg_gross = (book * regime).fillna(0.0)
    regime_trade = regime.diff().abs().fillna(0.0) * 5.0 / 1e4
    book_reg = (book_reg_gross - regime_trade).fillna(0.0)
    book_hard_gross = drawdown_control(book_reg_gross, 0.20, cost_bps=0.0)
    book_hard = drawdown_control(book_reg, 0.20, cost_bps=5.0)
    res = {
        "trend": perf(df["trend"]),
        "carry": perf(df["carry"]),
        "book_unlevered": perf(book_unlev),
        "book": perf(book),
        "book_dd_control_gross": perf(book_dd_gross),
        "book_dd_control": perf(book_dd),
        "book_regime_gross": perf(book_reg_gross),
        "book_regime": perf(book_reg),
        "book_hardened_gross": perf(book_hard_gross),
        "book_hardened": perf(book_hard),
        "note": "overlays are preference trades; net figures charge 5 bps per unit "
                "of exposure change",
    }
    _save_json("hardened_metrics.json", res)
    _curve_plot({"Book": book, "Book + DD control": book_dd,
                 "Book hardened (DD+regime)": book_hard},
                "Hardening the book: drawdown control + regime scaling",
                "08_hardened.png")
    return res


def run_tilt() -> dict:
    df = _sleeves()
    base, _ = vol_target(fixed_book(df, {"trend": 0.74, "carry": 0.26}))  # 10% target
    sv = base.rolling(20).std()
    lv = base.rolling(252).std()
    regime = (sv / lv).shift(1).clip(0.8, 2.0)
    out = {"base_book": perf(base)}
    for k in [0.3, 0.6, 1.0]:
        wt = (0.5 + k * (regime - 1)).clip(0, 1).fillna(0.5)
        g_gross = df["trend"] * wt + df["carry"] * (1 - wt)
        trade = wt.diff().abs().fillna(0.0) * 5.0 / 1e4
        g = g_gross - trade
        out[f"tilt_k{k}_gross"] = perf(vol_target(g_gross)[0])
        out[f"tilt_k{k}"] = perf(vol_target(g)[0])
    _save_json("tilt_metrics.json", out)
    return out


def run_sleeve() -> dict:
    px = prices()
    st = stocks()
    xsm, xdiag = stock_sleeve(st, "mom", cost_bps=STOCK_COST_BPS)
    low, ldiag = stock_sleeve(st, "lowvol", cost_bps=STOCK_COST_BPS)
    sleeve = 0.5 * vol_target(xsm)[0] + 0.5 * vol_target(low)[0]
    trend, _ = _trend()
    df = pd.DataFrame({"trend": trend, "xs_mom": xsm, "lowvol": low,
                       "sleeve": sleeve}).dropna()
    combo = 0.5 * vol_target(df["trend"])[0] + 0.5 * vol_target(df["sleeve"])[0]
    res = {
        "xs_momentum": perf(df["xs_mom"]),
        "low_vol": perf(df["lowvol"]),
        "equity_sleeve": perf(df["sleeve"]),
        "trend": perf(df["trend"]),
        "corr_sleeve_trend": round(float(df["sleeve"].corr(df["trend"])), 3),
        "corr_mom_trend": round(float(df["xs_mom"].corr(df["trend"])), 3),
        "turnover_mom": xdiag["annual_turnover"],
        "turnover_lowvol": ldiag["annual_turnover"],
        "cost_bps": STOCK_COST_BPS,
        "survivorship": survivorship_note(),
        "combo_trend_sleeve": perf(combo),
    }
    _save_json("sleeve_metrics.json", res)
    _curve_plot({"Trend book": df["trend"], "Equity sleeve": df["sleeve"],
                 "50/50": combo},
                "inercia: trend book + cross-sectional equity sleeve (log)",
                "09_sleeve.png")
    return res


TRIAL_REGISTRY = {
    "trend_variants": 8,
    "risk_allocation_variants": 4,
    "tilt_variants": 3,
    "combo_variants": 2,
    "carry_combo": 1,
    "sleeve_variants": 2,
    "book_weightings": 2,
    "hardening_overlays": 3,
    "final_book": 1,
}


def run_finalbook() -> dict:
    trend, _ = _trend()
    carry, _, _ = _carry()
    xsm, xdiag = stock_sleeve(stocks(), "mom", cost_bps=STOCK_COST_BPS)
    # The book is trend + carry. The stock sleeve is reported separately because
    # it is survivorship-biased; it must not truncate the book sample.
    df = pd.DataFrame({"trend": trend, "carry": carry}).dropna()
    df_all = pd.DataFrame({"trend": trend, "carry": carry, "xsmom": xsm}).dropna()
    fixed = {"trend": 0.74, "carry": 0.26}
    book = fixed_book(df, fixed)
    book_target, scale = vol_target(book)
    wf = walkforward_weights(df)
    book_wf = (wf * df).sum(axis=1)
    book_wf_target, _ = vol_target(book_wf)
    spy, sixty40, rf = _benchmarks()
    combo = (0.7 * sixty40 + 0.3 * book).dropna()
    sr = sharpe_daily(book)
    n_obs = int(book.dropna().shape[0])
    dsr_all = deflated_sharpe(sr, sum(TRIAL_REGISTRY.values()), n_obs,
                              skew=float(book.skew()), kurt=float(book.kurtosis() + 3))
    dsr_final = deflated_sharpe(sr, 2, n_obs,
                                skew=float(book.skew()), kurt=float(book.kurtosis() + 3))
    overlay_sr = sharpe_daily(combo)
    overlay_dsr = deflated_sharpe(
        overlay_sr, sum(TRIAL_REGISTRY.values()), len(combo),
        skew=float(combo.skew()), kurt=float(combo.kurtosis() + 3),
    )
    overlay_boot = bootstrap_sharpe(combo, n_boot=2000, block=21)
    sixty40_m, spy_m = _monthly_6040()
    book_m = (1 + book).resample("ME").prod() - 1
    combo_m = (0.7 * sixty40_m + 0.3 * book_m).dropna()
    rf_m = (1 + rf).resample("ME").prod() - 1
    res = {
        "trend": perf(df["trend"]),
        "carry": perf(df["carry"]),
        "xs_momentum": perf(xsm),
        "corr": df_all.corr().round(3).to_dict(),
        "book_weights": fixed,
        "book_weights_note": "fixed 74/26 selected in-sample; headline book is unlevered",
        "book": perf(book),
        "book_target_vol": perf(book_target),
        "book_walkforward": perf(book_wf),
        "book_walkforward_target_vol": perf(book_wf_target),
        "leverage_mean": round(float(scale.mean()), 3),
        "leverage_max": round(float(scale.max()), 3),
        "book_weights_walkforward_latest": {
            k: round(float(v), 3) for k, v in wf.iloc[-1].items()
        },
        "sixty40": perf(sixty40, rf=rf),
        "combo_60_40_plus_30_book": perf(combo, rf=rf),
        "xsmom_excluded": True,
        "xsmom_survivorship": survivorship_note(),
        "xsmom_turnover": xdiag["annual_turnover"],
        "deflated_sharpe_all_trials": dsr_all,
        "deflated_sharpe_final_variants": dsr_final,
        "overlay_dsr_all_trials": overlay_dsr,
        "overlay_bootstrap": overlay_boot,
        "benchmarks_monthly": {
            "spy": perf_m(spy_m, rf_monthly=rf_m),
            "sixty40_monthly_rebal": perf_m(sixty40_m, rf_monthly=rf_m),
            "note": "monthly-rebalanced 60/40 (SPY/IEF), no rebalancing costs",
        },
        "combo_60_40_plus_30_monthly_rebal": perf_m(combo_m, rf_monthly=rf_m),
        "deflated_sharpe_note": "deflated_sharpe_* is the sleeve book; "
                                "overlay_dsr_all_trials is the 60/40+30% claim",
        "trial_registry": TRIAL_REGISTRY,
        "excess_convention": EXCESS_CONVENTION,
    }
    _save_json("finalbook_metrics.json", res)
    _save_json("trials.json", {
        "registry": TRIAL_REGISTRY,
        "n_trials_all": sum(TRIAL_REGISTRY.values()),
        "n_trials_final_published": 2,
        "deflated_sharpe_all_trials": dsr_all,
        "deflated_sharpe_final_variants": dsr_final,
        "note": "DSR uses the daily Sharpe of the final fixed-weight book.",
    })
    return res


def run_cost_stress() -> dict:
    """Net performance at 5/10/25/50 bps per unit of turnover."""
    px = prices()
    spy, sixty40, rf = _benchmarks()
    out = {}
    for bps in (5.0, 10.0, 25.0, 50.0):
        trend, _ = trend_returns(px, cost_bps=bps)
        carry, _, _ = carry_returns(cost_bps=bps)
        df = pd.DataFrame({"trend": trend, "carry": carry}).dropna()
        book = fixed_book(df, {"trend": 0.74, "carry": 0.26})
        combo = (0.7 * sixty40 + 0.3 * book).dropna()
        out[str(int(bps))] = {
            "trend": perf(trend),
            "carry": perf(carry),
            "book": perf(book),
            "overlay_60_40_plus_30": perf(combo, rf=rf),
        }
    _save_json("cost_stress.json", out)
    return out


def run_all() -> dict:
    out = {}
    for name, fn in [
        ("momentum", run_momentum),
        ("variants", run_variants),
        ("riskalloc", run_riskalloc),
        ("final", run_final),
        ("carry", run_carry),
        ("combo", run_combo),
        ("book", run_book),
        ("harden", run_harden),
        ("tilt", run_tilt),
        ("sleeve", run_sleeve),
        ("finalbook", run_finalbook),
        ("cost_stress", run_cost_stress),
    ]:
        print(f"[inercia] {name} ...", flush=True)
        out[name] = fn()
    print("[inercia] done", flush=True)
    return out


STAGES = {
    "momentum": run_momentum,
    "variants": run_variants,
    "riskalloc": run_riskalloc,
    "final": run_final,
    "carry": run_carry,
    "combo": run_combo,
    "book": run_book,
    "harden": run_harden,
    "tilt": run_tilt,
    "sleeve": run_sleeve,
    "finalbook": run_finalbook,
    "cost_stress": run_cost_stress,
    "all": run_all,
}
