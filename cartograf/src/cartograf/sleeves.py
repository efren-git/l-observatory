"""Sleeve construction: each published pattern, one faithful implementation."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .backtest import (
    month_end_dates, scale_weights_to_target, turnover_annual, weights_to_returns,
)
from .config import COST, COST_VOL, START, TARGET
from .data import cboe_term, daily_rate, dividends, fred, monthly_rate_lagged, prices
from .stats import vol_target

try:
    from fetch_data import UNIVERSE
except Exception:  # pragma: no cover - only when imported outside src/
    UNIVERSE = {}


def universe_setup(start: str = START):
    px = prices()
    tradable = [t for t in UNIVERSE if t in px.columns]
    R = px[tradable].pct_change().fillna(0.0)
    me = month_end_dates(R.index)
    me = me[me >= pd.Timestamp(start)]
    groups = group_map(tradable)
    return px, R, tradable, me, groups


def group_map(cols):
    g = {}
    for t, grp in UNIVERSE.items():
        if t in cols:
            g.setdefault(grp, []).append(t)
    return {k: v for k, v in g.items() if len(v) >= 2}


def live_mask(px: pd.DataFrame, dates, cols) -> pd.DataFrame:
    """Boolean [dates x cols]: the fund has a valid price on or before each date.

    The first valid observation is the listing date. A name is never scored or
    weighted before it existed. Signal lookbacks (252 days for momentum, 1260
    for value) remain NaN until computable; this mask only removes the phantom
    cross-section that a zero-filled return panel would otherwise create.
    """
    cols = list(cols)
    seen = px.reindex(columns=cols).notna().cumsum()
    return seen.reindex(pd.DatetimeIndex(dates), method="ffill").fillna(0.0).gt(0)


def group_z(df, groups):
    out = pd.DataFrame(index=df.index, columns=df.columns, dtype=float)
    for _, cols in groups.items():
        sub = df[cols]
        mu, sd = sub.mean(axis=1), sub.std(axis=1)
        out[cols] = sub.sub(mu, axis=0).div(sd.replace(0, np.nan), axis=0)
    return out.fillna(0.0)


def xs_targets(score, me, groups):
    """Cross-sectional z-score weights, gross 1 inside each group, then equal groups.

    Only names that are live at the rebalance enter the cross-section. This
    matters most where a score is built from a fillna(0) return panel: a fund
    that has not listed must not be ranked, normalised against, or traded.
    """
    live = live_mask(prices(), score.index, score.columns)
    score = score.where(live.reindex(index=score.index, columns=score.columns).fillna(False),
                        np.nan)
    z = group_z(score, groups)
    w = z.copy()
    for _, cols in groups.items():
        denom = w[cols].abs().sum(axis=1).replace(0, np.nan)
        w[cols] = w[cols].div(denom, axis=0)
    w = w / max(len(groups), 1)
    w = w.reindex(me).fillna(0.0)
    return w.where(live.reindex(index=me, columns=w.columns).fillna(False), 0.0)


def _build(rows, me, cols, R, cost=COST):
    w = pd.DataFrame(rows, index=me).reindex(columns=cols).fillna(0.0)
    w = w.where(live_mask(prices(), me, cols), 0.0)
    w = scale_weights_to_target(w, R, TARGET)
    net, to, _ = weights_to_returns(R, w, cost)
    return net, turnover_annual(to, len(R)), w


def trend(px, R, tradable, me, groups):
    sigs = [np.sign(px / px.shift(h) - 1) for h in (21, 63, 126, 252)]
    sig = sum(sigs) / 4.0
    vol = R.rolling(63).std() * np.sqrt(252)
    rows = (sig * (TARGET / vol.clip(lower=0.05))).reindex(me).fillna(0.0)
    net, to, _ = _build(rows, me, tradable, R, COST)
    return net, to


def xsmom(px, R, tradable, me, groups):
    mom = px.shift(21) / px.shift(252) - 1
    rows = xs_targets(mom, me, groups)
    net, to, _ = _build(rows, me, tradable, R, COST)
    return net, to


def value(px, R, tradable, me, groups):
    val = -(px / px.shift(1260) - 1)
    rows = xs_targets(val, me, groups)
    net, to, _ = _build(rows, me, tradable, R, COST)
    return net, to


def bab(R, tradable, me, groups):
    eq = [t for t in tradable if UNIVERSE.get(t, "").startswith("equity")]
    spy = R["SPY"]
    beta = pd.DataFrame({t: R[t].rolling(252).cov(spy) / spy.rolling(252).var()
                         for t in eq})
    score = -(beta.sub(1.0))
    score = score.div((R[eq].rolling(63).std() * np.sqrt(252)).clip(lower=0.05))
    # R is zero-filled before an ETF lists, so beta=0 and vol=0 produce a huge
    # phantom score. Mask the name until it has a real 252-day history too.
    score = score.where(live_mask(prices(), score.index, eq), np.nan)
    rows = score.div(score.abs().sum(axis=1).replace(0, np.nan), axis=0)
    net, to, _ = _build(rows.reindex(me).fillna(0.0), me, tradable, R, COST)
    return net, to


def vrp_svxy(px, R, tradable, me):
    """Legacy proxy: long SVXY when the VIX curve is in contango."""
    contango = (px["^VIX3M"] / px["^VIX"]) > 1.02
    rows = pd.DataFrame(0.0, index=me, columns=tradable)
    rows["SVXY"] = contango.reindex(me).fillna(False).astype(float)
    net, to, _ = _build(rows, me, tradable, R, COST_VOL)
    return net, to, float(contango.reindex(me).mean())


def vrp_monthly():
    """Proper VRP: implied minus realized variance, monthly, with a contango gate.

    Returns a monthly frame with A (always-on), B (gated), C (old SVXY proxy).
    """
    px = prices()
    term = cboe_term()
    spy = px["SPY"]
    logret = np.log(spy / spy.shift(1)).dropna()
    me = month_end_dates(spy.index)

    per = logret.index.to_period("M")
    rv = logret.groupby(per).apply(lambda s: float(np.sqrt((s ** 2).mean() * 252)) * 100)
    rv.index = rv.index.to_timestamp(how="end").normalize()

    vix = term["vix"].reindex(spy.index).ffill()
    vix3m = term["vix3m"].reindex(spy.index).ffill()
    df = pd.DataFrame({
        "K": vix.reindex(me).shift(1),
        "K3": vix3m.reindex(me).shift(1),
        "RV": rv.reindex(me),
    }).dropna(subset=["K", "RV"])
    df["pnl"] = (df["K"] ** 2 - df["RV"] ** 2) / (2 * df["K"])
    df["contango"] = df["K3"].notna() & (df["K"] < df["K3"])

    vol_ann = df["pnl"].rolling(24, min_periods=24).std() * np.sqrt(12)
    # P&L is in vol points, so scale is not a dimensionless return multiplier.
    # Leave the first 24 months as NaN and drop them, rather than filling 1.0
    # (which would turn a 4-vol-point month into a 400% "return").
    df["scale"] = (TARGET / vol_ann.replace(0, np.nan)).clip(upper=4.0).shift(1)
    on_a = df["scale"].notna() & (df["scale"] > 0)
    on_b = on_a & df["contango"]
    df["A"] = df["pnl"] * df["scale"] - (5.0 / 1e4) * on_a.astype(float)
    df["B"] = df["pnl"].where(df["contango"], 0.0) * df["scale"] - (5.0 / 1e4) * on_b.astype(float)
    # Before VIX3M exists there is no gate and no B strategy. Keep it NaN, not 0:
    # zeros would silently enter the performance stats and the core book.
    df.loc[df["K3"].isna(), "B"] = np.nan

    if "SVXY" in px.columns:
        sv = px["SVXY"].resample("ME").last().pct_change()
        sv = sv.reindex(df.index)
        # Do not invest until the trailing vol estimate exists. Filling 1.0 here
        # would hold raw SVXY (realised vol ~50%) for the first 24 months, which
        # contaminates the whole C series and makes the proxy look far better than
        # it is. The old code used 0.0; keep that convention.
        sv_scale = (TARGET / (sv.rolling(24, min_periods=24).std() * np.sqrt(12))
                    .replace(0, np.nan)).clip(upper=4.0).shift(1).fillna(0.0)
        df["C"] = sv * sv_scale - (5.0 / 1e4) * (sv_scale > 0).astype(float)
        df.loc[sv.isna(), "C"] = np.nan
    else:
        df["C"] = np.nan
    return df


def monthly_to_daily(monthly: pd.Series, daily_index: pd.DatetimeIndex) -> pd.Series:
    """Spread each monthly return evenly across that month's trading days.

    This preserves the monthly sum and avoids a single-day jump when a monthly
    sleeve is combined with daily sleeves. It is an approximation, stated in the
    README; the monthly VRP result itself is reported separately.
    """
    m = pd.Series(monthly).dropna()
    out = pd.Series(np.nan, index=daily_index, dtype=float)
    per = daily_index.to_period("M")
    for ts, v in m.items():
        mask = per == ts.to_period("M")
        n = int(mask.sum())
        if n:
            out[mask] = float(v) / n
    return out


FX_MAP = {"FXE": "fx_eur", "FXY": "fx_jpy", "FXB": "fx_gbp",
          "FXA": "fx_aud", "FXC": "fx_cad", "FXF": "fx_chf"}
BOND_TENOR = {"SHY": "dgs2", "IEF": "dgs7", "TLT": "dgs30"}
EQ_CARRY = ["SPY", "QQQ", "IWM", "EFA", "EEM", "IWD", "IWF", "USMV", "SPLV",
            "QUAL", "MTUM", "SPHB", "VNQ", "RWX"]


def carry_inputs():
    """Bond/equity/FX carry signals and the returns each leg is paid on.

    FX fix: currency ETFs track spot closely (the diagnostic shows FXE - spot is
    about 2.6 bp/month), so the foreign deposit rate is missing from the ETF
    return. We add the publication-lagged foreign rate and subtract the US rate;
    the old code subtracted the US rate without adding the foreign rate.
    """
    px = prices()
    fr = fred()
    div = dividends()
    R = px.pct_change().fillna(0.0)
    me = month_end_dates(R.index)
    me = me[me >= pd.Timestamp("2007-01-01")]
    frd = fr.reindex(R.index).ffill()

    div_m = div.resample("ME").sum()
    trail = div_m.rolling(12).sum()
    eq_cols = [c for c in EQ_CARRY if c in px.columns]
    dyield = (trail.reindex(me, method="ffill")
              .div(px[eq_cols].reindex(me).replace(0, np.nan)) * 100.0)

    bond_cols = [c for c in BOND_TENOR if c in px.columns]
    fx_cols = [c for c in FX_MAP if c in px.columns]
    cash = frd["dgs3mo"].reindex(me)

    # Publication-safe monthly FX rates, aligned to each day.
    fxd = {c: monthly_rate_lagged(FX_MAP[c], R.index) for c in fx_cols}
    usd = monthly_rate_lagged("fx_usd", R.index)

    # Rates exist before the ETF that carries them; the instrument does not.
    live_b = live_mask(px, me, bond_cols)
    live_e = live_mask(px, me, eq_cols)
    live_f = live_mask(px, me, fx_cols)

    wb, we, wf = [], [], []
    for d in me:
        c = cash.loc[d]
        yb = {t: frd[BOND_TENOR[t]].loc[d] - c for t in bond_cols}
        wb.append(_z_weights(yb, bond_cols, live_b.loc[d]))
        ye = (dyield.loc[d] - c).to_dict()
        we.append(_z_weights(ye, eq_cols, live_e.loc[d]))
        yf = {t: fxd[t].loc[d] - usd.loc[d] for t in fx_cols}
        wf.append(_z_weights(yf, fx_cols, live_f.loc[d]))

    # Excess return of each FX leg: spot ETF return + foreign rate - US rate.
    Rfx = R[fx_cols].copy()
    for t in fx_cols:
        Rfx[t] = Rfx[t] + (fxd[t] - usd) / 100.0 / 252.0

    return dict(px=px, R=R, me=me, frd=frd, wb=wb, we=we, wf=wf,
                bond_cols=bond_cols, eq_cols=eq_cols, fx_cols=fx_cols,
                Rfx=Rfx, fxd=fxd, usd=usd)


def _z_weights(score, cols, live_row=None):
    s = pd.Series(score).reindex(cols)
    if live_row is not None:
        s = s.where(pd.Series(live_row).reindex(cols).fillna(False).astype(bool))
    s = s.dropna()
    if len(s) < 2:
        return pd.Series(0.0, index=cols)
    z = s - s.mean()
    denom = float(z.abs().sum())
    if denom <= 0:
        return pd.Series(0.0, index=cols)
    return (z / denom).reindex(cols).fillna(0.0)


def _carry_leg(rows, cols, rets, me, cost=COST):
    w = pd.DataFrame(rows, index=me).reindex(columns=cols).fillna(0.0)
    w = scale_weights_to_target(w, rets, TARGET)
    net, to, _ = weights_to_returns(rets, w, cost)
    return net, turnover_annual(to, len(rets))


def carry_legs():
    inp = carry_inputs()
    bond_ret, bond_to = _carry_leg(inp["wb"], inp["bond_cols"], inp["R"], inp["me"])
    eq_ret, eq_to = _carry_leg(inp["we"], inp["eq_cols"], inp["R"], inp["me"])
    fx_ret, fx_to = _carry_leg(inp["wf"], inp["fx_cols"], inp["Rfx"], inp["me"])

    combined = pd.DataFrame({"bond_carry": bond_ret, "equity_carry": eq_ret,
                             "fx_carry": fx_ret})
    combined = combined.loc[combined.index >= pd.Timestamp("2007-01-01")]
    mix = combined.mean(axis=1)
    carry_book = vol_target(mix, TARGET)[0]
    return dict(combined=combined, mix=mix, carry_book=carry_book,
                bond=bond_ret, equity=eq_ret, fx=fx_ret,
                turnover={"bond": bond_to, "equity": eq_to, "fx": fx_to},
                inputs=inp)


def network_sleeves():
    px, R, tradable, me, groups = universe_setup()
    cols = [t for t in tradable if UNIVERSE.get(t) != "vol"]
    px = px[cols]
    R = R[cols]
    wk = px.resample("W-FRI").last().pct_change()
    trend_sig = sum(np.sign(px / px.shift(h) - 1) for h in (21, 63, 126, 252)) / 4.0
    vol = R.rolling(63).std() * np.sqrt(252)
    volm = vol.reindex(me)

    live = live_mask(px, me, cols)
    own_rows, net_rows, comb_rows = [], [], []
    edge_stats = []
    for d in me:
        live_cols = [c for c in cols if bool(live.loc[d, c])]
        t = trend_sig.loc[d].reindex(live_cols)
        hist = wk.loc[:d, live_cols].tail(157)
        if len(hist) >= 60 and len(live_cols) >= 2:
            Z = ((hist - hist.mean()) / hist.std()).fillna(0.0)
            A = Z.values
            M = (A[:-1].T @ A[1:]) / (len(A) - 1)
            M = np.nan_to_num(M)
            np.fill_diagonal(M, 0.0)
        else:
            M = np.zeros((len(live_cols), len(live_cols)))
        lead = pd.DataFrame(M, index=live_cols, columns=live_cols)
        nt = pd.Series(0.0, index=cols)
        kept = []
        for ci in live_cols:
            col = lead[ci]
            col = col[col > 0].nlargest(5)
            if len(col):
                w = col / col.sum()
                nt[ci] = float((w * t.reindex(col.index).fillna(0.0)).sum())
                kept.append(float(col.mean()))
        own = trend_sig.loc[d].reindex(cols).where(live.loc[d], 0.0).fillna(0.0)
        own_rows.append(own)
        net_rows.append(nt)
        comb_rows.append(0.5 * own + 0.5 * nt)
        if kept:
            edge_stats.append(float(np.mean(kept)))

    def build(rows):
        w = pd.DataFrame(rows, index=me).reindex(columns=cols).fillna(0.0)
        w = w.where(live, 0.0)
        w = w * (TARGET / volm.reindex(columns=cols).clip(lower=0.05)).fillna(0.0)
        w = scale_weights_to_target(w, R, TARGET)
        net, to, _ = weights_to_returns(R, w, COST)
        return net, turnover_annual(to, len(R))

    own_ret, own_to = build(own_rows)
    net_ret, net_to = build(net_rows)
    comb_ret, comb_to = build(comb_rows)
    # The target book only starts in 2008. Without this slice, the pre-2008
    # zero rows enter perf() and make the sleeve look longer and calmer.
    start = me[0]
    own_ret, net_ret, comb_ret = own_ret.loc[start:], net_ret.loc[start:], comb_ret.loc[start:]
    return dict(own=own_ret, network=net_ret, combined=comb_ret,
                turnover={"own": own_to, "net": net_to, "comb": comb_to},
                avg_lead_corr=round(float(np.mean(edge_stats)), 4) if edge_stats else None,
                me=me, R=R)
