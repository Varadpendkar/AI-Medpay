#!/usr/bin/env python3
"""
train_plan_ranker_v2.py - Feature-based personalized ranking

Uses synthetic labels based on user-plan fit rather than mismatched historical interactions.
This creates actual personalization by rewarding age-appropriate, affordable, risk-aligned plans.
"""

import os
import pandas as pd
import numpy as np
from lightgbm import LGBMRanker
import joblib

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_DIR_1 = os.path.join(ROOT, "backend", "models")
DATA_DIR_2 = os.path.join(ROOT, "models")
DATA_DIR = DATA_DIR_1 if os.path.exists(DATA_DIR_1) else DATA_DIR_2

ENHANCED_PLANS = os.path.join(DATA_DIR, "enhanced_plans_dataset.csv")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
INTERACTIONS_CSV = os.path.join(DATA_DIR, "interactions.csv")
MODEL_PATH = os.path.join(DATA_DIR, "plan_ranker.pkl")

print(f"📂 Using data directory: {DATA_DIR}")
print(f"📂 Will save model to: {MODEL_PATH}")


def age_in_range(user_age, plan_age_range):
    """Check if user age falls within plan age range"""
    try:
        if pd.isna(plan_age_range):
            return 0
        age_str = str(plan_age_range).strip()
        if '-' not in age_str:
            return 0
        parts = [int(x.strip()) for x in age_str.split("-")]
        if len(parts) == 2:
            lo, hi = parts
            return 1 if (lo <= user_age <= hi) else 0
    except Exception:
        pass
    return 0


def map_income_band_to_numeric(income_band):
    """Convert income band to numeric value"""
    mapping = {
        '<3L': 250000,
        '3-6L': 450000,
        '6-10L': 800000,
        '10-20L': 1500000,
        '>20L': 2500000
    }
    return mapping.get(str(income_band), 800000)


def compute_features_and_labels(users_df, plans_df):
    """
    Build feature matrix and synthetic personalized labels.

    Key idea: Label = base_relevance + user_fit_bonus
    where user_fit_bonus rewards:
      - Age-appropriate plans
      - Affordable plans (premium < 5% income)
      - Risk-aligned plans (smoker → high risk, non-smoker → low risk)
      - Family-friendly plans (dependents → large network)
    """

    # Cross-product of users and plans
    users_df["_key"] = 1
    plans_df["_key"] = 1
    cross = users_df.merge(plans_df, on="_key").drop("_key", axis=1)

    print(f"  ✓ Cross-product: {len(cross)} user-plan pairs")

    # Extract user attributes
    cross["user_age"] = pd.to_numeric(
        cross.get("age", 35), errors='coerce').fillna(35)
    cross["user_income_band"] = cross.get("income_band", "6-10L")
    cross["user_income"] = cross["user_income_band"].apply(
        map_income_band_to_numeric)
    cross["user_smoking"] = cross.get(
        "smoking_status", "no").astype(str).str.lower()
    cross["user_dependents"] = pd.to_numeric(
        cross.get("dependents", 0), errors='coerce').fillna(0)
    cross["user_claim_history"] = pd.to_numeric(
        cross.get("claim_history_count", 0), errors='coerce').fillna(0)
    cross["user_renewal"] = pd.to_numeric(
        cross.get("renewal_loyalty_years", 0), errors='coerce').fillna(0)
    cross["user_risk"] = pd.to_numeric(
        cross.get("risk_score", 0.5), errors='coerce').fillna(0.5)

    # Plan attributes
    cross["plan_premium"] = pd.to_numeric(
        cross.get("premium", 0), errors='coerce').fillna(0)
    cross["plan_deductible"] = pd.to_numeric(
        cross.get("deductible", 0), errors='coerce').fillna(0)
    cross["plan_coverage"] = pd.to_numeric(
        cross.get("coverage_amount", 0), errors='coerce').fillna(0)
    cross["plan_network"] = pd.to_numeric(
        cross.get("network_size", 0), errors='coerce').fillna(0)
    cross["plan_age_range"] = cross.get("age_range", "")
    cross["plan_risk"] = cross.get("risk_profile", "medium").fillna("medium")
    cross["plan_relevance"] = pd.to_numeric(
        cross.get("relevance_score", 0.5), errors='coerce').fillna(0.5)

    # Feature engineering
    cross["premium_income_ratio"] = cross["plan_premium"] / \
        (cross["user_income"] + 1e-9)
    cross["premium_coverage_ratio"] = cross["plan_premium"] / \
        (cross["plan_coverage"] + 1e-9)
    cross["network_per_100"] = cross["plan_network"] / 100.0
    cross["age_match"] = cross.apply(lambda r: age_in_range(
        r["user_age"], r["plan_age_range"]), axis=1)

    # Risk mapping
    risk_map = {"low": 0, "medium": 1, "high": 2}
    cross["risk_num"] = cross["plan_risk"].map(
        risk_map).fillna(1).astype(float)

    # Smoking flag
    smoking_map = {"yes": 1.0, "smoker": 1.0, "no": 0.0,
                   "non-smoker": 0.0, "ex-smoker": 0.5, "ex_smoker": 0.5}
    cross["smoking_flag"] = cross["user_smoking"].map(smoking_map).fillna(0.0)

    cross["dependents_count"] = cross["user_dependents"].astype(float)
    cross["claim_history"] = cross["user_claim_history"].astype(float)
    cross["renewal_years"] = cross["user_renewal"].astype(float)
    cross["user_risk_score"] = cross["user_risk"].astype(float)

    # Additional interaction features for personalization
    cross["age_premium_interaction"] = cross["user_age"] * \
        cross["premium_income_ratio"]
    cross["income_coverage_interaction"] = cross["user_income"] / \
        1e6 * cross["plan_coverage"] / 1e6
    cross["risk_smoking_interaction"] = cross["risk_num"] * cross["smoking_flag"]

    # Define feature columns
    feature_cols = [
        "plan_premium", "plan_deductible", "plan_coverage", "plan_network",
        "premium_income_ratio", "premium_coverage_ratio", "network_per_100",
        "age_match", "risk_num", "smoking_flag", "dependents_count",
        "claim_history", "renewal_years", "user_risk_score", "user_age",
        "age_premium_interaction", "income_coverage_interaction", "risk_smoking_interaction"
    ]

    # Ensure all features exist
    for col in feature_cols:
        if col not in cross.columns:
            cross[col] = 0.0
        cross[col] = pd.to_numeric(
            cross[col], errors='coerce').fillna(0).astype(float)

    # Build personalized labels
    labels = []
    for _, row in cross.iterrows():
        # Start with plan's base relevance
        label = row["plan_relevance"]

        # Fit bonuses
        fit_bonus = 0.0

        # 1. Age appropriateness (STRONG signal)
        if row["age_match"] == 1:
            fit_bonus += 2.0
        else:
            fit_bonus -= 1.0  # Penalty for age mismatch

        # 2. Affordability (STRONG signal)
        premium_ratio = row["premium_income_ratio"]
        if premium_ratio < 0.03:  # Very affordable (< 3% of income)
            fit_bonus += 1.5
        elif premium_ratio < 0.05:  # Affordable (< 5%)
            fit_bonus += 1.0
        elif premium_ratio < 0.10:  # Reasonable (< 10%)
            fit_bonus += 0.0
        elif premium_ratio < 0.20:  # Expensive (10-20%)
            fit_bonus -= 0.5
        else:  # Too expensive (> 20%)
            fit_bonus -= 1.5

        # 3. Risk alignment
        user_smoking = row["smoking_flag"]
        plan_risk = row["risk_num"]
        if user_smoking >= 0.5 and plan_risk >= 1:  # Smoker → medium/high risk plan
            fit_bonus += 0.8
        elif user_smoking == 0 and plan_risk == 0:  # Non-smoker → low risk plan
            fit_bonus += 0.8
        else:
            fit_bonus -= 0.3  # Misalignment

        # 4. Family coverage (dependents → large network)
        if row["dependents_count"] > 0:
            if row["network_per_100"] > 80:  # Large network (> 8000 hospitals)
                fit_bonus += 1.0
            elif row["network_per_100"] > 50:
                fit_bonus += 0.5

        # 5. High claimers → better coverage
        if row["claim_history"] > 3:
            if row["plan_coverage"] > 2000000:
                fit_bonus += 0.5

        # Final label
        label = label + fit_bonus
        label = max(0.0, min(10.0, label))  # Clamp to [0, 10]

        # Convert to discrete integer label (0-5) for LambdaRank
        # This maps: [0-2) → 0, [2-4) → 1, [4-5) → 2, [5-6) → 3, [6-8) → 4, [8-10] → 5
        if label < 2:
            discrete_label = 0
        elif label < 4:
            discrete_label = 1
        elif label < 5:
            discrete_label = 2
        elif label < 6:
            discrete_label = 3
        elif label < 8:
            discrete_label = 4
        else:
            discrete_label = 5

        labels.append(discrete_label)

    print(f"  ✓ Built {len(labels)} personalized labels")
    label_counts = pd.Series(labels).value_counts().sort_index()
    print(f"    Label distribution: {dict(label_counts)}")

    X = cross[feature_cols].astype(float)
    y = np.array(labels)

    return cross, X, y, feature_cols


def main():
    print("="*80)
    print("🤖 TRAINING PLAN RANKER V2 - PERSONALIZED FEATURE-BASED RANKING")
    print("="*80)

    # Load data
    print("\n📊 Loading data...")
    plans = pd.read_csv(ENHANCED_PLANS)
    users = pd.read_csv(USERS_CSV)
    print(f"  ✓ Loaded {len(plans)} plans")
    print(f"  ✓ Loaded {len(users)} users")

    # Build features and labels
    print("\n🔨 Building features and personalized labels...")
    cross, X, y, feature_cols = compute_features_and_labels(users, plans)

    # Create groups for ranking (each user is a group)
    groups = cross.groupby("user_id").size().values
    print(f"  ✓ Created {len(groups)} ranking groups")

    # Split: 85% train, 15% val (by user groups)
    print("\n✂️  Splitting data...")
    n_train_groups = int(len(groups) * 0.85)
    train_groups = groups[:n_train_groups]
    val_groups = groups[n_train_groups:]

    train_size = sum(train_groups)
    val_size = sum(val_groups)

    X_train = X.iloc[:train_size]
    y_train = y[:train_size]
    X_val = X.iloc[train_size:]
    y_val = y[train_size:]

    print(f"  ✓ Train: {train_size} samples, {len(train_groups)} groups")
    print(f"  ✓ Val: {val_size} samples, {len(val_groups)} groups")

    # Train LightGBM Ranker
    print("\n🏋️  Training LightGBM Ranker...")
    model = LGBMRanker(
        objective="lambdarank",
        n_estimators=300,
        learning_rate=0.05,
        max_depth=6,
        num_leaves=31,
        min_child_samples=20,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        verbose=-1
    )

    model.fit(
        X_train, y_train,
        group=train_groups,
        eval_set=[(X_val, y_val)],
        eval_group=[val_groups],
        eval_metric="ndcg",
        eval_at=[3]
    )

    print(f"  ✓ Model trained with {model.n_estimators} trees")

    # Validation metrics
    print("\n📈 Computing validation metrics...")
    val_preds = model.predict(X_val)

    # Compute NDCG@3 manually
    ndcg_scores = []
    offset = 0
    for group_size in val_groups:
        group_preds = val_preds[offset:offset+group_size]
        group_true = y_val[offset:offset+group_size]

        # Sort by predictions
        top_k = min(3, len(group_preds))
        top_indices = np.argsort(group_preds)[::-1][:top_k]

        # DCG
        dcg = sum((2**group_true[i] - 1) / np.log2(rank + 2)
                  for rank, i in enumerate(top_indices))

        # IDCG
        ideal_indices = np.argsort(group_true)[::-1][:top_k]
        idcg = sum((2**group_true[i] - 1) / np.log2(rank + 2)
                   for rank, i in enumerate(ideal_indices))

        ndcg = dcg / idcg if idcg > 0 else 0
        ndcg_scores.append(ndcg)
        offset += group_size

    ndcg_mean = np.mean(ndcg_scores)
    print(f"  ✓ Validation NDCG@3: {ndcg_mean:.4f}")

    # Feature importance
    print("\n📊 Top 10 Feature Importances:")
    importances = model.feature_importances_
    feature_importance = sorted(
        zip(feature_cols, importances), key=lambda x: x[1], reverse=True)
    for feat, imp in feature_importance[:10]:
        print(f"     {feat:30s}: {imp:8.2f}")

    # Save model
    print(f"\n💾 Saving model to: {MODEL_PATH}")
    save_obj = {
        "model": model,
        "feature_cols": feature_cols,
        "feature_importance": dict(feature_importance)
    }
    joblib.dump(save_obj, MODEL_PATH)

    print("\n" + "="*80)
    print("✅ TRAINING COMPLETE")
    print("="*80)
    print(f"\n📦 Model saved to: {MODEL_PATH}")
    print(f"📊 Validation NDCG@3: {ndcg_mean:.4f}")
    print(f"🎯 Features: {len(feature_cols)}")
    print(f"🌳 Trees: {model.n_estimators}")
    print("\n💡 Next: Run test_top5_for_5_users.py to validate recommendations")
    print("="*80)


if __name__ == "__main__":
    main()
