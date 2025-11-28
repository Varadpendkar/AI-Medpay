#!/usr/bin/env python3
"""
Quick test script to simulate form submission and verify the fix
"""
import requests
import json

# Test data matching the user from the screen recording
test_data = {
    'user_id': 'test_user_123',
    'age': '30',
    'gender': 'F',
    'marital_status': 'single',
    'dependents_count': '2',
    'city': 'Mumbai',
    'state': 'Maharashtra',
    'pincode': '400001',
    'income': '2400000',  # 24 lakhs
    'premium_budget': '20000',  # 20,000/month
    'occupation_type': 'salaried',
    'employment_sector': 'private',
    'smoking_flag': 'false',  # Ex-smoker = false currently
    'alcohol_flag': 'false',
    'bmi': '24.5',
    'previous_claims_count': '1',
    'pre_existing_diabetes': 'on',  # Checkbox checked
    'plan_type': 'floater',
    'coverage_amount_preference': '2000000',  # 20 lakhs
    'maternity_required': 'false',
    'critical_illness_required': 'true',
    'years_with_insurer': '3',
    'time_since_last_claim_months': '0'
}

print("🧪 Testing Get Quote Form Submission")
print("=" * 60)
print(f"\n📋 Test Data:")
for key, value in test_data.items():
    print(f"  {key}: {value}")

print("\n\n🚀 Submitting to http://127.0.0.1:5001/get-quote ...")

try:
    response = requests.post(
        'http://127.0.0.1:5001/get-quote',
        data=test_data,
        allow_redirects=False
    )

    print(f"\n✅ Response Status: {response.status_code}")
    print(f"📏 Response Length: {len(response.text)} bytes")

    # Check if we got recommendations in the response
    if 'No recommendations available' in response.text:
        print("\n⚠️  Response contains: 'No recommendations available'")
        print("   This means the ranker failed but fallback should activate!")
    elif 'plan_name' in response.text.lower() or 'star health' in response.text.lower():
        print("\n✅ SUCCESS! Response contains recommendation data")
        # Count how many recommendation cards
        card_count = response.text.count('card-container')
        if card_count > 0:
            print(f"   Found {card_count} recommendation cards")
    else:
        print("\n❓ Unexpected response")

    # Save response for inspection
    with open('/tmp/get_quote_test_response.html', 'w') as f:
        f.write(response.text)
    print(f"\n💾 Full response saved to: /tmp/get_quote_test_response.html")

except requests.exceptions.ConnectionError:
    print("\n❌ ERROR: Could not connect to server")
    print("   Make sure Flask server is running on http://127.0.0.1:5001")
except Exception as e:
    print(f"\n❌ ERROR: {type(e).__name__}: {e}")

print("\n" + "=" * 60)
print("Test complete!")
