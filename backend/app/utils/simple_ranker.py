#!/usr/bin/env python3
"""
Simplified PlanRanker that works with our trained 11-feature model.
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import Booster

# Simple 11-feature list matching our trained model
FEATURES = [
    "age", "dependents", "risk_score", "income",
    "premium", "deductible", "copay", "coverage_amount",
    "network_size", "claim_rejection_rate", "waiting_period_days"
]


def _add_features(user: dict, plans: pd.DataFrame) -> pd.DataFrame:
    """Add user features to plans dataframe."""
    df = plans.copy()

    # Ensure required plan columns exist
    for col, default in [
        ("premium", 5000.0), ("deductible", 10000.0), ("copay",
                                                       500.0), ("coverage_amount", 500000.0),
        ("network_size", 100.0), ("claim_rejection_rate",
                                  0.1), ("waiting_period_days", 30.0)
    ]:
        if col not in df.columns:
            df[col] = default

    # Add user features (broadcast to all plans)
    df["age"] = int(user.get("age", 30))
    df["dependents"] = int(user.get("dependents", 0))
    df["risk_score"] = float(user.get("risk_score", 0.3))
    df["income"] = float(user.get("income", 800000))  # Default middle income

    # Ensure numeric columns and handle missing values
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    return df


def _generate_bullets(user: dict, plan: dict) -> list:
    """Generate bullet points explaining plan benefits."""
    bullets = []

    income = float(user.get("income", 800000))
    premium = float(plan.get("premium", 0))

    # Premium affordability
    if income > 0:
        ratio = premium / income
        if ratio < 0.05:
            bullets.append("Very affordable premium for your income")
        elif ratio < 0.08:
            bullets.append("Reasonable premium for your income")

    # Network size
    network_size = float(plan.get("network_size", 0))
    if network_size > 200:
        bullets.append("Extensive hospital network")
    elif network_size > 100:
        bullets.append("Good hospital network coverage")

    # Claim rejection rate
    rejection_rate = float(plan.get("claim_rejection_rate", 1.0))
    if rejection_rate < 0.05:
        bullets.append("Very low claim rejection rate")
    elif rejection_rate < 0.1:
        bullets.append("Low claim rejection rate")

    # Coverage amount
    coverage = float(plan.get("coverage_amount", 0))
    if coverage >= 1000000:
        bullets.append("High coverage amount")
    elif coverage >= 500000:
        bullets.append("Good coverage amount")

    # Deductible
    deductible = float(plan.get("deductible", float('inf')))
    if deductible < 10000:
        bullets.append("Low deductible - quick coverage")
    elif deductible < 20000:
        bullets.append("Moderate deductible")

    return bullets[:4]  # Return max 4 bullets


class PlanRanker:
    """Simplified PlanRanker for LTR model inference."""

    def __init__(self, project_root: Path):
        self.root = Path(project_root)

        # Load model
        model_path = self._find_model_path()
        self.booster = Booster(model_file=str(model_path))

        # Load plans data
        data_dir = self.root.parent / "data"  # backend/data
        self.plans = pd.read_csv(data_dir / "plans.csv")

        # Normalize column names
        column_mapping = {
            "planid": "plan_id",
            "coverageamount": "coverage_amount",
            "networksize": "network_size",
            "claimrejectionrate": "claim_rejection_rate",
            "waitingperioddays": "waiting_period_days"
        }

        # Apply mapping if columns exist
        for old_name, new_name in column_mapping.items():
            if old_name in self.plans.columns and new_name not in self.plans.columns:
                self.plans[new_name] = self.plans[old_name]

    def _find_model_path(self) -> Path:
        """Find the LTR model file."""
        candidates = [
            os.environ.get("RANKER_MODEL_PATH"),
            str(self.root / "models" / "ltr_model.txt"),
            str(self.root.parent / "models" / "ltr_model.txt")
        ]

        for candidate in candidates:
            if candidate and Path(candidate).exists():
                return Path(candidate)

        raise FileNotFoundError(
            f"No LTR model found. Tried: {candidates}"
        )

    def rank(self, user: dict, plans_data: list = None, k: int = 8) -> list:
        """
        Rank plans for a user.

        Args:
            user: User profile dict with age, income, etc.
            plans_data: Optional list of plans. If None, uses self.plans.
            k: Number of top plans to return

        Returns:
            List of ranked plan dictionaries with scores and bullets
        """
        # Use provided plans or default plans
        if plans_data:
            plans_df = pd.DataFrame(plans_data)
        else:
            plans_df = self.plans.copy()

        if plans_df.empty:
            return []

        # Add features
        features_df = _add_features(user, plans_df)

        # Get predictions
        scores = self.booster.predict(features_df[FEATURES].values)

        # Create result dataframe
        result_df = plans_df.copy()
        result_df['score'] = scores

        # Sort by score and take top k
        top_plans = result_df.sort_values('score', ascending=False).head(k)

        # Convert to list of dicts with additional info
        recommendations = []
        for _, row in top_plans.iterrows():
            plan_dict = row.to_dict()

            # Add bullets
            plan_dict['bullets'] = _generate_bullets(user, plan_dict)

            # Ensure score is float
            plan_dict['score'] = float(plan_dict['score'])

            # Convert numeric fields to int where appropriate
            for field in ['premium', 'deductible', 'copay', 'coverage_amount', 'network_size']:
                if field in plan_dict and pd.notnull(plan_dict[field]):
                    plan_dict[field] = int(float(plan_dict[field]))

            recommendations.append(plan_dict)

        return recommendations
