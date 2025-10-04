# src/train_ranker.py  — LambdaMART training (CLI-enabled)
import json
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime
from lightgbm import LGBMRanker, early_stopping, log_evaluation

# -------------------------
# Paths (default)
# -------------------------
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "backend" / "data"
MODELS_DIR = ROOT / "backend" / "app" / "models"
OUTPUTS_DIR = ROOT / "backend" / "outputs"
MODELS_DIR.mkdir(exist_ok=True)
OUTPUTS_DIR.mkdir(exist_ok=True)

# -------------------------
# Load data
# -------------------------
users = pd.read_csv(DATA_DIR / "users.csv")        # training-ready (no 'name')
plans = pd.read_csv(DATA_DIR / "plans.csv")
inter = pd.read_csv(DATA_DIR / "interactions.csv")

# -------------------------
# Normalize column names
# -------------------------
# Rename planid to plan_id for consistency
inter = inter.rename(columns={"planid": "plan_id"})
plans = plans.rename(columns={"planid": "plan_id"})

# -------------------------
# Join to interaction rows
# -------------------------
df = inter.merge(users, on="user_id", how="left").merge(
    plans, on="plan_id", how="left")

# -------------------------
# Clean & basic feature engineering
# -------------------------
# Ensure numeric dtypes where expected
numeric_cols = [
    "age", "dependents", "risk_score", "past_claims_count", "past_claims_amount", "income",
    "premium", "deductible", "copay", "coverage_amount", "network_size",
    "claim_rejection_rate", "waiting_period_days"
]
for c in numeric_cols:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

# Normalize small categoricals
df["coverage_preference"] = (
    df.get("coverage_preference", "balanced")
      .astype(str).str.lower().str.replace(" ", "_", regex=False)
)
df["health_status"] = df.get("health_status", "good").astype(str).str.lower()

# Engineered numerics
income_safe = df["income"].replace([np.inf, -np.inf], np.nan)
income_safe = income_safe.where(income_safe > 0, np.nan)
income_fallback = float(np.nanmedian(income_safe)) if np.isfinite(
    np.nanmedian(income_safe)) else 1.0
df["premium_income_ratio"] = df["premium"] / \
    income_safe.fillna(income_fallback)

df["log_income"] = np.log1p(df["income"].fillna(0))
df["log_past_claims_amount"] = np.log1p(df["past_claims_amount"].fillna(0))
df["addons_count"] = df.get("addons", "").fillna("").apply(
    lambda s: 0 if str(s).strip() == "" else len(
        [x for x in str(s).split(";") if x.strip()])
)
df["cond_count"] = df.get("chronic_conditions", "none").fillna("none").apply(
    lambda s: 0 if s in ["", "none"] else len(
        [x for x in str(s).split(";") if x.strip()])
)

# Preference match: provider inside preferred_providers (row-wise, null-safe)


def provider_match_row(r):
    prefs = [p.strip().lower() for p in str(
        r.get("preferred_providers", "")).split(";") if p.strip()]
    prov = str(r.get("provider", "")).strip().lower()
    return int(prov in prefs) if prov else 0


df["preferred_providers"] = df.get("preferred_providers", "").fillna("")
df["provider"] = df.get("provider", "").fillna("")
df["provider_match"] = df.apply(provider_match_row, axis=1)

# Map categoricals safely (fillna BEFORE astype(int) to avoid IntCastingNaNError)
pref_map = {"low_premium": 0, "balanced": 1, "high_coverage": 2}
df["pref_code"] = df["coverage_preference"].map(pref_map).fillna(1).astype(int)

health_map = {"excellent": 3, "good": 2, "fair": 1, "poor": 0}
df["health_code"] = df["health_status"].map(health_map).fillna(1).astype(int)

# Final feature list
FEATURES = [
    "age", "dependents", "risk_score", "past_claims_count", "log_past_claims_amount", "log_income",
    "premium", "deductible", "copay", "coverage_amount", "network_size", "claim_rejection_rate",
    "waiting_period_days", "addons_count", "cond_count", "premium_income_ratio", "provider_match",
    "pref_code", "health_code"
]

# Replace any residual NaN/Inf in features
df[FEATURES] = df[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)

# Label: chosen (1/0). If all zeros in a session, keep as-is (LTR can still learn from pairwise).
df["label"] = df.get("chosen", 0).fillna(0).astype(int)

# -------------------------
# Train/valid split by session
# -------------------------
df = df.sort_values(["session_id", "shown_rank"]).reset_index(drop=True)
sessions = df["session_id"].dropna().unique()
rng = np.random.default_rng(42)
rng.shuffle(sessions)

cut = int(0.8 * len(sessions))
train_sess = set(sessions[:cut])
valid_sess = set(sessions[cut:])

train_df = df[df.session_id.isin(train_sess)].copy()
valid_df = df[df.session_id.isin(valid_sess)].copy()

X_train = train_df[FEATURES].values
y_train = train_df["label"].values
X_valid = valid_df[FEATURES].values
y_valid = valid_df["label"].values

# group sizes (counts per session) — arrays of ints in session order
group_train = train_df.groupby("session_id").size().to_numpy()
group_valid = valid_df.groupby("session_id").size().to_numpy()

# -------------------------
# Train LambdaMART
# -------------------------
ranker = LGBMRanker(
    objective="lambdarank",
    metric="ndcg",
    learning_rate=0.05,
    n_estimators=800,
    num_leaves=31,
    min_data_in_leaf=50,
    feature_fraction=0.8,
    reg_lambda=2.0,
    random_state=42,
)

ranker.fit(
    X_train, y_train,
    group=group_train,
    eval_set=[(X_valid, y_valid)],
    eval_group=[group_valid],
    eval_at=[3, 5],
    callbacks=[log_evaluation(period=50), early_stopping(stopping_rounds=50)],
)

# -------------------------
# Save model + small preview
# -------------------------
model_out = MODELS_DIR / "ltr_model_v1.txt"
ranker.booster_.save_model(str(model_out))
# also copy as current model for app inference
try:
    (MODELS_DIR / "ltr_model.txt").write_text(model_out.read_text())
except Exception:
    pass

# Preview: top-3 for one validation session
report = {}
if len(valid_df):
    sample_sess = valid_df["session_id"].iloc[0]
    mini = valid_df[valid_df.session_id == sample_sess].copy()
    mini["score"] = ranker.predict(mini[FEATURES].values)
    mini = mini.sort_values("score", ascending=False)
    mini_out = mini[["session_id", "user_id", "plan_id",
                     "score", "shown_rank", "clicked", "chosen"]]
    mini_out.to_csv(OUTPUTS_DIR / "sample_ranking.csv", index=False)

# Save metadata and train report
metadata = {
    "model_path": str(model_out),
    "saved_at": datetime.utcnow().isoformat()+"Z",
    "features": FEATURES,
    "params": {
        "objective": "lambdarank", "metric": "ndcg", "learning_rate": 0.05,
        "n_estimators": ranker.n_estimators, "num_leaves": ranker.num_leaves,
    }
}
(MODELS_DIR / "metadata_ltr_model_v1.json").write_text(json.dumps(metadata, indent=2))
(OUTPUTS_DIR / "train_report.json").write_text(json.dumps(report, indent=2))

print("✅ Trained! Model ->", model_out)
print("🔎 Sample ranking (one session) -> outputs/sample_ranking.csv")
