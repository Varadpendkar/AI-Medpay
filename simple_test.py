#!/usr/bin/env python3
"""Simple test for get-quote route"""

from backend.app.main import app
import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'


print("🧪 Flask Test Client - Get Quote Form")
print("=" * 50)

with app.test_client() as client:
    print("🔍 Testing GET /get-quote...")
    get_response = client.get('/get-quote')
    print(f"   Status: {get_response.status_code}")

    if get_response.status_code == 200:
        print("   ✅ GET works!")

        print("\n🚀 Testing POST /get-quote...")
        form_data = {
            'full-name': 'John Doe',
            'age': '30',
            'email': 'john.doe@example.com',
            'phone': '9876543210',
            'city': 'Mumbai',
            'coverage-type': 'individual',
            'family-members': '1',
            'sum-insured': '500000',
            'payment-mode': 'annual',
            'budget-range': '10000',
            'health-condition': 'excellent'
        }

        post_response = client.post('/get-quote', data=form_data)
        print(f"   Status: {post_response.status_code}")
        print(f"   Content-Type: {post_response.content_type}")

        if post_response.status_code == 200:
            data = post_response.get_data(as_text=True)

            if 'application/json' in str(post_response.content_type):
                print("   ❌ Still returning JSON")
                print(f"   Content preview: {data[:200]}...")
            elif 'text/html' in str(post_response.content_type):
                print("   ✅ Returning HTML!")

                # Check for key elements
                has_recommendations = 'recommendation-card' in data
                has_success = 'Perfect Match Found' in data
                has_confetti = 'confetti' in data

                print(f"   🎯 Has recommendations: {has_recommendations}")
                print(f"   🎉 Has success message: {has_success}")
                print(f"   🎊 Has confetti: {has_confetti}")

                if has_recommendations and has_success:
                    print("\n🎉 SUCCESS: Form fix is working perfectly!")
                else:
                    print("\n⚠️ HTML returned but missing some elements")
            else:
                print(
                    f"   ❓ Unexpected content type: {post_response.content_type}")
        else:
            print(f"   ❌ POST failed: {post_response.status_code}")
    else:
        print(f"   ❌ GET failed: {get_response.status_code}")

print("\n✨ Test completed!")
