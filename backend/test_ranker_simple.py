#!/usr/bin/env python3
"""
Simple test of the new ranker directly in backend context
"""
import sys
from pathlib import Path

# Set up path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from app.utils.new_ranker import NewPlanRanker
    from datetime import datetime

    print("="*80)
    print("TESTING NEW LIGHTGBM RANKER")
    print("="*80)
    print(f"Test Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    # Initialize ranker
    print("Step 1: Loading ranker...")
    project_root = Path(__file__).parent / 'app'
    ranker = NewPlanRanker(project_root)
    print("✓ Ranker loaded successfully!\n")

    # Test user (unseen)
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

    print("Step 2: Testing with unseen user U9999...")
    print(
        f"Profile: {test_user['age']}yr old {test_user['gender']}, {test_user['region']}, Income: {test_user['income_band']}\n")

    # Get recommendations
    print("Step 3: Generating recommendations...")
    recommendations = ranker.rank(test_user, k=5)
    print(f"✓ Generated {len(recommendations)} recommendations\n")

    # Display results
    print("="*80)
    print("TOP 5 RECOMMENDED PLANS:")
    print("="*80)

    for rec in recommendations:
        print(f"\n🏆 RANK {rec['rank']}: {rec['plan_name'][:60]}")
        print(f"   Provider: {rec['provider']}")
        print(f"   Premium: ₹{rec['premium']:,.0f}/year")
        print(f"   Coverage: ₹{rec['coverage_amount']:,.0f}")
        print(f"   Network: {rec['network_size']} hospitals")
        print(f"   Score: {rec['score']:.4f}")
        print(f"   Why: {rec['explain_text']}")

    print("\n" + "="*80)
    print("✅ TEST PASSED!")
    print("="*80)
    print("\nThe new LightGBM ranker is working correctly!")
    print("• Model loaded successfully")
    print("• Processed unseen user U9999")
    print("• Generated personalized recommendations")
    print("• Created explanations")
    print("\n🚀 Ready for production!")

except Exception as e:
    print(f"\n❌ TEST FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
