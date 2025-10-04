#!/usr/bin/env python3
"""
Test script to verify the trained LTR model works correctly.
"""
import pandas as pd
from utils.simple_ranker import PlanRanker
import sys
import os
sys.path.append('/Users/varadpendkar/Documents/project/backend/app')


def test_model():
    print("Testing LTR model integration...")

    # Initialize ranker
    try:
        from pathlib import Path
        project_root = Path(
            '/Users/varadpendkar/Documents/project/backend/app')
        ranker = PlanRanker(project_root)
        print("✅ PlanRanker initialized successfully")
    except Exception as e:
        print(f"❌ PlanRanker initialization failed: {e}")
        return False

    # Create sample user profile
    user_profile = {
        'age': 30,
        'dependents': 2,
        'risk_score': 0.3,
        'income': 1200000,
        'location': 'Mumbai'
    }

    # Create sample plans
    plans_data = [
        {
            'plan_id': 'PL001',
            'plan_name': 'Basic Health Plan',
            'premium': 8000,
            'deductible': 15000,
            'copay': 500,
            'coverage_amount': 300000,
            'network_size': 50,
            'claim_rejection_rate': 0.15,
            'waiting_period_days': 30
        },
        {
            'plan_id': 'PL002',
            'plan_name': 'Premium Health Plan',
            'premium': 15000,
            'deductible': 10000,
            'copay': 300,
            'coverage_amount': 1000000,
            'network_size': 200,
            'claim_rejection_rate': 0.05,
            'waiting_period_days': 45
        },
        {
            'plan_id': 'PL003',
            'plan_name': 'Super Premium Plan',
            'premium': 25000,
            'deductible': 5000,
            'copay': 200,
            'coverage_amount': 2000000,
            'network_size': 300,
            'claim_rejection_rate': 0.02,
            'waiting_period_days': 60
        }
    ]

    # Test ranking
    try:
        ranked_plans = ranker.rank(user_profile, plans_data)
        print("✅ Model ranking successful")
        print("\n🏆 Ranked Results:")
        for i, plan in enumerate(ranked_plans, 1):
            print(
                f"{i}. {plan.get('plan_name', plan.get('plan_id'))} - Score: {plan.get('score', 'N/A'):.3f}")

        return True
    except Exception as e:
        print(f"❌ Model ranking failed: {e}")
        return False


if __name__ == "__main__":
    success = test_model()
    if success:
        print("\n🎉 Model test passed! Ready for Flask integration.")
    else:
        print("\n💥 Model test failed. Check the errors above.")
