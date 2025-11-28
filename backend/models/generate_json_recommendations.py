import pandas as pd
import numpy as np
import pickle
import os
import json
from datetime import datetime

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))

print("Generating JSON recommendations...")

# Load model
model_path = os.path.join(script_dir, 'plan_ranker.pkl')
with open(model_path, 'rb') as f:
    model_artifacts = pickle.load(f)

model = model_artifacts['model']
feature_columns = model_artifacts['feature_columns']
label_encoders = model_artifacts['label_encoders']

# Define test user
test_user = {
    "user_id": "U9999",
    "age": 32,
    "gender": "male",
    "marital_status": "married",
    "dependents": 1,
    "region": "Maharashtra",
    "urban_rural": "urban",
    "income_band": "6-10L",
    "occupation": "salaried",
    "digital_literacy": "high",
    "preferred_payment_mode": "annual",
    "preferred_providers": "HDFC ERGO;Star Health",
    "avg_annual_spend": 45000,
    "risk_score": 0.25,
    "chronic_conditions": "none",
    "family_medical_history": "diabetes",
    "existing_health_policy": "no",
    "claim_history_count": 0,
    "renewal_loyalty_years": 0,
    "has_diabetes": "no",
    "has_hypertension": "no",
    "has_asthma": "no",
    "has_cancer_history": "no",
    "has_heart_disease": "no",
    "has_thyroid": "no",
    "has_kidney_disease": "no",
    "has_obesity": "no",
    "has_disability": "no",
    "smoking_status": "non-smoker"
}

# Load and prepare data (same as test_unseen_user.py)
plans = pd.read_csv(os.path.join(script_dir, 'plans.csv'))
plan_hospital_map = pd.read_csv(os.path.join(
    script_dir, 'plan_hospital_map_large.csv'))
hospitals = pd.read_csv(os.path.join(script_dir, 'hospitals_large.csv'))

# Aggregate network statistics
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

hospital_states = hospitals[['hospital_id', 'state']].copy()
plan_hospital_with_state = plan_hospital_map.merge(
    hospital_states, on='hospital_id', how='left')
plan_states = plan_hospital_with_state.groupby('plan_id')['state'].apply(
    lambda x: ','.join(sorted(set(x.dropna())))
).reset_index()
plan_states.columns = ['planid', 'hospital_states']
plan_profiles = plan_profiles.merge(plan_states, on='planid', how='left')

# Create user-plan pairs and generate features
user_plan_pairs = []
for _, plan in plan_profiles.iterrows():
    pair = {**test_user, **plan.to_dict()}
    user_plan_pairs.append(pair)

inference_df = pd.DataFrame(user_plan_pairs)

# Feature engineering
income_mapping = {'<3L': 2.5, '3-6L': 4.5,
                  '6-10L': 8.0, '10-20L': 15.0, '>20L': 25.0}
inference_df['income_numeric'] = inference_df['income_band'].map(
    income_mapping)
inference_df['premium_affordability'] = (
    inference_df['premium'] * 12) / (inference_df['income_numeric'] * 100000)
inference_df['coverage_need_match'] = 0
inference_df.loc[(inference_df['chronic_conditions'] != 'none') & (
    inference_df['coverageamount'] >= 5000000), 'coverage_need_match'] = 1


def check_regional_match(row):
    if pd.isna(row['hospital_states']) or pd.isna(row['region']):
        return 0
    return 1 if str(row['region']).strip() in str(row['hospital_states']).split(',') else 0


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
    return row['premium']


inference_df['age_adjusted_premium'] = inference_df.apply(
    get_age_premium_fit, axis=1)
inference_df['age_premium_fit'] = inference_df['premium'] / \
    (inference_df['age_adjusted_premium'] + 1)
inference_df['claim_approval_rate'] = 100 - inference_df['claimrejectionrate']
inference_df['cashless_ratio'] = inference_df['cashless_percentage'] / 100
inference_df['value_score'] = inference_df['coverageamount'] / \
    (inference_df['premium'] + 1)
inference_df['risk_alignment'] = (
    inference_df['risk_score'] * inference_df['coverageamount']) / 10000000
inference_df['has_accident_cover'] = inference_df['addons'].str.contains(
    'accident_cover', na=False).astype(int)
inference_df['loyalty_bonus'] = inference_df['renewal_loyalty_years'] / 10

# Preprocessing
bool_columns = ['has_diabetes', 'has_hypertension', 'has_asthma', 'has_cancer_history',
                'has_heart_disease', 'has_thyroid', 'has_kidney_disease', 'has_obesity', 'has_disability']
for col in bool_columns:
    if col in inference_df.columns:
        inference_df[col] = inference_df[col].map(
            {'yes': 1, 'no': 0}).fillna(0)

categorical_features = [
    col for col in label_encoders.keys() if col in inference_df.columns]
for col in categorical_features:
    inference_df[col] = inference_df[col].fillna('unknown')
    inference_df[col] = inference_df[col].apply(
        lambda x: x if str(x) in label_encoders[col].classes_ else 'unknown')
    inference_df[col] = label_encoders[col].transform(
        inference_df[col].astype(str))

numerical_features = [
    col for col in feature_columns if col not in categorical_features]
for col in numerical_features:
    if col in inference_df.columns:
        inference_df[col] = inference_df[col].fillna(0)

# Generate predictions
X_inference = inference_df[feature_columns].copy()
scores = model.predict(X_inference)

# Create results
results = pd.DataFrame({
    'planid': inference_df['planid'],
    'plan_name': inference_df['plan_name'],
    'provider': inference_df['provider'],
    'premium': inference_df['premium'],
    'coverageamount': inference_df['coverageamount'],
    'plan_type': inference_df['plan_type'],
    'plan_category': inference_df['plan_category'],
    'networksize': inference_df['networksize'],
    'claimrejectionrate': inference_df['claimrejectionrate'],
    'cashless_percentage': inference_df['cashless_percentage'],
    'regional_match': inference_df['regional_match'],
    'addons': inference_df['addons'],
    'score': scores
})

results = results.sort_values('score', ascending=False)

# Filter by constraints
max_budget = 5000
min_coverage = 500000
filtered_results = results[(results['premium'] <= max_budget) & (
    results['coverageamount'] >= min_coverage)]
top_10 = filtered_results.head(10)

# Create JSON output
output = {
    "request_timestamp": datetime.now().isoformat(),
    "user_profile": test_user,
    "requirements": {
        "max_budget": max_budget,
        "min_coverage": min_coverage,
        "plan_type_preference": "Family Floater",
        "special_requirements": ["maternity_coverage", "cashless_hospitals_mumbai"]
    },
    "summary": {
        "total_plans_evaluated": len(results),
        "plans_within_budget": int((results['premium'] <= max_budget).sum()),
        "plans_with_min_coverage": int((results['coverageamount'] >= min_coverage).sum()),
        "plans_matching_all_criteria": len(filtered_results),
        "score_range": {
            "min": float(scores.min()),
            "max": float(scores.max())
        }
    },
    "recommendations": []
}

for idx, (_, row) in enumerate(top_10.iterrows(), 1):
    recommendation = {
        "rank": idx,
        "score": float(row['score']),
        "plan": {
            "plan_id": str(row['planid']),
            "plan_name": str(row['plan_name']),
            "provider": str(row['provider']),
            "plan_type": str(row['plan_type']),
            "plan_category": str(row['plan_category'])
        },
        "pricing": {
            "premium_annual": float(row['premium']),
            "coverage_amount": float(row['coverageamount']),
            "value_ratio": float(row['coverageamount'] / row['premium'])
        },
        "quality_metrics": {
            "claim_approval_rate": float(100 - row['claimrejectionrate']),
            "network_size": int(row['networksize']),
            "cashless_percentage": float(row['cashless_percentage']),
            "regional_match": bool(row['regional_match'])
        },
        "features": {
            "addons": str(row['addons']) if pd.notna(row['addons']) else None
        },
        "fit_assessment": {
            "affordability": f"{(row['premium']/max_budget*100):.0f}% of budget",
            "coverage_adequacy": f"{(row['coverageamount']/min_coverage):.1f}x minimum",
            "network_availability": "Yes" if row['regional_match'] else "No"
        }
    }
    output["recommendations"].append(recommendation)

# Save JSON
output_path = os.path.join(script_dir, 'recommendations_U9999.json')
with open(output_path, 'w') as f:
    json.dump(output, f, indent=2)

print(f"✓ JSON recommendations saved to: {output_path}")
print(f"✓ Generated {len(output['recommendations'])} recommendations")
print("\nPreview (first recommendation):")
print(json.dumps(output['recommendations'][0], indent=2))
