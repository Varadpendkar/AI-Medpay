#!/usr/bin/env python3
"""
Simple LTR model training script that works with existing data structure.
Creates the ltr_model.txt file needed by the PlanRanker class.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path
from lightgbm import LGBMRanker, early_stopping, log_evaluation

# Paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "backend" / "data"
MODEL_DIR = PROJECT_ROOT / "backend" / "app" / "models"
OUTPUT_DIR = PROJECT_ROOT / "backend" / "outputs"

# Ensure directories exist
MODEL_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def create_training_data():
    """Create synthetic training data from existing CSV files."""
    print("Loading data files...")

    # Load existing data
    users = pd.read_csv(DATA_DIR / "users.csv")
    plans = pd.read_csv(DATA_DIR / "plans.csv")
    interactions = pd.read_csv(DATA_DIR / "interactions.csv")

    print(
        f"Loaded {len(users)} users, {len(plans)} plans, {len(interactions)} interactions")

    # Create synthetic training sessions
    # Each user gets a session with 5-10 plans to rank
    training_data = []

    # Normalize column names
    plans = plans.rename(columns={
        "planid": "plan_id",
        "coverageamount": "coverage_amount",
        "networksize": "network_size",
        "claimrejectionrate": "claim_rejection_rate",
        "waitingperioddays": "waiting_period_days"
    })

    session_id = 0
    for _, user in users.head(100).iterrows():  # Use first 100 users for training
        session_id += 1

        # Sample 5-10 plans for this user session
        n_plans = np.random.randint(5, 11)
        session_plans = plans.sample(n_plans).copy()

        # Create relevance scores based on user profile
        for idx, (_, plan) in enumerate(session_plans.iterrows()):
            # Simple relevance scoring based on user attributes
            relevance = calculate_relevance(user, plan)

            training_data.append({
                'session_id': session_id,
                'user_id': user['user_id'],
                'plan_id': plan['plan_id'],
                'label': relevance,
                'shown_rank': idx + 1,

                # User features
                'age': user.get('age', 35),
                'dependents': user.get('dependents', 0),
                'risk_score': user.get('risk_score', 0.5),
                'income': extract_income(user.get('income_band', 'middle')),

                # Plan features
                'premium': plan.get('premium', 5000),
                'deductible': plan.get('deductible', 10000),
                'copay': plan.get('copay', 500),
                'coverage_amount': plan.get('coverage_amount', 500000),
                'network_size': plan.get('network_size', 100),
                'claim_rejection_rate': plan.get('claim_rejection_rate', 0.1),
                'waiting_period_days': plan.get('waiting_period_days', 30)
            })

    return pd.DataFrame(training_data)


def extract_income(income_band):
    """Convert income band to numeric value."""
    band_map = {
        'low': 300000, 'middle': 800000, 'high': 1500000,
        'very_low': 200000, 'very_high': 2500000
    }
    return band_map.get(str(income_band).lower(), 800000)


def calculate_relevance(user, plan):
    """Calculate synthetic relevance score (0-2) for user-plan pair."""
    score = 0

    # Age-based premium preference
    age = user.get('age', 35)
    premium = plan.get('premium', 5000)
    if age < 35 and premium < 8000:
        score += 1
    elif age >= 35 and premium < 15000:
        score += 1

    # Income-coverage matching
    income = extract_income(user.get('income_band', 'middle'))
    coverage = plan.get('coverage_amount', 500000)
    if income > 1000000 and coverage > 500000:
        score += 1
    elif income <= 1000000 and coverage <= 500000:
        score += 1

    return min(score, 2)  # Cap at 2


def train_model():
    """Train the LTR model and save artifacts."""
    print("Creating training data...")
    df = create_training_data()

    print(
        f"Created {len(df)} training examples across {df['session_id'].nunique()} sessions")

    # Define features
    features = [
        'age', 'dependents', 'risk_score', 'income',
        'premium', 'deductible', 'copay', 'coverage_amount',
        'network_size', 'claim_rejection_rate', 'waiting_period_days'
    ]

    # Fill any missing values
    df[features] = df[features].fillna(0)

    # Split by session (80/20)
    sessions = df['session_id'].unique()
    np.random.shuffle(sessions)

    split_idx = int(0.8 * len(sessions))
    train_sessions = sessions[:split_idx]
    val_sessions = sessions[split_idx:]

    train_df = df[df['session_id'].isin(train_sessions)].copy()
    val_df = df[df['session_id'].isin(val_sessions)].copy()

    # Prepare training data
    X_train = train_df[features].values
    y_train = train_df['label'].values
    X_val = val_df[features].values
    y_val = val_df['label'].values

    # Group sizes (number of plans per session)
    group_train = train_df.groupby('session_id').size().to_numpy()
    group_val = val_df.groupby('session_id').size().to_numpy()

    print(
        f"Training: {len(train_df)} examples, {len(train_sessions)} sessions")
    print(f"Validation: {len(val_df)} examples, {len(val_sessions)} sessions")

    # Train LGBMRanker
    print("Training LTR model...")
    ranker = LGBMRanker(
        objective='lambdarank',
        metric='ndcg',
        learning_rate=0.1,
        n_estimators=100,  # Reduced for faster training
        num_leaves=31,
        min_data_in_leaf=10,
        feature_fraction=0.9,
        random_state=42
    )

    ranker.fit(
        X_train, y_train,
        group=group_train,
        eval_set=[(X_val, y_val)],
        eval_group=[group_val],
        eval_at=[3, 5],
        callbacks=[log_evaluation(period=20),
                   early_stopping(stopping_rounds=20)]
    )

    # Save model
    model_path = MODEL_DIR / "ltr_model.txt"
    ranker.booster_.save_model(str(model_path))
    print(f"✅ Model saved to: {model_path}")

    # Save metadata
    metadata = {
        "features": features,
        "model_path": str(model_path),
        "training_sessions": len(train_sessions),
        "validation_sessions": len(val_sessions),
        "n_estimators": ranker.n_estimators
    }

    metadata_path = MODEL_DIR / "ltr_model_metadata.json"
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    # Create sample ranking
    if len(val_df) > 0:
        sample_session = val_df['session_id'].iloc[0]
        sample_df = val_df[val_df['session_id'] == sample_session].copy()
        sample_df['predicted_score'] = ranker.predict(
            sample_df[features].values)
        sample_df = sample_df.sort_values('predicted_score', ascending=False)

        sample_output = sample_df[['session_id', 'user_id',
                                   'plan_id', 'predicted_score', 'label']].head()
        sample_path = OUTPUT_DIR / "sample_ranking.csv"
        sample_output.to_csv(sample_path, index=False)
        print(f"📊 Sample ranking saved to: {sample_path}")

    print("🎉 LTR model training complete!")
    return model_path


if __name__ == "__main__":
    try:
        model_path = train_model()
        print(f"\n🔗 Model ready for use in PlanRanker: {model_path}")
    except Exception as e:
        print(f"❌ Training failed: {e}")
        raise
