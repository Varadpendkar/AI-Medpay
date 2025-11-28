#!/usr/bin/env python3
"""
Debug Test Harness - Investigate constant 0.1000 score issue
"""
from app.utils.new_ranker import NewPlanRanker
from pathlib import Path
import sys
import os
import uuid
import logging

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("debug_run_tests")

# Initialize ranker
project_root = Path(__file__).parent / "backend" / "app"
plan_ranker = NewPlanRanker(project_root)

# ========== TEST USER PROFILES ==========

# Single user for deep dump
single_user = {
    "user_id": f"user_{uuid.uuid4()}",
    "age": 30, "gender": "F", "marital_status": "single",
    "city": "Mumbai", "state": "Maharashtra", "income": 2400000,
    "premium_budget": 20000, "occupation_type": "salaried",
    "dependents_count": 2, "smoking_flag": False, "plan_type": "individual",
    "pre_existing_conditions": ["diabetes"], "preferred_providers": [],
    "income_band": "10-20L", "region": "West"
}

# Two extremes
young_healthy = {
    "user_id": f"user_{uuid.uuid4()}",
    "age": 24, "gender": "F", "marital_status": "single",
    "city": "Ahmedabad", "state": "Gujarat", "income": 400000,
    "premium_budget": 2500, "occupation_type": "student",
    "dependents_count": 0, "smoking_flag": False, "plan_type": "individual",
    "pre_existing_conditions": [], "preferred_providers": [],
    "income_band": "<3L", "region": "West"
}

old_sick = {
    "user_id": f"user_{uuid.uuid4()}",
    "age": 58, "gender": "M", "marital_status": "married",
    "city": "Lucknow", "state": "Uttar Pradesh", "income": 700000,
    "premium_budget": 6000, "occupation_type": "retired",
    "dependents_count": 2, "smoking_flag": True, "plan_type": "floater",
    "pre_existing_conditions": ["heart_disease"], "preferred_providers": [],
    "income_band": "3-6L", "region": "North"
}

# 10 diverse users
test_users = [
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 26, "gender": "F", "marital_status": "single",
        "city": "Mumbai", "state": "Maharashtra", "income": 450000,
        "premium_budget": 3000, "occupation_type": "salaried",
        "dependents_count": 0, "smoking_flag": False, "plan_type": "individual",
        "pre_existing_conditions": [], "preferred_providers": [],
        "income_band": "<3L", "region": "West"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 38, "gender": "M", "marital_status": "married",
        "city": "Delhi", "state": "Delhi", "income": 1500000,
        "premium_budget": 8000, "occupation_type": "self_employed",
        "dependents_count": 3, "smoking_flag": False, "plan_type": "floater",
        "pre_existing_conditions": ["diabetes"], "preferred_providers": [],
        "income_band": "10-20L", "region": "North"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 45, "gender": "F", "marital_status": "married",
        "city": "Pune", "state": "Maharashtra", "income": 900000,
        "premium_budget": 5000, "occupation_type": "salaried",
        "dependents_count": 3, "smoking_flag": False, "plan_type": "floater",
        "pre_existing_conditions": ["hypertension"], "preferred_providers": [],
        "income_band": "6-10L", "region": "West"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 29, "gender": "M", "marital_status": "single",
        "city": "Bangalore", "state": "Karnataka", "income": 1200000,
        "premium_budget": 4000, "occupation_type": "salaried",
        "dependents_count": 0, "smoking_flag": False, "plan_type": "individual",
        "pre_existing_conditions": [], "preferred_providers": [],
        "income_band": "10-20L", "region": "South"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 50, "gender": "F", "marital_status": "married",
        "city": "Hyderabad", "state": "Telangana", "income": 600000,
        "premium_budget": 4500, "occupation_type": "salaried",
        "dependents_count": 2, "smoking_flag": False, "plan_type": "floater",
        "pre_existing_conditions": ["heart_disease"], "preferred_providers": [],
        "income_band": "3-6L", "region": "South"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 33, "gender": "F", "marital_status": "married",
        "city": "Chennai", "state": "Tamil Nadu", "income": 2000000,
        "premium_budget": 10000, "occupation_type": "salaried",
        "dependents_count": 1, "smoking_flag": False, "plan_type": "floater",
        "pre_existing_conditions": ["asthma"], "preferred_providers": [],
        "income_band": ">20L", "region": "South"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 42, "gender": "M", "marital_status": "married",
        "city": "Kolkata", "state": "West Bengal", "income": 850000,
        "premium_budget": 6000, "occupation_type": "self_employed",
        "dependents_count": 4, "smoking_flag": True, "plan_type": "floater",
        "pre_existing_conditions": ["diabetes", "hypertension"], "preferred_providers": [],
        "income_band": "6-10L", "region": "East"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 24, "gender": "F", "marital_status": "single",
        "city": "Ahmedabad", "state": "Gujarat", "income": 400000,
        "premium_budget": 2500, "occupation_type": "student",
        "dependents_count": 0, "smoking_flag": False, "plan_type": "individual",
        "pre_existing_conditions": [], "preferred_providers": [],
        "income_band": "<3L", "region": "West"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 58, "gender": "M", "marital_status": "married",
        "city": "Lucknow", "state": "Uttar Pradesh", "income": 700000,
        "premium_budget": 6000, "occupation_type": "retired",
        "dependents_count": 2, "smoking_flag": True, "plan_type": "floater",
        "pre_existing_conditions": ["heart_disease"], "preferred_providers": [],
        "income_band": "3-6L", "region": "North"
    },
    {
        "user_id": f"user_{uuid.uuid4()}",
        "age": 31, "gender": "F", "marital_status": "single",
        "city": "Jaipur", "state": "Rajasthan", "income": 1300000,
        "premium_budget": 7000, "occupation_type": "salaried",
        "dependents_count": 1, "smoking_flag": False, "plan_type": "individual",
        "pre_existing_conditions": ["thyroid"], "preferred_providers": [],
        "income_band": "10-20L", "region": "North"
    }
]

# ========== TEST FUNCTIONS ==========


def run_single_dump(user):
    """Deep dive into single user's feature matrix and predictions"""
    print("\n\n" + "="*80)
    print("=== SINGLE USER DEEP DUMP ===")
    print("="*80)
    print(
        f"User: age={user['age']}, city={user['city']}, income={user['income']}, budget={user['premium_budget']}")
    print(
        f"      conditions={user['pre_existing_conditions']}, smoking={user['smoking_flag']}")

    try:
        results = plan_ranker.rank(user, k=5)

        if results:
            print(f"\n✓ Received {len(results)} recommendations")
            print("\nTop 5 Plans:")
            for i, rec in enumerate(results, 1):
                print(
                    f"  {i}. {rec['plan_name']} - Score: {rec['score']:.6f}, Premium: ₹{rec['premium']:,.0f}")
        else:
            print("✗ No recommendations returned")

    except Exception as e:
        print(f"✗ Ranking failed: {e}")
        logger.exception("Single user dump failed")

    print("\n⚠️  Check logs above for detailed feature matrix info")
    print("="*80)


def run_two_extremes(u1, u2):
    """Compare two extreme users to see if features differ"""
    print("\n\n" + "="*80)
    print("=== TWO EXTREMES COMPARISON ===")
    print("="*80)

    print("\n🔵 User 1 (Young & Healthy):")
    print(
        f"   age={u1['age']}, income=₹{u1['income']:,}, budget=₹{u1['premium_budget']:,}")
    print(
        f"   conditions={u1['pre_existing_conditions']}, smoking={u1['smoking_flag']}")

    print("\n🔴 User 2 (Older & Sick):")
    print(
        f"   age={u2['age']}, income=₹{u2['income']:,}, budget=₹{u2['premium_budget']:,}")
    print(
        f"   conditions={u2['pre_existing_conditions']}, smoking={u2['smoking_flag']}")

    try:
        results1 = plan_ranker.rank(u1, k=3)
        print(f"\n🔵 User 1 got {len(results1)} recommendations:")
        for i, rec in enumerate(results1, 1):
            print(f"   {i}. {rec['plan_name']} - Score: {rec['score']:.6f}")
    except Exception as e:
        print(f"✗ User 1 ranking failed: {e}")

    try:
        results2 = plan_ranker.rank(u2, k=3)
        print(f"\n🔴 User 2 got {len(results2)} recommendations:")
        for i, rec in enumerate(results2, 1):
            print(f"   {i}. {rec['plan_name']} - Score: {rec['score']:.6f}")
    except Exception as e:
        print(f"✗ User 2 ranking failed: {e}")

    print("\n⚠️  Check logs above to compare feature matrices between users")
    print("="*80)


def run_full_diversity(users):
    """Test diversity across all 10 users"""
    print("\n\n" + "="*80)
    print("=== FULL DIVERSITY TEST (10 Users) ===")
    print("="*80)

    all_top3 = []
    all_scores = []

    for i, u in enumerate(users, start=1):
        print(
            f"\nUser {i}: {u['city']}, age {u['age']}, income ₹{u['income']:,}, budget ₹{u['premium_budget']:,}")
        print(
            f"        conditions={u['pre_existing_conditions']}, smoking={u['smoking_flag']}")

        try:
            results = plan_ranker.rank(u, k=3)
        except Exception as e:
            print(f"  ✗ Rank failed: {e}")
            results = []

        if not results:
            print("  ✗ No results.")
            all_top3.append(None)
            all_scores.append([])
        else:
            top3_ids = [r.get("plan_id") for r in results[:3]]
            top3_scores = [r.get("score") for r in results[:3]]
            all_top3.append(tuple(sorted(top3_ids)))
            all_scores.append(top3_scores)

            print(f"  Top 3:")
            for j, r in enumerate(results[:3], 1):
                print(
                    f"    {j}. {r['plan_name'][:40]:40s} - Score: {r['score']:.6f}")

    # Calculate diversity
    unique_sets = set([x for x in all_top3 if x])
    total_users = len([x for x in all_top3 if x])

    print("\n" + "="*80)
    print("📊 DIVERSITY ANALYSIS:")
    print("="*80)
    print(f"✓ Total Users Tested: {len(users)}")
    print(f"✓ Successful Results: {total_users}")
    print(f"✓ Distinct Recommendation Sets: {len(unique_sets)}")
    print(f"✓ Diversity Score: {len(unique_sets)/total_users*100:.1f}%")

    # Check score variance
    all_flat_scores = [s for sublist in all_scores for s in sublist]
    if all_flat_scores:
        import numpy as np
        unique_scores = len(set([round(s, 6) for s in all_flat_scores]))
        print(f"✓ Unique Score Values: {unique_scores}")
        print(
            f"✓ Score Range: {min(all_flat_scores):.6f} to {max(all_flat_scores):.6f}")
        print(f"✓ Score Std Dev: {np.std(all_flat_scores):.6f}")

    if len(unique_sets) == 1:
        print("\n⚠️  CRITICAL: All users received IDENTICAL recommendations!")
        print("    This indicates the model is NOT personalizing.")
    elif len(unique_sets) < total_users * 0.5:
        print("\n⚠️  WARNING: Low diversity detected (< 50% unique sets)")
    else:
        print("\n✓ PASS: Good diversity in recommendations")

    print("="*80)

# ========== MAIN EXECUTION ==========


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🧪 DEBUG TEST HARNESS - Investigating Constant 0.1000 Score Issue")
    print("="*80)

    # Run all tests
    run_single_dump(single_user)
    run_two_extremes(young_healthy, old_sick)
    run_full_diversity(test_users)

    print("\n\n" + "="*80)
    print("✅ ALL TESTS COMPLETED")
    print("="*80)
    print("\n📝 Check the logs above for:")
    print("   1. Feature matrix shape & unique rows")
    print("   2. Constant/low-variance features")
    print("   3. Raw prediction values and variance")
    print("   4. Score diversity across users")
    print("\n💡 Next steps based on findings:")
    print("   - If features are identical → Fix _create_derived_features()")
    print("   - If raw preds are constant → Model issue (reload/retrain)")
    print("   - If scores constant but preds vary → Fix normalization")
    print("="*80 + "\n")
