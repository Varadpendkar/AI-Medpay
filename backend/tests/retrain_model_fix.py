#!/usr/bin/env python3
"""
Quick Model Retraining Script - Fix Constant 0.1 Predictions

This script trains a new LightGBM ranking model using synthetic interaction data
to replace the broken model that returns constant 0.1 scores.
"""
from sklearn.preprocessing import LabelEncoder
from pathlib import Path
import lightgbm as lgb
import pandas as pd
import numpy as np
import pickle
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


print("="*80)
print("🔧 RETRAINING MODEL - Fix Constant 0.1 Score Issue")
print("="*80)

# Load existing data
models_dir = Path(__file__).parent / "backend" / "models"
plans_df = pd.read_csv(models_dir / "plans.csv")
users_df = pd.read_csv(models_dir / "users.csv")

print(f"\n✓ Loaded {len(plans_df)} plans")
print(f"✓ Loaded {len(users_df)} users")

# Create synthetic training data with realistic preferences
print("\n📊 Creating synthetic training data...")

training_data = []

# Sample 50 users for training
sample_users = users_df.sample(min(50, len(users_df)), random_state=42)

# Map income bands to numeric values for affordability calculation
income_map = {'<3L': 250000, '3-6L': 450000,
              '6-10L': 800000, '10-20L': 1500000, '>20L': 2500000}

for _, user in sample_users.iterrows():
    user_plans = plans_df.copy()

    # Add user columns to each plan row
    for col in user.index:
        if col not in user_plans.columns:
            user_plans[col] = user[col]

    # Assign relevance labels (0-4) based on user-plan fit
    labels = []
    user_income = income_map.get(user.get('income_band', '6-10L'), 800000)

    for _, plan in user_plans.iterrows():
        score = 0

        # Premium affordability (most important)
        premium_annual = plan['premium'] * 12
        affordability_ratio = premium_annual / user_income
        if affordability_ratio < 0.05:
            score += 3
        elif affordability_ratio < 0.08:
            score += 2
        elif affordability_ratio < 0.12:
            score += 1

        # Coverage amount
        if plan.get('coverageamount', 0) >= 500000:
            score += 1

        # Network size
        if plan.get('networksize', 0) > 50:
            score += 1

        # Claim rejection rate
        if plan.get('claimrejectionrate', 5) < 2.0:
            score += 1

        # Cap at 4
        labels.append(min(score, 4))

    user_plans['label'] = labels
    user_plans['group_id'] = user['user_id']

    training_data.append(user_plans)

train_df = pd.concat(training_data, ignore_index=True)
print(
    f"✓ Created {len(train_df)} training samples from {len(sample_users)} users")
print(
    f"  Label distribution: {dict(train_df['label'].value_counts().sort_index())}")

# Feature engineering (same as inference)
print("\n🔨 Engineering features...")

# Categorical features to encode
categorical_features = [
    'gender', 'marital_status', 'occupation', 'income_band', 'urban_rural',
    'region', 'smoking_status', 'chronic_conditions', 'family_medical_history',
    'existing_health_policy', 'plan_type', 'plan_category', 'provider'
]

label_encoders = {}
for col in categorical_features:
    if col in train_df.columns:
        le = LabelEncoder()
        train_df[col] = train_df[col].fillna('unknown').astype(str)
        train_df[col] = le.fit_transform(train_df[col])
        label_encoders[col] = le

# Numerical features
numerical_features = [
    'age', 'dependents', 'avg_annual_spend', 'risk_score',
    'claim_history_count', 'renewal_loyalty_years', 'premium',
    'deductible', 'copay', 'coverageamount', 'networksize',
    'claimrejectionrate', 'waitingperioddays'
]

for col in numerical_features:
    if col in train_df.columns:
        train_df[col] = pd.to_numeric(train_df[col], errors='coerce').fillna(0)

# Derived features (add the same features used in new_ranker.py)
income_mapping = {'<3L': 2.5, '3-6L': 4.5,
                  '6-10L': 8.0, '10-20L': 15.0, '>20L': 25.0}
if 'income_band' in train_df.columns:
    train_df['income_numeric'] = train_df['income_band'].map(
        income_mapping).fillna(8.0)
else:
    train_df['income_numeric'] = 8.0
train_df['premium_affordability'] = (
    train_df['premium'] * 12) / (train_df['income_numeric'] * 100000 + 1)
train_df['claim_approval_rate'] = 100 - train_df['claimrejectionrate']
train_df['cashless_ratio'] = train_df.get('cashless_percentage', 0) / 100
train_df['value_score'] = train_df['coverageamount'] / \
    (train_df['premium'] + 1)
train_df['risk_alignment'] = (
    train_df['risk_score'] * train_df['coverageamount']) / 10000000

# Fill missing columns
for col in ['avg_distance_score', 'cashless_percentage', 'reimbursement_percentage',
            'coverage_need_match', 'regional_match', 'age_premium_fit',
            'has_accident_cover', 'loyalty_bonus']:
    if col not in train_df.columns:
        train_df[col] = 0

# Boolean health columns
bool_columns = [
    'has_diabetes', 'has_hypertension', 'has_asthma', 'has_cancer_history',
    'has_heart_disease', 'has_thyroid', 'has_kidney_disease', 'has_obesity',
    'has_disability'
]
for col in bool_columns:
    if col in train_df.columns:
        train_df[col] = train_df[col].map(
            {'yes': 1, 'no': 0, 'Yes': 1, 'No': 0}).fillna(0).astype(int)
    else:
        train_df[col] = 0

# Define feature columns (48 features)
feature_columns = categorical_features + numerical_features + [
    'premium_affordability', 'coverage_need_match', 'regional_match', 'age_premium_fit',
    'claim_approval_rate', 'cashless_ratio', 'value_score', 'risk_alignment',
    'has_accident_cover', 'loyalty_bonus'
] + bool_columns

# Ensure all features exist
for col in feature_columns:
    if col not in train_df.columns:
        train_df[col] = 0

X_train = train_df[feature_columns].values
y_train = train_df['label'].astype(int).values
group_train = train_df.groupby('group_id').size().to_numpy()

print(f"✓ Feature matrix: {X_train.shape}")
print(f"✓ Features ({len(feature_columns)}): {feature_columns[:10]}...")

# Train LightGBM LambdaRank model
print("\n🤖 Training LightGBM LambdaRank model...")

dtrain = lgb.Dataset(X_train, label=y_train,
                     group=group_train, free_raw_data=False)

params = {
    "objective": "lambdarank",
    "metric": "ndcg",
    "ndcg_eval_at": [1, 3, 5, 10],
    "boosting": "gbdt",
    "num_leaves": 64,
    "learning_rate": 0.05,
    "min_data_in_leaf": 10,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbosity": 1,
    "seed": 42
}

model = lgb.train(
    params,
    dtrain,
    num_boost_round=200,
    valid_sets=[dtrain],
    valid_names=["train"],
)

print(f"✓ Model trained with {model.num_trees()} trees")

# Test predictions to verify they vary
test_preds = model.predict(X_train[:100])
print(f"\n✓ Test predictions (first 10): {test_preds[:10]}")
print(f"  Unique values: {len(np.unique(test_preds))}")
print(f"  Min: {test_preds.min():.4f}, Max: {test_preds.max():.4f}, Mean: {test_preds.mean():.4f}")

if len(np.unique(test_preds)) == 1:
    print("\n⚠️  WARNING: Model still predicting constant values!")
    print("   This may indicate insufficient training data variation.")
else:
    print("\n✓ SUCCESS: Model producing varied predictions!")

# Save model artifacts
model_path = models_dir / "plan_ranker.pkl"
backup_path = models_dir / "plan_ranker_broken_backup.pkl"

print(f"\n💾 Saving model to {model_path}...")

# Backup old model
if model_path.exists():
    import shutil
    shutil.copy(model_path, backup_path)
    print(f"✓ Backed up old model to {backup_path}")

# Feature importance
feature_importance = dict(
    zip(feature_columns, model.feature_importance(importance_type='gain')))
top_features = sorted(feature_importance.items(),
                      key=lambda x: x[1], reverse=True)[:10]
print("\n📊 Top 10 features by importance:")
for feat, imp in top_features:
    print(f"   {feat}: {imp:.2f}")

# Save new model
artifacts = {
    'model': model,
    'feature_columns': feature_columns,
    'label_encoders': label_encoders,
    'feature_importance': feature_importance
}

with open(model_path, 'wb') as f:
    pickle.dump(artifacts, f)

print(f"\n✅ Model saved successfully!")
print(f"   Features: {len(feature_columns)}")
print(f"   Label encoders: {len(label_encoders)}")
print(f"   Trees: {model.num_trees()}")

print("\n" + "="*80)
print("🎯 RETRAINING COMPLETE")
print("="*80)
print("\n💡 Next steps:")
print("   1. Restart the Flask server to load the new model")
print("   2. Re-run debug_run_tests.py to verify diversity")
print("   3. Test the /get-quote endpoint with real users")
print("="*80)
