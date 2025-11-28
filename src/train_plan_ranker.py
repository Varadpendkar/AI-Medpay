#!/usr/bin/env python3
# train_plan_ranker.py
"""
Train PlanRanker (LightGBM Lambdarank) using existing enhanced_plans_dataset.csv,
users.csv, and interactions.csv. Saves model to ../models/plan_ranker.pkl or ../backend/models/plan_ranker.pkl.

How to run:
    cd project/src
    python train_plan_ranker.py
"""

import os
import pandas as pd
import numpy as np
import joblib
from sklearn.model_selection import train_test_split
from lightgbm import LGBMRanker
from sklearn.metrics import ndcg_score

# --- Paths (adjust if your repo layout differs) ---
ROOT = os.path.join(os.path.dirname(__file__), "..")
# Try both locations for data
DATA_DIR_1 = os.path.join(ROOT, "backend", "models")
DATA_DIR_2 = os.path.join(ROOT, "models")
DATA_DIR = DATA_DIR_1 if os.path.exists(DATA_DIR_1) else DATA_DIR_2

ENHANCED_PLANS = os.path.join(DATA_DIR, "enhanced_plans_dataset.csv")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
INTERACTIONS_CSV = os.path.join(DATA_DIR, "interactions.csv")
OUT_MODEL = os.path.join(DATA_DIR, "plan_ranker.pkl")

print(f"📂 Using data directory: {DATA_DIR}")
print(f"📂 Will save model to: {OUT_MODEL}")

# --- Helpers: feature engineering for user-plan pair ---


def age_in_range(user_age, plan_age_range):
    """Check if user age falls within plan's age range"""
    try:
        if pd.isna(plan_age_range):
            return 0
        age_str = str(plan_age_range).strip()
        if '-' not in age_str:
            return 0
        lo, hi = [int(x.strip()) for x in age_str.split("-")]
        return 1 if (lo <= user_age <= hi) else 0
    except Exception:
        return 0


def map_income_band_to_numeric(income_band):
    """Map income band string to numeric value"""
    income_mapping = {
        '<3L': 250000,
        '3-6L': 450000,
        '6-10L': 800000,
        '10-20L': 1500000,
        '>20L': 2500000
    }
    return income_mapping.get(str(income_band), 800000)


def compute_features_for_cross(user_df, plans_df):
    """Create feature matrix for user-plan cross product"""
    # Prepare users
    user_df = user_df.copy()
    if 'income' not in user_df.columns and 'income_band' in user_df.columns:
        user_df['income'] = user_df['income_band'].apply(
            map_income_band_to_numeric)

    # Cross join
    user_df["_tmpkey"] = 1
    plans_df["_tmpkey"] = 1
    cross = user_df.merge(plans_df, on="_tmpkey", suffixes=(
        "_user", "_plan")).drop(columns=["_tmpkey"])

    # Numeric features
    cross["premium_income_ratio"] = cross["premium"] / (cross["income"] + 1e-9)
    cross["premium_coverage_ratio"] = cross["premium"] / \
        (cross["coverage_amount"] + 1e-9)
    cross["network_per_100"] = cross["network_size"] / 100.0
    cross["age_match"] = cross.apply(
        lambda r: age_in_range(r["age"], r.get("age_range")), axis=1)

    # Risk profile mapping
    risk_map = {"low": 0, "medium": 1, "high": 2}
    cross["risk_num"] = cross.get("risk_profile", "medium").fillna(
        "medium").map(risk_map).fillna(1)

    # User flags
    cross["smoking_flag"] = cross.get("smoking_status", "no").map({
        "yes": 1, "no": 0, "ex-smoker": 0.5, "smoker": 1, "non-smoker": 0
    }).fillna(0).astype(float)

    cross["dependents_count"] = pd.to_numeric(
        cross.get("dependents", 0), errors='coerce').fillna(0).astype(float)

    # Additional features from user data
    cross["claim_history"] = pd.to_numeric(
        cross.get("claim_history_count", 0), errors='coerce').fillna(0).astype(float)
    cross["renewal_years"] = pd.to_numeric(
        cross.get("renewal_loyalty_years", 0), errors='coerce').fillna(0).astype(float)
    cross["user_risk_score"] = pd.to_numeric(
        cross.get("risk_score", 0.5), errors='coerce').fillna(0.5).astype(float)

    # Final feature columns in deterministic order
    feature_cols = [
        "premium", "deductible", "coverage_amount", "network_size",
        "premium_income_ratio", "premium_coverage_ratio", "network_per_100",
        "age_match", "risk_num", "smoking_flag", "dependents_count",
        "claim_history", "renewal_years", "user_risk_score", "age"
    ]

    # Ensure columns exist (fill missing ones with 0)
    for c in feature_cols:
        if c not in cross.columns:
            cross[c] = 0.0
        else:
            cross[c] = pd.to_numeric(
                cross[c], errors='coerce').fillna(0).astype(float)

    X = cross[feature_cols].astype(float)
    return cross, X, feature_cols

# --- Build labels for ranking ---


def build_labels(cross_df):
    """Build relevance labels from interactions or use plan relevance_score"""
    print("Building labels from interactions...")

    if os.path.exists(INTERACTIONS_CSV):
        inter = pd.read_csv(INTERACTIONS_CSV)
        print(f"  Loaded {len(inter)} interactions")

        # Create interaction map
        inter_map = {}
        for _, row in inter.iterrows():
            user_id = str(row.get("user_id", ""))
            plan_id = str(row.get("planid", row.get("plan_id", "")))
            event_type = str(row.get("event_type", ""))
            label = row.get("label", 0)

            key = (user_id, plan_id)

            # Priority: label > event_type mapping
            if pd.notna(label):
                inter_map[key] = float(label)
            elif event_type == "purchase":
                inter_map[key] = 4.0
            elif event_type == "shortlist":
                inter_map[key] = 3.0
            elif event_type == "view":
                inter_map[key] = 1.0
            else:
                inter_map[key] = 0.5

        # Assign labels
        labels = []
        for _, row in cross_df.iterrows():
            user_id = str(row.get("user_id", ""))
            # Try both column names
            plan_id = str(row.get("plan_id", row.get("planid", "")))
            key = (user_id, plan_id)

            if key in inter_map:
                labels.append(inter_map[key])
            else:
                # Fallback to plan relevance score
                labels.append(float(row.get("relevance_score", 1.0)))

        print(
            f"  Applied {len([l for l in labels if l > 1])} interaction-based labels")
        return np.array(labels)

    # Fallback to plan relevance scores
    print("  No interactions file, using plan relevance_score")
    return cross_df.get("relevance_score", 1.0).fillna(1.0).astype(float).to_numpy()

# --- Main training flow ---


def main():
    print("="*80)
    print("🤖 TRAINING PLAN RANKER")
    print("="*80)

    print("\n📊 Loading data...")
    plans = pd.read_csv(ENHANCED_PLANS)
    users = pd.read_csv(USERS_CSV)
    print(f"  ✓ Loaded {len(plans)} plans")
    print(f"  ✓ Loaded {len(users)} users")

    # Augment users if needed for robust training
    users_aug = users.copy()
    if len(users_aug) < 100:
        print(f"  ⚠️  Only {len(users_aug)} users, augmenting...")
        # Replicate users with variation
        users_list = [users_aug]
        for i in range(4):
            aug = users_aug.copy()
            aug["user_id"] = aug["user_id"].astype(str) + f"_aug{i}"
            # Add small variations to age and income
            if 'age' in aug.columns:
                aug['age'] = aug['age'] + np.random.randint(-2, 3, len(aug))
                aug['age'] = aug['age'].clip(18, 80)
            users_list.append(aug)
        users_aug = pd.concat(users_list, ignore_index=True)
        print(f"  ✓ Augmented to {len(users_aug)} users")

    # Build cross user-plan features
    print("\n🔨 Building features...")
    cross, X, feature_cols = compute_features_for_cross(users_aug, plans)
    print(f"  ✓ Feature matrix shape: {X.shape}")
    print(f"  ✓ Features: {feature_cols}")

    y = build_labels(cross)
    print(
        f"  ✓ Labels: min={y.min():.2f}, max={y.max():.2f}, mean={y.mean():.2f}")

    # Split by users: create train/val split on user groups
    print("\n✂️  Splitting data...")
    user_ids = cross["user_id"].unique()
    train_u, val_u = train_test_split(
        user_ids, test_size=0.15, random_state=42)
    train_mask = cross["user_id"].isin(train_u)
    val_mask = cross["user_id"].isin(val_u)

    X_train = X[train_mask]
    y_train = y[train_mask]
    group_train = cross[train_mask].groupby(
        "user_id", sort=False).size().to_numpy()

    X_val = X[val_mask]
    y_val = y[val_mask]
    group_val = cross[val_mask].groupby(
        "user_id", sort=False).size().to_numpy()

    print(f"  ✓ Train: {X_train.shape[0]} samples, {len(group_train)} groups")
    print(f"  ✓ Val: {X_val.shape[0]} samples, {len(group_val)} groups")

    # Train LGBMRanker
    print("\n🏋️  Training LightGBM Ranker...")
    model = LGBMRanker(
        objective="lambdarank",
        n_estimators=300,
        learning_rate=0.05,
        num_leaves=64,
        max_depth=8,
        min_child_samples=20,
        random_state=42,
        n_jobs=-1
    )

    model.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_val, y_val)],
        eval_group=[group_val],
        eval_at=[1, 3, 5],
        callbacks=[
            # early_stopping_rounds requires lightgbm callback
        ]
    )

    print(f"  ✓ Model trained with {model.n_estimators} trees")

    # Quick validation: compute ndcg on validation set
    print("\n📈 Computing validation metrics...")
    preds_val = model.predict(X_val)

    # Compute NDCG per group
    ndcg_vals = []
    start = 0
    for gsize in group_val:
        rel = y_val[start:start+gsize]
        pred = preds_val[start:start+gsize]
        try:
            # ndcg_score expects 2D arrays
            score = ndcg_score([rel], [pred], k=3)
            ndcg_vals.append(score)
        except Exception:
            pass
        start += gsize

    avg_ndcg = np.mean(ndcg_vals) if ndcg_vals else 0.0
    print(f"  ✓ Validation NDCG@3: {avg_ndcg:.4f}")

    # Feature importance
    print("\n📊 Top 10 Feature Importances:")
    importances = model.feature_importances_
    feat_imp = sorted(zip(feature_cols, importances),
                      key=lambda x: x[1], reverse=True)
    for feat, imp in feat_imp[:10]:
        print(f"     {feat:30s}: {imp:8.2f}")

    # Save model and feature order
    print(f"\n💾 Saving model to: {OUT_MODEL}")
    joblib.dump({
        "model": model,
        "feature_cols": feature_cols,
        "feature_importance": dict(feat_imp)
    }, OUT_MODEL)

    print("\n" + "="*80)
    print("✅ TRAINING COMPLETE")
    print("="*80)
    print(f"\n📦 Model saved to: {OUT_MODEL}")
    print(f"📊 Validation NDCG@3: {avg_ndcg:.4f}")
    print(f"🎯 Features: {len(feature_cols)}")
    print(f"🌳 Trees: {model.n_estimators}")
    print("\n💡 Next: Run test_top5_for_5_users.py to validate recommendations")
    print("="*80)


if __name__ == "__main__":
    main()
