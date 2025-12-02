import pandas as pd
import numpy as np
import os
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
import lightgbm as lgb
import pickle
from datetime import datetime

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

print("="*80)
print("INSURANCE PLAN RECOMMENDATION MODEL TRAINING")
print("="*80)
print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# ============================================================================
# STEP 1: LOAD ALL DATASETS
# ============================================================================
print("\n" + "="*80)
print("STEP 1: Loading All Datasets")
print("="*80)

users = pd.read_csv(os.path.join(script_dir, 'users.csv'))
demographics = pd.read_csv(os.path.join(script_dir, 'demographics.csv'))
health_lifestyle = pd.read_csv(
    os.path.join(script_dir, 'health_lifestyle.csv'))
income_profession = pd.read_csv(
    os.path.join(script_dir, 'income_profession.csv'))
insurance_history = pd.read_csv(
    os.path.join(script_dir, 'insurance_history.csv'))
plans = pd.read_csv(os.path.join(script_dir, 'plans.csv'))
policy_preferences = pd.read_csv(
    os.path.join(script_dir, 'policy_preferences.csv'))
product_specific = pd.read_csv(
    os.path.join(script_dir, 'product_specific.csv'))
insurer_quality = pd.read_csv(os.path.join(script_dir, 'insurer_quality.csv'))
interactions = pd.read_csv(os.path.join(script_dir, 'interactions.csv'))
hospitals = pd.read_csv(os.path.join(script_dir, 'hospitals_large.csv'))
plan_hospital_map = pd.read_csv(os.path.join(
    script_dir, 'plan_hospital_map_large.csv'))

print(f"✓ Users: {users.shape}")
print(f"✓ Demographics: {demographics.shape}")
print(f"✓ Health/Lifestyle: {health_lifestyle.shape}")
print(f"✓ Income/Profession: {income_profession.shape}")
print(f"✓ Insurance History: {insurance_history.shape}")
print(f"✓ Plans: {plans.shape}")
print(f"✓ Policy Preferences: {policy_preferences.shape}")
print(f"✓ Product Specific: {product_specific.shape}")
print(f"✓ Insurer Quality: {insurer_quality.shape}")
print(f"✓ Interactions: {interactions.shape}")
print(f"✓ Hospitals: {hospitals.shape}")
print(f"✓ Plan-Hospital Map: {plan_hospital_map.shape}")

# ============================================================================
# STEP 2: CREATE COMPREHENSIVE USER PROFILES
# ============================================================================
print("\n" + "="*80)
print("STEP 2: Creating Comprehensive User Profiles")
print("="*80)

# Start with users.csv as base (it has most columns already)
user_profiles = users.copy()

# The users.csv already contains most fields, but we can verify and merge if needed
# Check if we need additional columns from other tables
print(
    f"User profiles created with {user_profiles.shape[0]} users and {user_profiles.shape[1]} features")

# ============================================================================
# STEP 3: CREATE ENRICHED PLAN PROFILES WITH NETWORK FEATURES
# ============================================================================
print("\n" + "="*80)
print("STEP 3: Creating Enriched Plan Profiles with Network Features")
print("="*80)

# Start with plans.csv as base
plan_profiles = plans.copy()

# Aggregate hospital network features per plan
print("Aggregating network statistics...")
network_stats = plan_hospital_map.groupby('plan_id').agg({
    'hospital_id': 'count',  # network_size
    'distance_score': 'mean',  # avg_distance_score
    'contract_type': [
        lambda x: (x == 'cashless').sum() / len(x) *
        100,  # cashless_percentage
        lambda x: (x == 'reimbursement').sum() /
        len(x) * 100  # reimbursement_percentage
    ]
}).reset_index()

network_stats.columns = ['planid', 'network_size_actual', 'avg_distance_score',
                         'cashless_percentage', 'reimbursement_percentage']

# Merge network stats with plan profiles
plan_profiles = plan_profiles.merge(network_stats, on='planid', how='left')

# Update networksize with actual counts
plan_profiles['networksize'] = plan_profiles['network_size_actual'].fillna(
    plan_profiles['networksize'])
plan_profiles = plan_profiles.drop('network_size_actual', axis=1)

# Add hospital-state mapping for regional matching
hospital_states = hospitals[['hospital_id', 'state']].copy()
plan_hospital_with_state = plan_hospital_map.merge(
    hospital_states, on='hospital_id', how='left')

# For each plan, get list of states where hospitals are available
plan_states = plan_hospital_with_state.groupby('plan_id')['state'].apply(
    lambda x: ','.join(sorted(set(x.dropna())))
).reset_index()
plan_states.columns = ['planid', 'hospital_states']

plan_profiles = plan_profiles.merge(plan_states, on='planid', how='left')

print(
    f"Plan profiles created with {plan_profiles.shape[0]} plans and {plan_profiles.shape[1]} features")
print(f"Network features: avg_distance_score, cashless_percentage, reimbursement_percentage")

# ============================================================================
# STEP 4: BUILD TRAINING DATASET WITH USER-PLAN PAIRS
# ============================================================================
print("\n" + "="*80)
print("STEP 4: Building Training Dataset with User-Plan Pairs")
print("="*80)

# Get positive interactions (label=1)
positive_interactions = interactions[interactions['label'] == 1][[
    'user_id', 'planid', 'label']].copy()
print(f"Positive interactions: {len(positive_interactions)}")

# Generate negative samples (random plans user didn't interact with)
print("Generating negative samples...")
all_users = user_profiles['user_id'].unique()
all_plans = plan_profiles['planid'].unique()

# For each user, sample negative plans (plans they didn't interact with)
negative_samples = []
interaction_pairs = set(zip(interactions['user_id'], interactions['planid']))

np.random.seed(42)
for user in all_users:
    user_interacted_plans = interactions[interactions['user_id']
                                         == user]['planid'].unique()
    available_plans = [p for p in all_plans if (
        user, p) not in interaction_pairs]

    # Sample 5 negative plans per user (adjust ratio as needed)
    num_negatives = min(5, len(available_plans))
    if num_negatives > 0:
        sampled_negatives = np.random.choice(
            available_plans, size=num_negatives, replace=False)
        for plan in sampled_negatives:
            negative_samples.append(
                {'user_id': user, 'planid': plan, 'label': 0})

negative_df = pd.DataFrame(negative_samples)
print(f"Negative samples generated: {len(negative_df)}")

# Combine positive and negative samples
training_data = pd.concat(
    [positive_interactions, negative_df], ignore_index=True)
print(f"Total training samples: {len(training_data)}")
print(f"Positive ratio: {training_data['label'].mean():.3f}")

# ============================================================================
# STEP 5: MERGE USER AND PLAN FEATURES WITH TRAINING DATA
# ============================================================================
print("\n" + "="*80)
print("STEP 5: Merging User and Plan Features")
print("="*80)

# Merge user features
training_data = training_data.merge(user_profiles, on='user_id', how='left')
print(f"After user merge: {training_data.shape}")

# Merge plan features
training_data = training_data.merge(plan_profiles, on='planid', how='left')
print(f"After plan merge: {training_data.shape}")

# ============================================================================
# STEP 6: CREATE DERIVED FEATURES
# ============================================================================
print("\n" + "="*80)
print("STEP 6: Creating Derived Features")
print("="*80)

# 1. Premium affordability (relative to income)
income_mapping = {
    '<3L': 2.5, '3-6L': 4.5, '6-10L': 8.0, '10-20L': 15.0, '>20L': 25.0
}
training_data['income_numeric'] = training_data['income_band'].map(
    income_mapping)
training_data['premium_affordability'] = (
    training_data['premium'] * 12) / (training_data['income_numeric'] * 100000)

# 2. Coverage need match based on chronic conditions
training_data['coverage_need_match'] = 0
training_data.loc[
    (training_data['chronic_conditions'] != 'none') & (
        training_data['coverageamount'] >= 5000000),
    'coverage_need_match'
] = 1

# 3. Regional match (check if user's region/state has hospitals in plan network)


def check_regional_match(row):
    if pd.isna(row['hospital_states']) or pd.isna(row['region']):
        return 0
    hospital_state_list = str(row['hospital_states']).split(',')
    user_state = str(row['region']).strip()
    return 1 if user_state in hospital_state_list else 0


training_data['regional_match'] = training_data.apply(
    check_regional_match, axis=1)

# 4. Age-premium fit (use age-specific premiums if available)


def get_age_premium_fit(row):
    age = row['age']
    if age >= 18 and age <= 35 and pd.notna(row.get('age_band_18_35_premium')):
        return row['age_band_18_35_premium']
    elif age >= 36 and age <= 50 and pd.notna(row.get('age_band_36_50_premium')):
        return row['age_band_36_50_premium']
    elif age >= 51 and age <= 65 and pd.notna(row.get('age_band_51_65_premium')):
        return row['age_band_51_65_premium']
    else:
        return row['premium']


training_data['age_adjusted_premium'] = training_data.apply(
    get_age_premium_fit, axis=1)
training_data['age_premium_fit'] = training_data['premium'] / \
    (training_data['age_adjusted_premium'] + 1)

# 5. Claim approval rate (inverse of rejection rate)
training_data['claim_approval_rate'] = 100 - \
    training_data['claimrejectionrate']

# 6. Cashless ratio
training_data['cashless_ratio'] = training_data['cashless_percentage'] / 100

# 7. Value score (coverage per rupee of premium)
training_data['value_score'] = training_data['coverageamount'] / \
    (training_data['premium'] + 1)

# 8. Risk alignment (match high-risk users with comprehensive plans)
training_data['risk_alignment'] = (
    (training_data['risk_score'] * training_data['coverageamount']) / 10000000
)

# 9. Has accident cover
training_data['has_accident_cover'] = training_data['addons'].str.contains(
    'accident_cover', na=False
).astype(int)

# 10. Loyalty bonus (reward plans for users with high renewal loyalty)
training_data['loyalty_bonus'] = training_data['renewal_loyalty_years'] / 10

print("Derived features created:")
print("  ✓ premium_affordability")
print("  ✓ coverage_need_match")
print("  ✓ regional_match")
print("  ✓ age_premium_fit")
print("  ✓ claim_approval_rate")
print("  ✓ cashless_ratio")
print("  ✓ value_score")
print("  ✓ risk_alignment")
print("  ✓ has_accident_cover")
print("  ✓ loyalty_bonus")

# ============================================================================
# STEP 7: FEATURE ENGINEERING AND PREPROCESSING
# ============================================================================
print("\n" + "="*80)
print("STEP 7: Feature Engineering and Preprocessing")
print("="*80)

# Select features for modeling
categorical_features = [
    'gender', 'marital_status', 'occupation', 'income_band', 'urban_rural',
    'region', 'smoking_status', 'chronic_conditions', 'family_medical_history',
    'existing_health_policy', 'plan_type', 'plan_category', 'provider'
]

numerical_features = [
    'age', 'dependents', 'avg_annual_spend', 'risk_score', 'claim_history_count',
    'renewal_loyalty_years', 'premium', 'deductible', 'copay', 'coverageamount',
    'networksize', 'claimrejectionrate', 'waitingperioddays', 'avg_distance_score',
    'cashless_percentage', 'reimbursement_percentage', 'premium_affordability',
    'coverage_need_match', 'regional_match', 'age_premium_fit', 'claim_approval_rate',
    'cashless_ratio', 'value_score', 'risk_alignment', 'has_accident_cover',
    'loyalty_bonus', 'has_diabetes', 'has_hypertension', 'has_asthma',
    'has_cancer_history', 'has_heart_disease', 'has_thyroid', 'has_kidney_disease',
    'has_obesity', 'has_disability'
]

# Convert boolean columns to int
bool_columns = [
    'has_diabetes', 'has_hypertension', 'has_asthma', 'has_cancer_history',
    'has_heart_disease', 'has_thyroid', 'has_kidney_disease', 'has_obesity',
    'has_disability'
]
for col in bool_columns:
    if col in training_data.columns:
        training_data[col] = training_data[col].map(
            {'yes': 1, 'no': 0}).fillna(0)

# Encode categorical variables
label_encoders = {}
for col in categorical_features:
    if col in training_data.columns:
        le = LabelEncoder()
        training_data[col] = training_data[col].fillna('unknown')
        training_data[col] = le.fit_transform(training_data[col].astype(str))
        label_encoders[col] = le

print(f"Encoded {len(label_encoders)} categorical features")

# Fill missing values in numerical features
for col in numerical_features:
    if col in training_data.columns:
        training_data[col] = training_data[col].fillna(
            training_data[col].median())

print("Missing values handled")

# Prepare feature matrix
feature_columns = [col for col in categorical_features +
                   numerical_features if col in training_data.columns]
X = training_data[feature_columns].copy()
y = training_data['label'].copy()
groups = training_data['user_id'].copy()

print(f"\nFinal feature matrix: {X.shape}")
print(f"Number of features: {len(feature_columns)}")
print(
    f"Target distribution - Positive: {y.sum()}, Negative: {len(y) - y.sum()}")

# ============================================================================
# STEP 8: TRAIN-TEST SPLIT (GROUP BY USER)
# ============================================================================
print("\n" + "="*80)
print("STEP 8: Creating Train-Test Split")
print("="*80)

# Get unique users and split them
unique_users = training_data['user_id'].unique()
train_users, test_users = train_test_split(
    unique_users, test_size=0.2, random_state=42)

train_mask = training_data['user_id'].isin(train_users)
test_mask = training_data['user_id'].isin(test_users)

X_train = X[train_mask]
y_train = y[train_mask]
groups_train = groups[train_mask]

X_test = X[test_mask]
y_test = y[test_mask]
groups_test = groups[test_mask]

print(f"Train set: {len(X_train)} samples from {len(train_users)} users")
print(f"Test set: {len(X_test)} samples from {len(test_users)} users")

# Create group information for ranking
train_group_data = groups_train.value_counts().sort_index().values
test_group_data = groups_test.value_counts().sort_index().values

print(f"Train groups: {len(train_group_data)}")
print(f"Test groups: {len(test_group_data)}")

# ============================================================================
# STEP 9: TRAIN LIGHTGBM RANKER MODEL
# ============================================================================
print("\n" + "="*80)
print("STEP 9: Training LightGBM Ranker Model")
print("="*80)

# Create LightGBM datasets
train_data = lgb.Dataset(
    X_train,
    label=y_train,
    group=train_group_data,
    categorical_feature=[
        col for col in categorical_features if col in feature_columns]
)

test_data = lgb.Dataset(
    X_test,
    label=y_test,
    group=test_group_data,
    categorical_feature=[
        col for col in categorical_features if col in feature_columns],
    reference=train_data
)

# Set parameters for LambdaRank
params = {
    'objective': 'lambdarank',
    'metric': 'ndcg',
    'ndcg_eval_at': [5, 10, 20],
    'boosting_type': 'gbdt',
    'num_leaves': 31,
    'learning_rate': 0.05,
    'feature_fraction': 0.9,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'verbose': 0,
    'max_depth': 6,
    'min_data_in_leaf': 20,
}

print("Training with parameters:")
for key, value in params.items():
    print(f"  {key}: {value}")

# Train the model
print("\nTraining in progress...")
callbacks = [
    lgb.log_evaluation(period=50),
    lgb.early_stopping(stopping_rounds=50)
]

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, test_data],
    valid_names=['train', 'test'],
    callbacks=callbacks
)

print(f"\n✓ Training completed!")
print(f"Best iteration: {model.best_iteration}")
print(f"Best score: {model.best_score}")

# ============================================================================
# STEP 10: EVALUATE MODEL
# ============================================================================
print("\n" + "="*80)
print("STEP 10: Model Evaluation")
print("="*80)

# Feature importance
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importance(importance_type='gain')
}).sort_values('importance', ascending=False)

print("\nTop 20 Most Important Features:")
print(feature_importance.head(20).to_string(index=False))

# ============================================================================
# STEP 11: SAVE MODEL AND ARTIFACTS
# ============================================================================
print("\n" + "="*80)
print("STEP 11: Saving Model and Artifacts")
print("="*80)

# Save the trained model
model_path = os.path.join(script_dir, 'plan_ranker.pkl')
with open(model_path, 'wb') as f:
    pickle.dump({
        'model': model,
        'feature_columns': feature_columns,
        'label_encoders': label_encoders,
        'categorical_features': categorical_features,
        'numerical_features': numerical_features,
        'feature_importance': feature_importance
    }, f)

print(f"✓ Model saved to: {model_path}")

# Save feature importance
feature_importance_path = os.path.join(script_dir, 'feature_importance.csv')
feature_importance.to_csv(feature_importance_path, index=False)
print(f"✓ Feature importance saved to: {feature_importance_path}")

# Save training metadata
metadata = {
    'training_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'total_samples': len(training_data),
    'train_samples': len(X_train),
    'test_samples': len(X_test),
    'num_features': len(feature_columns),
    'num_users': len(unique_users),
    'num_plans': len(plan_profiles),
    'positive_ratio': float(y.mean()),
    'best_iteration': model.best_iteration,
    'best_score': model.best_score
}

metadata_path = os.path.join(script_dir, 'training_metadata.txt')
with open(metadata_path, 'w') as f:
    for key, value in metadata.items():
        f.write(f"{key}: {value}\n")

print(f"✓ Training metadata saved to: {metadata_path}")

print("\n" + "="*80)
print(" MODEL TRAINING COMPLETED SUCCESSFULLY!")
print("="*80)
print(f"\nModel artifacts saved:")
print(f"  1. plan_ranker.pkl - Trained model")
print(f"  2. feature_importance.csv - Feature importance rankings")
print(f"  3. training_metadata.txt - Training metadata")
print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)
