#!/usr/bin/env python3
# test_top5_for_5_users.py
"""
Loads saved model and returns top-5 recommendations + raw scores for 5 users.
Also runs simple validation checks:
 - Diversity: checks that scores are not identical across users
 - If interactions.csv has a chosen plan for that user, checks top-1 match

How to run:
    cd project/src
    python test_top5_for_5_users.py
"""

import os
import pandas as pd
import joblib
import numpy as np

ROOT = os.path.join(os.path.dirname(__file__), "..")
# Try both locations for data
DATA_DIR_1 = os.path.join(ROOT, "backend", "models")
DATA_DIR_2 = os.path.join(ROOT, "models")
DATA_DIR = DATA_DIR_1 if os.path.exists(DATA_DIR_1) else DATA_DIR_2

MODEL_PATH = os.path.join(DATA_DIR, "plan_ranker.pkl")
ENHANCED_PLANS = os.path.join(DATA_DIR, "enhanced_plans_dataset.csv")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")
INTERACTIONS_CSV = os.path.join(DATA_DIR, "interactions.csv")

print("="*80)
print("🧪 TESTING PLAN RANKER - TOP 5 RECOMMENDATIONS FOR 5 USERS")
print("="*80)

# Load data
print(f"\n📂 Loading data from: {DATA_DIR}")
users_df = pd.read_csv(USERS_CSV)
plans_df = pd.read_csv(ENHANCED_PLANS)

# Choose 5 user_ids to test - pick first 5 from users.csv
test_users = users_df["user_id"].drop_duplicates().tolist()[:5]
print(f"✓ Loaded {len(plans_df)} plans")
print(f"✓ Loaded {len(users_df)} users")
print(f"✓ Testing 5 users: {test_users}")

# Load model
print(f"\n🤖 Loading model from: {MODEL_PATH}")
saved = joblib.load(MODEL_PATH)
model = saved["model"]
feature_cols = saved["feature_cols"]
print(f"✓ Model loaded with {len(feature_cols)} features")
print(f"  Features: {feature_cols}")

# Helper functions


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


def build_user_candidates(user_row):
    """Build feature matrix for one user against all plans"""
    # Convert user row to dict
    user = user_row.to_dict()

    # Get user attributes
    user_age = user.get("age", 35)
    user_income_band = user.get("income_band", "6-10L")
    user_income = user.get(
        "income", map_income_band_to_numeric(user_income_band))
    user_smoking = user.get("smoking_status", "no")
    user_dependents = user.get("dependents", 0)
    user_claim_history = user.get("claim_history_count", 0)
    user_renewal = user.get("renewal_loyalty_years", 0)
    user_risk = user.get("risk_score", 0.5)

    # Create candidate dataframe
    df = plans_df.copy()
    df["user_id"] = user["user_id"]

    # Compute features
    df["age"] = user_age
    df["income"] = user_income
    df["premium_income_ratio"] = df["premium"] / (df["income"] + 1e-9)
    df["premium_coverage_ratio"] = df["premium"] / \
        (df["coverage_amount"] + 1e-9)
    df["network_per_100"] = df["network_size"] / 100.0
    df["age_match"] = df.apply(lambda r: age_in_range(
        user_age, r.get("age_range")), axis=1)

    # Risk mapping
    risk_map = {"low": 0, "medium": 1, "high": 2}
    df["risk_num"] = df.get("risk_profile", "medium").fillna(
        "medium").map(risk_map).fillna(1).astype(float)

    # Smoking flag
    smoking_map = {"yes": 1, "no": 0,
                   "ex-smoker": 0.5, "smoker": 1, "non-smoker": 0}
    df["smoking_flag"] = smoking_map.get(str(user_smoking).lower(), 0)

    df["dependents_count"] = float(user_dependents)
    df["claim_history"] = float(user_claim_history)
    df["renewal_years"] = float(user_renewal)
    df["user_risk_score"] = float(user_risk)

    # Ensure all feature columns exist
    for col in feature_cols:
        if col not in df.columns:
            df[col] = 0.0
        else:
            df[col] = pd.to_numeric(
                df[col], errors='coerce').fillna(0).astype(float)

    # Extract features in correct order
    X = df[feature_cols].astype(float)
    return df, X


# Load interactions for ground truth check
inter = pd.read_csv(INTERACTIONS_CSV) if os.path.exists(
    INTERACTIONS_CSV) else pd.DataFrame()
print(f"✓ Loaded {len(inter)} interactions")

# Test each user
print("\n" + "="*80)
print("📊 GENERATING RECOMMENDATIONS")
print("="*80)

all_top_ids = []
all_top1_scores = []

for idx, uid in enumerate(test_users, 1):
    user_row = users_df[users_df["user_id"] == uid].iloc[0]
    user_age = user_row.get("age", "N/A")
    user_income_band = user_row.get("income_band", "N/A")
    user_income = map_income_band_to_numeric(user_income_band)

    # Build candidates
    df_candidates, X = build_user_candidates(user_row)

    # Predict
    preds = model.predict(X)
    df_candidates["score"] = preds

    # Get top 5
    top5 = df_candidates.sort_values("score", ascending=False).head(5)

    # Get plan IDs (handle both column names)
    if "plan_id" in top5.columns:
        top_ids = top5["plan_id"].tolist()
    elif "planid" in top5.columns:
        top_ids = top5["planid"].tolist()
    else:
        top_ids = ["UNKNOWN"] * 5

    all_top_ids.append(tuple(top_ids[:3]))  # Store top-3 for diversity check
    all_top1_scores.append(preds.max())

    # Display results
    print(f"\n{'─'*80}")
    print(f"👤 USER {idx}: {uid}")
    print(f"{'─'*80}")
    print(
        f"📋 Profile: Age={user_age}, Income Band={user_income_band} (₹{user_income:,})")
    print(
        f"           Smoking={user_row.get('smoking_status', 'N/A')}, Dependents={user_row.get('dependents', 0)}")
    print(f"\n🎯 TOP 5 RECOMMENDATIONS:\n")

    # Format and display top 5
    for rank, (_, row) in enumerate(top5.iterrows(), 1):
        plan_id = row.get("plan_id", row.get("planid", "N/A"))
        provider = row.get("provider", "N/A")
        plan_name = row.get("plan_name", "N/A")
        premium = row.get("premium", 0)
        coverage = row.get("coverage_amount", 0)
        network = row.get("network_size", 0)
        score = row.get("score", 0)

        print(f"   {rank}. {plan_name[:50]}")
        print(f"      Provider: {provider[:40]}")
        print(f"      Plan ID: {plan_id} | Premium: ₹{premium:,.0f}/month")
        print(
            f"      Coverage: ₹{coverage:,.0f} | Network: {int(network)} hospitals")
        print(f"      📊 Score: {score:.6f}\n")

    # Check historical interaction match
    if not inter.empty:
        # Try to find purchase or shortlist events for this user
        user_interactions = inter[inter["user_id"] == uid]

        if len(user_interactions) > 0:
            # Look for purchase events first, then shortlist
            purchase = user_interactions[user_interactions["event_type"] == "purchase"]
            if len(purchase) > 0:
                chosen_pid = purchase.iloc[0]["planid"] if "planid" in purchase.columns else purchase.iloc[0].get(
                    "plan_id", "")
                match = "✅ MATCH!" if top_ids[0] == chosen_pid else "❌ No match"
                print(
                    f"   🎯 Historical Purchase: {chosen_pid} → Top-1: {top_ids[0]} {match}")
            else:
                shortlist = user_interactions[user_interactions["event_type"]
                                              == "shortlist"]
                if len(shortlist) > 0:
                    chosen_pid = shortlist.iloc[0]["planid"] if "planid" in shortlist.columns else shortlist.iloc[0].get(
                        "plan_id", "")
                    match = "✅ In Top-5!" if chosen_pid in top_ids else "❌ Not in Top-5"
                    print(f"   📌 Historical Shortlist: {chosen_pid} {match}")

# Validation checks
print("\n" + "="*80)
print("🔍 VALIDATION CHECKS")
print("="*80)

# 1) Score diversity check
print("\n1️⃣  SCORE DIVERSITY CHECK:")
print(f"   Top-1 scores across users: {[f'{s:.6f}' for s in all_top1_scores]}")

unique_scores = len(set([round(s, 5) for s in all_top1_scores]))
if unique_scores == 1:
    print(f"   ⚠️  WARNING: All top-1 scores are IDENTICAL!")
    print(f"      This indicates the model is not personalizing.")
    print(f"      → Check feature engineering (are user features varying?)")
elif unique_scores < len(test_users):
    print(
        f"   ⚡ PARTIAL: {unique_scores}/{len(test_users)} users have unique top-1 scores")
    print(f"      Some users may have identical profiles or similar preferences.")
else:
    print(f"   ✅ PASS: All {len(test_users)} users have unique top-1 scores")

# 2) Recommendation diversity check
print("\n2️⃣  RECOMMENDATION DIVERSITY CHECK:")
unique_top3_sets = len(set(all_top_ids))
print(f"   Distinct top-3 sets: {unique_top3_sets}/{len(test_users)}")

if unique_top3_sets == 1:
    print(f"   ⚠️  CRITICAL: All users received IDENTICAL top-3 recommendations!")
    print(f"      This indicates a serious personalization issue.")
    print(f"      → Re-check feature engineering and model training.")
elif unique_top3_sets < len(test_users) * 0.6:
    print(
        f"   ⚡ MODERATE: {unique_top3_sets}/{len(test_users)} users have unique top-3 sets")
    print(f"      Consider adding more features (demographics, geography, plan tiers)")
else:
    print(
        f"   ✅ GOOD: {unique_top3_sets}/{len(test_users)} users have distinct top-3 recommendations")

# 3) Score range check
print("\n3️⃣  SCORE RANGE CHECK:")
all_scores = []
for uid in test_users:
    user_row = users_df[users_df["user_id"] == uid].iloc[0]
    df_candidates, X = build_user_candidates(user_row)
    preds = model.predict(X)
    all_scores.extend(preds)

all_scores = np.array(all_scores)
print(f"   Score statistics across all predictions:")
print(f"     Min: {all_scores.min():.6f}")
print(f"     Max: {all_scores.max():.6f}")
print(f"     Mean: {all_scores.mean():.6f}")
print(f"     Std: {all_scores.std():.6f}")

if all_scores.std() < 0.01:
    print(
        f"   ⚠️  WARNING: Very low score variance (std={all_scores.std():.6f})")
    print(f"      Model may not be learning meaningful patterns.")
else:
    print(f"   ✅ PASS: Scores show good variance")

# Summary
print("\n" + "="*80)
print("📋 TEST SUMMARY")
print("="*80)
print(f"✓ Tested {len(test_users)} users")
print(f"✓ Generated {len(test_users) * 5} recommendations total")
print(
    f"✓ Score diversity: {unique_scores}/{len(test_users)} unique top-1 scores")
print(
    f"✓ Recommendation diversity: {unique_top3_sets}/{len(test_users)} unique top-3 sets")
print(f"✓ Score range: [{all_scores.min():.4f}, {all_scores.max():.4f}]")

# Pass/Fail criteria
passes = []
warnings = []

if unique_scores >= len(test_users) * 0.8:
    passes.append("Score diversity")
else:
    warnings.append("Low score diversity")

if unique_top3_sets >= len(test_users) * 0.6:
    passes.append("Recommendation diversity")
else:
    warnings.append("Low recommendation diversity")

if all_scores.std() >= 0.1:
    passes.append("Score variance")
else:
    warnings.append("Low score variance")

print(f"\n{'✅ PASSES:' if passes else '✅ No passes'}")
for p in passes:
    print(f"   ✓ {p}")

if warnings:
    print(f"\n⚠️  WARNINGS:")
    for w in warnings:
        print(f"   • {w}")

print("\n" + "="*80)
if len(warnings) == 0:
    print("🎉 ALL CHECKS PASSED - Model is working well!")
elif len(warnings) <= 1:
    print("⚡ MOSTLY GOOD - Minor tuning recommended")
else:
    print("⚠️  NEEDS ATTENTION - Review feature engineering and training")
print("="*80 + "\n")
