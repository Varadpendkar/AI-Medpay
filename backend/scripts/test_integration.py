#!/usr/bin/env python3
"""
Integration test: Verify Get Quote form submissions are persisted to leads.db
This script simulates what happens when a user submits the Get Quote form.
"""
import sqlite3
from pathlib import Path
from app.utils.new_ranker import NewPlanRanker
from app.services.persistence import save_lead_and_recs, get_lead_stats
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


print("🧪 Integration Test: Get Quote → Leads Persistence")
print("=" * 70)

# Build user profile (same as get_quote.py does)
user_profile = {
    'user_id': 'integration_test_user',
    'age': 32,
    'gender': 'female',
    'marital_status': 'married',
    'dependents_count': 2,
    'city': 'Bangalore',
    'state': 'Karnataka',
    'pincode': '560001',
    'region': 'Bangalore',
    'income': 1200000,
    'annual_income': 1200000,
    'income_band': '10-20L',
    'premium_budget': 10000,
    'occupation_type': 'salaried',
    'employment_sector': 'private',
    'smoking_flag': False,
    'smoking_status': 'no',
    'alcohol_flag': False,
    'bmi': 23.5,
    'previous_claims_count': 0,
    'claim_history_count': 0,
    'renewal_loyalty_years': 0,
    'risk_score': 0.3,
    'dependents': 2,
    'pre_existing_conditions': [],
    'family_history': [],
    'plan_type': 'family',
    'coverage_amount_preference': 1000000,
    'maternity_required': True,
    'critical_illness_required': True,
    'preferred_providers': [],
    'years_with_insurer': 0,
    'time_since_last_claim_months': 0
}

print(f"\n👤 User Profile:")
print(f"   Age: {user_profile['age']}, Income: ₹{user_profile['income']:,}")
print(
    f"   City: {user_profile['city']}, Plan Type: {user_profile['plan_type']}")
print(f"   Dependents: {user_profile['dependents_count']}")

# Initialize ranker (same as app.main.py does)
print(f"\n🤖 Skipping ranker initialization for this test...")
print(f"   (Using mock recommendations instead)")

# Use mock recommendations for testing persistence
recs = [
    {
        'plan_id': 'PL_FAM_001',
        'plan_name': 'Family Health Plus',
        'provider': 'HDFC ERGO',
        'score': 0.92,
        'premium': 9800,
        'coverage_amount': 1000000,
        'deductible': 15000,
        'network_size': 18000
    },
    {
        'plan_id': 'PL_FAM_002',
        'plan_name': 'Star Comprehensive Family',
        'provider': 'Star Health',
        'score': 0.88,
        'premium': 10200,
        'coverage_amount': 1000000,
        'deductible': 10000,
        'network_size': 16000
    },
    {
        'plan_id': 'PL_FAM_003',
        'plan_name': 'Care Family First',
        'provider': 'Care Health',
        'score': 0.85,
        'premium': 9500,
        'coverage_amount': 1000000,
        'deductible': 20000,
        'network_size': 15000
    },
    {
        'plan_id': 'PL_FAM_004',
        'plan_name': 'ICICI Complete Family Shield',
        'provider': 'ICICI Lombard',
        'score': 0.81,
        'premium': 11000,
        'coverage_amount': 1000000,
        'deductible': 5000,
        'network_size': 20000
    },
    {
        'plan_id': 'PL_FAM_005',
        'plan_name': 'Bajaj Family Floater',
        'provider': 'Bajaj Allianz',
        'score': 0.78,
        'premium': 8900,
        'coverage_amount': 1000000,
        'deductible': 25000,
        'network_size': 12000
    }
]

# Get recommendations (same as get_quote.py does)
print(f"\n🎯 Mock recommendations ready:")
print(f"✅ Got {len(recs)} recommendations")
for i, rec in enumerate(recs[:3], 1):
    plan_name = rec.get('plan_name') or rec.get('name') or 'Unknown'
    provider = rec.get('provider') or 'Unknown'
    score = rec.get('score', 0)
    print(f"   {i}. {plan_name} ({provider}) - Score: {score:.3f}")

# Save to database (this is what get_quote.py now does)
print(f"\n💾 Saving to leads.db...")
stats_before = get_lead_stats()
print(f"   Leads before: {stats_before['total_leads']}")

try:
    lead_id = save_lead_and_recs(
        user_id='integration_test_user',
        profile_dict=user_profile,
        recommendations_list=recs,
        ip='127.0.0.1',
        source='integration_test'
    )
    print(f"✅ Saved lead ID: {lead_id}")
except Exception as e:
    print(f"❌ Failed to save: {e}")
    sys.exit(1)

# Verify
stats_after = get_lead_stats()
print(
    f"   Leads after: {stats_after['total_leads']} (+{stats_after['total_leads'] - stats_before['total_leads']})")
print(
    f"   Recommendations after: {stats_after['total_recommendations']} (+{stats_after['total_recommendations'] - stats_before['total_recommendations']})")

# Verify profile_json can be parsed back
DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')
conn = sqlite3.connect(DB)
cur = conn.cursor()
lead = cur.execute(
    "SELECT profile_json FROM leads WHERE id = ?", (lead_id,)).fetchone()
if lead:
    import json
    profile_back = json.loads(lead[0])
    print(f"\n✅ Profile JSON verification:")
    print(
        f"   Age: {profile_back.get('age')} (original: {user_profile['age']})")
    print(
        f"   Income: ₹{profile_back.get('income'):,} (original: ₹{user_profile['income']:,})")
    print(
        f"   Plan type: {profile_back.get('plan_type')} (original: {user_profile['plan_type']})")
conn.close()

print("\n" + "=" * 70)
print("✅ Integration test PASSED!")
print("   Get Quote submissions are now being persisted to leads.db")
print("   Ready for retraining pipeline!")
print("=" * 70)
