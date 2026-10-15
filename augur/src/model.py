"""model.py - walk-forward ML for next-day SPY direction (honest, no lookahead)."""
import os, json
import numpy as np, pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, accuracy_score

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(BASE, "data", "raw")
OUT = os.path.join(BASE, "output")
os.makedirs(OUT, exist_ok=True)

def load_price(t):
    d = pd.read_csv(os.path.join(RAW, "prices", f"{t}.csv"))
    dc = [c for c in d.columns if c.lower() == "date"][0]
    d[dc] = pd.to_datetime(d[dc]); d = d.set_index(dc).sort_index()
    return pd.to_numeric(d["Close"], errors="coerce").dropna()

def fred(sid):
    d = pd.read_csv(os.path.join(RAW, "fred", f"{sid}.csv")); d.columns = ["date", "value"]
    d["date"] = pd.to_datetime(d["date"]); d["value"] = pd.to_numeric(d["value"], errors="coerce")
    return d.dropna().set_index("date")["value"]

close = load_price("SPY")
d10, vix, oil = fred("DGS10"), fred("VIXCLS"), fred("DCOILWTICO")

df = pd.DataFrame({"close": close})
df["ret"] = close.pct_change()
for lag in [1, 2, 3, 5, 10, 20]:
    df[f"ret_lag{lag}"] = df["ret"].shift(lag)
for w in [5, 10, 20]:
    df[f"vol{w}"] = df["ret"].rolling(w).std()
    df[f"mom{w}"] = close.pct_change(w)
df["ma20_gap"] = close / close.rolling(20).mean() - 1
df["ma50_gap"] = close / close.rolling(50).mean() - 1
df["ma200_gap"] = close / close.rolling(200).mean() - 1
delta = close.diff()
up = delta.clip(lower=0).rolling(14).mean()
dn = (-delta.clip(upper=0)).rolling(14).mean()
df["rsi"] = 100 - 100 / (1 + up / dn)
df = df.join(d10.rename("d10")).join(vix.rename("vix")).join(oil.rename("oil"))
df["d10_chg"] = df["d10"].diff()
df["vix_chg"] = df["vix"].diff()
df["oil_ret"] = df["oil"].pct_change()
df = df.ffill()
df["target"] = (df["ret"].shift(-1) > 0).astype(int)
df["next_ret"] = df["ret"].shift(-1)
df["next_absret"] = df["ret"].shift(-1).abs()
df = df.dropna()

features = [c for c in df.columns if c not in ("close", "ret", "target", "next_ret", "next_absret")]
X = df[features].values; y = df["target"].values; n = len(df)

def walk_forward(make_model, scale=False):
    proba = np.full(n, np.nan); pred = np.full(n, np.nan)
    init = int(n * 0.5); step = 63; i = init
    while i < n:
        tr = slice(0, i); te = slice(i, min(i + step, n))
        Xtr, Xte = X[tr], X[te]
        if scale:
            sc = StandardScaler().fit(Xtr)
            Xtr, Xte = sc.transform(Xtr), sc.transform(Xte)
        m = make_model(); m.fit(Xtr, y[tr])
        proba[te] = m.predict_proba(Xte)[:, 1]
        pred[te] = (proba[te] > 0.5).astype(int)
        i += step
    return proba, pred

proba_gb, pred_gb = walk_forward(lambda: GradientBoostingClassifier(n_estimators=100, max_depth=3, learning_rate=0.05, random_state=0))
proba_lr, pred_lr = walk_forward(lambda: LogisticRegression(max_iter=1000), scale=True)

mask = ~np.isnan(pred_gb)
res = {}
for name, proba, pred in [("gradient_boosting", proba_gb, pred_gb), ("logistic", proba_lr, pred_lr)]:
    res[name] = {
        "accuracy": round(float(accuracy_score(y[mask], pred[mask])), 4),
        "auc": round(float(roc_auc_score(y[mask], proba[mask])), 4),
    }
base_rate = float(max(y[mask].mean(), 1 - y[mask].mean()))
res["baseline_majority_accuracy"] = round(base_rate, 4)
res["n_out_of_sample"] = int(mask.sum())
res["up_day_frequency"] = round(float(y[mask].mean()), 4)

oos = df[mask].copy()
oos["proba"] = proba_gb[mask]
oos["strat_ret"] = np.where(oos["proba"] > 0.5, oos["next_ret"], 0.0)
oos["always_long"] = oos["next_ret"]
def sharpe(r):
    return float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0
res["strategy_sharpe"] = round(sharpe(oos["strat_ret"]), 3)
res["buy_hold_sharpe"] = round(sharpe(oos["always_long"]), 3)
res["strategy_total_return"] = round(float((1 + oos["strat_ret"]).prod() - 1), 3)
res["buy_hold_total_return"] = round(float((1 + oos["always_long"]).prod() - 1), 3)

# volatility predictability (RQ3): next-day abs return vs features, correlation
res["vol_signal_corr"] = round(float(df["vol20"].corr(df["next_absret"])), 4)

fig, ax = plt.subplots(figsize=(11, 5.5))
ax.plot(oos.index, (1 + oos["strat_ret"]).cumprod(), label="Signal strategy (long/flat)", color="#8e44ad", lw=1.6)
ax.plot(oos.index, (1 + oos["always_long"]).cumprod(), label="Buy & hold", color="#2c3e50", lw=1.6)
ax.set_title("Out-of-sample: ML signal strategy vs buy & hold (SPY)")
ax.set_ylabel("growth of $1"); ax.legend()
fig.tight_layout(); fig.savefig(os.path.join(OUT, "01_strategy_vs_bh.png")); plt.close(fig)

fig, ax = plt.subplots(figsize=(9, 5))
ax.bar(["Majority\nbaseline", "Logistic", "Grad.\nboosting"], [base_rate, res["logistic"]["accuracy"], res["gradient_boosting"]["accuracy"]], color=["#95a5a6", "#2980b9", "#c0392b"])
ax.axhline(0.5, color="grey", ls="--", lw=1)
ax.set_ylabel("out-of-sample accuracy"); ax.set_ylim(0.45, 0.60)
ax.set_title("Directional accuracy vs the dumb baseline")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "02_accuracy.png")); plt.close(fig)

with open(os.path.join(OUT, "metrics.json"), "w") as f:
    json.dump(res, f, indent=2)
print(json.dumps(res, indent=2))
