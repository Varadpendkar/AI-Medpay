#!/usr/bin/env python3
"""
Test script to verify PlanRanker fix - sends a test request to the get-quote endpoint
"""
import requests
import json

# Test user profile
test_data = {
    'age': '35',
    'gender': 'male',
    'annual_income': '1200000',
    'dependents': '2',
    'region': 'pune',
    'urban_rural': 'urban',
    'marital_status': 'married',
    'city': 'Pune',
    'state': 'Maharashtra',
    'occupation_type': 'salaried',
    'plan_type': 'floater',
    'coverage_amount': '2000000',
    'payment_mode': 'monthly',
    'preferred_providers': '',
    'existing_policy': 'no',
    'premium_budget': '10000',
    'smoking_flag': 'false',
    'has_diabetes': '0',
    'has_hypertension': '0',
    'has_heart_disease': '0',
    'claim_history_count': '1',
    'renewal_loyalty_years': '3'
}

print("="*80)
print("🧪 TESTING PLANRANKER FIX")
print("="*80)
print(f"\n📋 Test Profile:")
print(
    f"   Age: {test_data['age']}, Income: ₹{int(test_data['annual_income']):,}")
print(
    f"   Dependents: {test_data['dependents']}, Smoking: {test_data['smoking_flag']}")
print(
    f"   Plan Type: {test_data['plan_type']}, Budget: ₹{test_data['premium_budget']}")

print("\n🌐 Sending POST request to http://localhost:5001/get-quote...")

try:
    response = requests.post(
        'http://localhost:5001/get-quote',
        data=test_data,
        timeout=30
    )

    print(f"\n✅ Response Status: {response.status_code}")

    # Check if we got HTML response (form page)
    if 'text/html' in response.headers.get('Content-Type', ''):
        # Look for indicators in the HTML
        html_content = response.text

        # Check for fallback message
        if 'fallback' in html_content.lower() or 'no recommendations' in html_content.lower():
            print("⚠️  WARNING: Fallback recommendations detected!")
            print("   The model may still have issues.")
        elif 'plan-card' in html_content or 'recommendation' in html_content:
            print("🎉 SUCCESS: Personalized recommendations generated!")

            # Count plan cards
            plan_count = html_content.count(
                'plan-card') or html_content.count('plan_card')
            if plan_count > 0:
                print(
                    f"   Found {plan_count} plan recommendations in response")
        else:
            print(
                "ℹ️  Response received but couldn't determine if recommendations were generated")

    else:
        print(f"Response: {response.text[:500]}")

except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to server at http://localhost:5001")
    print("   Make sure the Flask server is running:")
    print("   cd /Users/varadpendkar/Documents/project/backend")
    print("   PYTHONPATH=/Users/varadpendkar/Documents/project/backend python -m app.main")
except Exception as e:
    print(f"❌ ERROR: {e}")

print("\n" + "="*80)
print("💡 TIP: Check the server logs for detailed debugging info:")
print("   Look for: '✅ Final feature matrix shape: (204, 18)'")
print("   Look for: '🎯 Model predictions generated successfully'")
print("="*80)
