#!/usr/bin/env python3
"""
Test script to verify leads persistence is working correctly.
This simulates a Get Quote submission and verifies data is saved to leads.db
"""
import sqlite3
from app.services.persistence import save_lead_and_recs, get_lead_stats
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Test data - simulating a user profile and recommendations
test_user_profile = {
    'age': 35,
    'gender': 'male',
    'income': 800000,
    'annual_income': 800000,
    'city': 'Mumbai',
    'state': 'Maharashtra',
    'marital_status': 'married',
    'dependents': 1,
    'dependents_count': 1,
    'smoking_flag': False,
    'smoking_status': 'no',
    'plan_type': 'family',
    'coverage_amount_preference': 500000,
    'premium_budget': 8000,
    'occupation_type': 'salaried',
    'bmi': 24.5
}

test_recommendations = [
    {
        'plan_id': 'PL001',
        'plan_name': 'HDFC Health Plus',
        'provider': 'HDFC ERGO',
        'score': 0.95,
        'premium': 7500,
        'coverage_amount': 500000
    },
    {
        'plan_id': 'PL002',
        'plan_name': 'Star Family Care',
        'provider': 'Star Health',
        'score': 0.87,
        'premium': 8200,
        'coverage_amount': 500000
    },
    {
        'plan_id': 'PL003',
        'plan_name': 'ICICI Complete Health',
        'provider': 'ICICI Lombard',
        'score': 0.82,
        'premium': 7800,
        'coverage_amount': 500000
    }
]

print("🧪 Testing Leads Persistence System")
print("=" * 60)

# Get initial stats
print("\n📊 Initial Database Stats:")
stats_before = get_lead_stats()
print(f"   Total leads: {stats_before['total_leads']}")
print(f"   Total recommendations: {stats_before['total_recommendations']}")
print(f"   Recent leads (7d): {stats_before['recent_leads_7d']}")

# Save test lead
print("\n💾 Saving test lead...")
try:
    lead_id = save_lead_and_recs(
        user_id='test_user_123',
        profile_dict=test_user_profile,
        recommendations_list=test_recommendations,
        ip='127.0.0.1',
        source='test_script'
    )
    print(f"✅ Successfully saved lead with ID: {lead_id}")
except Exception as e:
    print(f"❌ Failed to save lead: {e}")
    sys.exit(1)

# Verify the save
print("\n🔍 Verifying saved data...")
DB = os.path.join(os.path.dirname(__file__), '..', 'data', 'leads.db')
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Check lead was saved
lead = cur.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
if lead:
    print(f"✅ Lead record found:")
    print(f"   User ID: {lead['user_id']}")
    print(f"   Source: {lead['source']}")
    print(f"   IP: {lead['ip']}")
    print(f"   Timestamp: {lead['timestamp']}")
else:
    print(f"❌ Lead {lead_id} not found in database!")
    sys.exit(1)

# Check recommendations were saved
recs = cur.execute(
    "SELECT * FROM recommendations WHERE lead_id = ? ORDER BY rank", (lead_id,)).fetchall()
print(f"\n✅ Found {len(recs)} recommendations:")
for rec in recs:
    print(
        f"   Rank {rec['rank']}: {rec['plan_name']} ({rec['provider']}) - Score: {rec['model_score']:.2f}")

conn.close()

# Get final stats
print("\n📊 Final Database Stats:")
stats_after = get_lead_stats()
print(
    f"   Total leads: {stats_after['total_leads']} (+{stats_after['total_leads'] - stats_before['total_leads']})")
print(
    f"   Total recommendations: {stats_after['total_recommendations']} (+{stats_after['total_recommendations'] - stats_before['total_recommendations']})")
print(f"   Recent leads (7d): {stats_after['recent_leads_7d']}")

print("\n" + "=" * 60)
print("✅ All tests passed! Leads persistence is working correctly.")
print("=" * 60)
