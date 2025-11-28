#!/usr/bin/env python3
"""
Test the Flask API with the new model
"""
import requests
import json

print("="*80)
print("TESTING FLASK API WITH NEW MODEL")
print("="*80)

# Test the API endpoint
url = "http://127.0.0.1:5001/api/recommendations"
params = {
    "user_id": "U9999",  # Unseen user
    "limit": 5
}

print(f"\nTesting: {url}")
print(f"Parameters: {params}\n")

try:
    response = requests.get(url, params=params, timeout=10)

    if response.status_code == 200:
        data = response.json()

        print("✅ API Response Successful!\n")
        print(f"User ID: {data.get('user_id')}")
        print(f"Model Version: {data.get('model_version')}")
        print(f"Timestamp: {data.get('timestamp')}")
        print(
            f"Number of Recommendations: {len(data.get('recommendations', []))}\n")

        print("="*80)
        print("TOP RECOMMENDATIONS:")
        print("="*80)

        for rec in data.get('recommendations', [])[:5]:
            print(
                f"\n🏆 Rank {rec.get('rank')}: {rec.get('plan_name', 'N/A')[:60]}")
            print(f"   Provider: {rec.get('provider', 'N/A')}")
            print(f"   Premium: ₹{rec.get('monthly_premium', 0):,.0f}/year")
            print(f"   Coverage: ₹{rec.get('coverage_amount', 0):,.0f}")
            print(f"   Score: {rec.get('score', 0):.4f}")
            print(f"   Explanation: {rec.get('explain_text', 'N/A')}")

        print("\n" + "="*80)
        print("✅ TEST PASSED - API IS WORKING!")
        print("="*80)

    else:
        print(f"❌ API Error: Status Code {response.status_code}")
        print(response.text)

except requests.exceptions.ConnectionError:
    print("❌ ERROR: Could not connect to Flask server")
    print("Please make sure the server is running on http://127.0.0.1:5001")
except Exception as e:
    print(f"❌ ERROR: {str(e)}")
