import pandas as pd
import numpy as np
import pickle
import os

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

print("="*80)
print("INSURANCE PLAN RECOMMENDATION - INFERENCE DEMO")
print("="*80)

# ============================================================================
# LOAD TRAINED MODEL
# ============================================================================
print("\nLoading trained model...")
model_path = os.path.join(script_dir, 'plan_ranker.pkl')

with open(model_path, 'rb') as f:
    model_artifacts = pickle.load(f)

model = model_artifacts['model']
feature_columns = model_artifacts['feature_columns']
label_encoders = model_artifacts['label_encoders']
feature_importance = model_artifacts['feature_importance']

print(f"✓ Model loaded successfully")
print(f"✓ Number of features: {len(feature_columns)}")

# ============================================================================
# LOAD DATA FOR INFERENCE
# ============================================================================
print("\nLoading data files...")
users = pd.read_csv(os.path.join(script_dir, 'users.csv'))
plans = pd.read_csv(os.path.join(script_dir, 'plans.csv'))
plan_hospital_map = pd.read_csv(os.path.join(
    script_dir, 'plan_hospital_map_large.csv'))
hospitals = pd.read_csv(os.path.join(script_dir, 'hospitals_large.csv'))

print(f"✓ Users: {len(users)}")
print(f"✓ Plans: {len(plans)}")

# ============================================================================
# PREPARE PLAN FEATURES (same as training)
# ============================================================================
print("\nPreparing plan features...")

# Aggregate network stats
network_stats = plan_hospital_map.groupby('plan_id').agg({
    'hospital_id': 'count',
    'distance_score': 'mean',
    'contract_type': [
        lambda x: (x == 'cashless').sum() / len(x) * 100,
        lambda x: (x == 'reimbursement').sum() / len(x) * 100
    ]
}).reset_index()
network_stats.columns = ['planid', 'network_size_actual', 'avg_distance_score',
                         'cashless_percentage', 'reimbursement_percentage']

plan_profiles = plans.merge(network_stats, on='planid', how='left')
plan_profiles['networksize'] = plan_profiles['network_size_actual'].fillna(
    plan_profiles['networksize'])
plan_profiles = plan_profiles.drop('network_size_actual', axis=1)

# Add hospital states
hospital_states = hospitals[['hospital_id', 'state']].copy()
plan_hospital_with_state = plan_hospital_map.merge(
    hospital_states, on='hospital_id', how='left')
plan_states = plan_hospital_with_state.groupby('plan_id')['state'].apply(
    lambda x: ','.join(sorted(set(x.dropna())))
).reset_index()
plan_states.columns = ['planid', 'hospital_states']
plan_profiles = plan_profiles.merge(plan_states, on='planid', how='left')

print(f"✓ Plan profiles prepared")

# ============================================================================
# EXAMPLE: GET RECOMMENDATIONS FOR A SPECIFIC USER
# ============================================================================
print("\n" + "="*80)
print("EXAMPLE: Getting Recommendations for Sample Users")
print("="*80)

# Select 5 random users for demo
sample_users = users.sample(n=5, random_state=42)

for idx, user in sample_users.iterrows():
    user_id = user['user_id']
    print(f"\n{'='*80}")
    print(f"User: {user_id}")
    print(f"{'='*80}")
    print(
        f"Age: {user['age']}, Gender: {user['gender']}, Region: {user['region']}")
    print(f"Income: {user['income_band']}, Occupation: {user['occupation']}")
    print(f"Chronic Conditions: {user['chronic_conditions']}")
    print(f"Risk Score: {user['risk_score']:.3f}")

    # Create user-plan pairs for all plans
    user_plan_pairs = []
    for _, plan in plan_profiles.iterrows():
        pair = {**user.to_dict(), **plan.to_dict()}
        user_plan_pairs.append(pair)

    inference_df = pd.DataFrame(user_plan_pairs)

    # Create derived features (same as training)
    income_mapping = {
        '<3L': 2.5, '3-6L': 4.5, '6-10L': 8.0, '10-20L': 15.0, '>20L': 25.0
    }
    inference_df['income_numeric'] = inference_df['income_band'].map(
        income_mapping)
    inference_df['premium_affordability'] = (
        inference_df['premium'] * 12) / (inference_df['income_numeric'] * 100000)

    inference_df['coverage_need_match'] = 0
    inference_df.loc[
        (inference_df['chronic_conditions'] != 'none') & (
            inference_df['coverageamount'] >= 5000000),
        'coverage_need_match'
    ] = 1

    def check_regional_match(row):
        if pd.isna(row['hospital_states']) or pd.isna(row['region']):
            return 0
        hospital_state_list = str(row['hospital_states']).split(',')
        user_state = str(row['region']).strip()
        return 1 if user_state in hospital_state_list else 0

    inference_df['regional_match'] = inference_df.apply(
        check_regional_match, axis=1)

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

    inference_df['age_adjusted_premium'] = inference_df.apply(
        get_age_premium_fit, axis=1)
    inference_df['age_premium_fit'] = inference_df['premium'] / \
        (inference_df['age_adjusted_premium'] + 1)
    inference_df['claim_approval_rate'] = 100 - \
        inference_df['claimrejectionrate']
    inference_df['cashless_ratio'] = inference_df['cashless_percentage'] / 100
    inference_df['value_score'] = inference_df['coverageamount'] / \
        (inference_df['premium'] + 1)
    inference_df['risk_alignment'] = (
        inference_df['risk_score'] * inference_df['coverageamount']) / 10000000
    inference_df['has_accident_cover'] = inference_df['addons'].str.contains(
        'accident_cover', na=False).astype(int)
    inference_df['loyalty_bonus'] = inference_df['renewal_loyalty_years'] / 10

    # Convert boolean columns
    bool_columns = [
        'has_diabetes', 'has_hypertension', 'has_asthma', 'has_cancer_history',
        'has_heart_disease', 'has_thyroid', 'has_kidney_disease', 'has_obesity',
        'has_disability'
    ]
    for col in bool_columns:
        if col in inference_df.columns:
            inference_df[col] = inference_df[col].map(
                {'yes': 1, 'no': 0}).fillna(0)

    # Encode categorical variables
    categorical_features = [
        col for col in label_encoders.keys() if col in inference_df.columns]
    for col in categorical_features:
        inference_df[col] = inference_df[col].fillna('unknown')
        # Handle unseen categories
        inference_df[col] = inference_df[col].apply(
            lambda x: x if x in label_encoders[col].classes_ else 'unknown'
        )
        inference_df[col] = label_encoders[col].transform(
            inference_df[col].astype(str))

    # Fill missing values
    numerical_features = [
        col for col in feature_columns if col not in categorical_features]
    for col in numerical_features:
        if col in inference_df.columns:
            inference_df[col] = inference_df[col].fillna(0)

    # Prepare feature matrix
    X_inference = inference_df[feature_columns].copy()

    # Get predictions
    scores = model.predict(X_inference)

    # Create results dataframe
    results = pd.DataFrame({
        'planid': inference_df['planid'],
        'plan_name': inference_df['plan_name'],
        'provider': inference_df['provider'],
        'premium': inference_df['premium'],
        'coverageamount': inference_df['coverageamount'],
        'networksize': inference_df['networksize'],
        'regional_match': inference_df['regional_match'],
        'score': scores
    })

    # Sort by score
    results = results.sort_values('score', ascending=False)

    # Display top 10 recommendations
    print(f"\nTop 10 Recommended Plans:")
    print("-" * 80)
    for i, (_, row) in enumerate(results.head(10).iterrows(), 1):
        print(f"\n{i}. {row['plan_name'][:60]}")
        print(f"   Provider: {row['provider']}")
        print(
            f"   Premium: ₹{row['premium']:,.0f}/year | Coverage: ₹{row['coverageamount']:,.0f}")
        print(
            f"   Network Size: {row['networksize']:.0f} hospitals | Regional Match: {'Yes' if row['regional_match'] else 'No'}")
        print(f"   Recommendation Score: {row['score']:.4f}")

print("\n" + "="*80)
print("✅ INFERENCE COMPLETED SUCCESSFULLY!")
print("="*80)
print("\nNote: Higher scores indicate better recommendations for the user.")
print("The model considers multiple factors including affordability, coverage needs,")
print("network accessibility, and risk alignment.")
print("="*80)
