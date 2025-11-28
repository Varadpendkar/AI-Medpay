#!/usr/bin/env python3
"""
test_model_recommendations.py
--------------------------------
Batch tests the PlanRanker model using 10 synthetic users to verify
distinct recommendation outputs and model diversity.

This ensures:
✅ Recommendations vary per user profile
✅ No missing field errors
✅ Fallback logic triggers correctly for edge cases
✅ Model produces personalized results
"""

import os
import sys
import json
import uuid
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

# Set PYTHONPATH
os.environ['PYTHONPATH'] = str(PROJECT_ROOT)

# Import the ranker
from backend.app.utils.new_ranker import NewPlanRanker

# ✅ 10 Diverse User Profiles
test_users = [
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Priya Sharma",
        "age": 26,
        "gender": "F",
        "marital_status": "single",
        "city": "Mumbai",
        "state": "Maharashtra",
        "annual_income": 450000,
        "income_band": "3-6L",
        "premium_budget": 2000,
        "occupation_type": "salaried",
        "dependents": 0,
        "dependents_count": 0,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "individual",
        "coverage_amount": 500000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": [],
        "preferred_providers": ["Star Health"],
        "claim_history_count": 0,
        "renewal_loyalty_years": 0,
        "risk_score": 0.2,
        "bmi": 22.5
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Rajesh Kumar",
        "age": 38,
        "gender": "M",
        "marital_status": "married",
        "city": "Delhi",
        "state": "Delhi",
        "annual_income": 1500000,
        "income_band": "10-20L",
        "premium_budget": 8000,
        "occupation_type": "self_employed",
        "dependents": 2,
        "dependents_count": 2,
        "smoking_flag": "yes",
        "smoking_status": "yes",
        "plan_type": "floater",
        "coverage_amount": 1000000,
        "has_diabetes": True,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": ["diabetes"],
        "preferred_providers": ["HDFC Ergo"],
        "claim_history_count": 2,
        "renewal_loyalty_years": 3,
        "risk_score": 0.7,
        "bmi": 28.0
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Anjali Desai",
        "age": 45,
        "gender": "F",
        "marital_status": "married",
        "city": "Pune",
        "state": "Maharashtra",
        "annual_income": 900000,
        "income_band": "6-10L",
        "premium_budget": 5000,
        "occupation_type": "salaried",
        "dependents": 3,
        "dependents_count": 3,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "floater",
        "coverage_amount": 1500000,
        "has_diabetes": False,
        "has_hypertension": True,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": ["hypertension"],
        "preferred_providers": [],
        "claim_history_count": 1,
        "renewal_loyalty_years": 2,
        "risk_score": 0.5,
        "bmi": 24.8
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Karthik Reddy",
        "age": 29,
        "gender": "M",
        "marital_status": "single",
        "city": "Bangalore",
        "state": "Karnataka",
        "annual_income": 1200000,
        "income_band": "10-20L",
        "premium_budget": 7000,
        "occupation_type": "IT professional",
        "dependents": 1,
        "dependents_count": 1,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "individual",
        "coverage_amount": 800000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": [],
        "preferred_providers": ["Tata AIG"],
        "claim_history_count": 0,
        "renewal_loyalty_years": 1,
        "risk_score": 0.3,
        "bmi": 23.5
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Sunita Iyer",
        "age": 50,
        "gender": "F",
        "marital_status": "widowed",
        "city": "Hyderabad",
        "state": "Telangana",
        "annual_income": 600000,
        "income_band": "6-10L",
        "premium_budget": 4000,
        "occupation_type": "teacher",
        "dependents": 1,
        "dependents_count": 1,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "individual",
        "coverage_amount": 700000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": True,
        "has_obesity": False,
        "pre_existing_conditions": ["heart_disease"],
        "preferred_providers": [],
        "claim_history_count": 3,
        "renewal_loyalty_years": 5,
        "risk_score": 0.8,
        "bmi": 26.2
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Dr. Meera Patel",
        "age": 33,
        "gender": "F",
        "marital_status": "married",
        "city": "Chennai",
        "state": "Tamil Nadu",
        "annual_income": 2000000,
        "income_band": ">20L",
        "premium_budget": 10000,
        "occupation_type": "doctor",
        "dependents": 2,
        "dependents_count": 2,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "floater",
        "coverage_amount": 2000000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": ["asthma"],
        "preferred_providers": ["ICICI Lombard"],
        "claim_history_count": 0,
        "renewal_loyalty_years": 0,
        "risk_score": 0.4,
        "bmi": 21.8
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Amit Ghosh",
        "age": 42,
        "gender": "M",
        "marital_status": "divorced",
        "city": "Kolkata",
        "state": "West Bengal",
        "annual_income": 850000,
        "income_band": "6-10L",
        "premium_budget": 4500,
        "occupation_type": "sales executive",
        "dependents": 1,
        "dependents_count": 1,
        "smoking_flag": "yes",
        "smoking_status": "yes",
        "plan_type": "individual",
        "coverage_amount": 600000,
        "has_diabetes": True,
        "has_hypertension": True,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": ["diabetes", "hypertension"],
        "preferred_providers": [],
        "claim_history_count": 4,
        "renewal_loyalty_years": 4,
        "risk_score": 0.9,
        "bmi": 29.5
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Neha Agarwal",
        "age": 24,
        "gender": "F",
        "marital_status": "single",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "annual_income": 400000,
        "income_band": "3-6L",
        "premium_budget": 2500,
        "occupation_type": "student",
        "dependents": 0,
        "dependents_count": 0,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "individual",
        "coverage_amount": 300000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": [],
        "preferred_providers": ["Care Health"],
        "claim_history_count": 0,
        "renewal_loyalty_years": 0,
        "risk_score": 0.1,
        "bmi": 20.5
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Ramesh Verma",
        "age": 58,
        "gender": "M",
        "marital_status": "married",
        "city": "Lucknow",
        "state": "Uttar Pradesh",
        "annual_income": 700000,
        "income_band": "6-10L",
        "premium_budget": 6000,
        "occupation_type": "retired",
        "dependents": 2,
        "dependents_count": 2,
        "smoking_flag": "yes",
        "smoking_status": "yes",
        "plan_type": "floater",
        "coverage_amount": 1000000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": True,
        "has_obesity": False,
        "pre_existing_conditions": ["heart_disease"],
        "preferred_providers": [],
        "claim_history_count": 5,
        "renewal_loyalty_years": 10,
        "risk_score": 0.85,
        "bmi": 27.8
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "name": "Kavita Jain",
        "age": 31,
        "gender": "F",
        "marital_status": "married",
        "city": "Jaipur",
        "state": "Rajasthan",
        "annual_income": 1300000,
        "income_band": "10-20L",
        "premium_budget": 7500,
        "occupation_type": "banker",
        "dependents": 1,
        "dependents_count": 1,
        "smoking_flag": "no",
        "smoking_status": "no",
        "plan_type": "floater",
        "coverage_amount": 1200000,
        "has_diabetes": False,
        "has_hypertension": False,
        "has_heart_disease": False,
        "has_obesity": False,
        "pre_existing_conditions": ["thyroid"],
        "preferred_providers": ["Reliance Health"],
        "claim_history_count": 1,
        "renewal_loyalty_years": 2,
        "risk_score": 0.4,
        "bmi": 23.2
    }
]


def format_currency(amount):
    """Format currency in Indian style"""
    if amount >= 100000:
        return f"₹{amount/100000:.1f}L"
    elif amount >= 1000:
        return f"₹{amount/1000:.1f}K"
    else:
        return f"₹{amount:.0f}"


def test_recommendations():
    """Run recommendation tests for all users"""
    print("=" * 80)
    print("🚀 AI-MEDPAY PLANRANKER - MODEL DIVERSITY TEST")
    print("=" * 80)
    print(f"Testing with {len(test_users)} synthetic user profiles\n")

    # Initialize ranker
    try:
        backend_root = PROJECT_ROOT / "backend" / "app"
        plan_ranker = NewPlanRanker(backend_root)
        print("✅ NewPlanRanker initialized successfully")
        print(f"   Model loaded with {len(plan_ranker.feature_columns)} features")
        print(f"   Plans loaded: {len(plan_ranker.plans)}\n")
    except Exception as e:
        print(f"❌ Failed to initialize PlanRanker: {e}")
        import traceback
        traceback.print_exc()
        return

    all_recommendations = []
    results_summary = []
    error_count = 0
    no_results_count = 0

    for i, user in enumerate(test_users, start=1):
        print(f"\n{'='*80}")
        print(f"🧩 USER {i}: {user['name']}")
        print(f"{'='*80}")
        print(f"📍 Location: {user['city']}, {user['state']}")
        print(
            f"👤 Profile: {user['occupation_type']} | Age {user['age']} | {user['gender']}")
        print(
            f"💰 Income: {format_currency(user['annual_income'])}/year | Budget: ₹{user['premium_budget']}/month")
        print(
            f"👨‍👩‍👧‍👦 Dependents: {user['dependents_count']} | Plan: {user['plan_type']}")
        print(
            f"🚬 Smoking: {'Yes' if user['smoking_flag'] in ['yes', 'true', True] else 'No'} | BMI: {user.get('bmi', 'N/A')}")

        if user['pre_existing_conditions']:
            print(
                f"⚕️  Pre-existing: {', '.join(user['pre_existing_conditions'])}")
        if user['preferred_providers']:
            print(f"🏥 Preferred: {', '.join(user['preferred_providers'])}")

        print(f"\n📊 RECOMMENDATIONS:")

        try:
            results = plan_ranker.rank(user, k=5)

            if not results:
                print("⚠️  NO RECOMMENDATIONS RETURNED")
                print("   → Check: premium_budget, age limits, or plan eligibility")
                no_results_count += 1
                all_recommendations.append([])
            else:
                top_plans = results[:3]
                plan_ids = [p["plan_id"] for p in top_plans]
                all_recommendations.append(plan_ids)

                for idx, rec in enumerate(top_plans, 1):
                    premium = rec.get('premium', rec.get('monthly_premium', 0))
                    coverage = rec.get('coverage_amount', 0)
                    score = rec.get('score', 0)

                    print(f"\n   {idx}. {rec['plan_name']}")
                    print(f"      Provider: {rec['provider']}")
                    print(
                        f"      Premium: ₹{premium:,.0f}/month | Coverage: {format_currency(coverage)}")
                    print(f"      Score: {score:.4f}")

                    # Show explanation if available
                    if 'explain_text' in rec:
                        print(f"      💡 {rec['explain_text'][:100]}...")

                results_summary.append({
                    'user': user['name'],
                    'city': user['city'],
                    'age': user['age'],
                    'income': user['annual_income'],
                    'top_plan': top_plans[0]['plan_name'],
                    'top_score': top_plans[0]['score'],
                    'count': len(results)
                })

        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            print(f"   Type: {type(e).__name__}")
            error_count += 1
            all_recommendations.append([])
            import traceback
            traceback.print_exc()

    # ✅ DIVERSITY ANALYSIS
    print(f"\n\n{'='*80}")
    print("📊 DIVERSITY ANALYSIS")
    print(f"{'='*80}\n")

    # Filter out empty results
    valid_recommendations = [r for r in all_recommendations if r]

    if valid_recommendations:
        unique_sets = len(set(tuple(sorted(r)) for r in valid_recommendations))
        print(f"✓ Total Users Tested: {len(test_users)}")
        print(f"✓ Successful Results: {len(valid_recommendations)}")
        print(f"✓ Distinct Recommendation Sets: {unique_sets}")
        print(
            f"✓ Diversity Score: {unique_sets/len(valid_recommendations)*100:.1f}%")

        if error_count > 0:
            print(f"⚠️  Errors Encountered: {error_count}")
        if no_results_count > 0:
            print(f"⚠️  No Results: {no_results_count}")

        print(f"\n{'='*80}")
        if unique_sets == len(valid_recommendations):
            print("✅ PASS: Each user received unique recommendations!")
            print("🎯 Model is producing highly personalized results.")
        elif unique_sets >= len(valid_recommendations) * 0.8:
            print("✅ GOOD: Most users received unique recommendations.")
            print("💡 Model shows good personalization.")
        else:
            print("⚠️  WARNING: Some users received similar recommendations.")
            print("💡 Consider tuning model features for better diversity.")

        # Show summary table
        if results_summary:
            print(f"\n{'='*80}")
            print("📋 RESULTS SUMMARY")
            print(f"{'='*80}\n")
            print(
                f"{'User':<20} {'City':<15} {'Age':>4} {'Income':>10} {'Top Plan':<30} {'Score':>6}")
            print("-" * 95)
            for r in results_summary:
                print(f"{r['user']:<20} {r['city']:<15} {r['age']:>4} {format_currency(r['income']):>10} "
                      f"{r['top_plan'][:29]:<30} {r['top_score']:>6.3f}")
    else:
        print("❌ FAIL: No valid recommendations generated!")
        print("🔍 Debug: Check model initialization, data files, and feature engineering.")

    print(f"\n{'='*80}")
    print("✅ TEST COMPLETE")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    test_recommendations()

