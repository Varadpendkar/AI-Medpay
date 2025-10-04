#!/usr/bin/env python3
"""Test the root route specifically"""

from backend.app.main import app
import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'


print("🧪 Testing Root Route")
print("=" * 30)

with app.test_client() as client:
    print("🔍 Testing GET /")
    try:
        response = client.get('/')
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.content_type}")

        if response.status_code == 200:
            print("   ✅ Root route works!")
            data = response.get_data(as_text=True)
            has_title = 'AI-MEDPAY' in data
            has_content = len(data) > 100
            print(f"   📄 Has title: {has_title}")
            print(f"   📝 Has content: {has_content}")
        elif response.status_code == 404:
            print("   ❌ 404 Not Found")
            print("   🔍 Available routes:")
            for rule in app.url_map.iter_rules():
                if rule.rule == '/':
                    print(f"      Found route: {rule.endpoint} -> {rule.rule}")
        elif response.status_code == 500:
            print("   ❌ 500 Internal Server Error")
            data = response.get_data(as_text=True)
            print(f"   Error details: {data[:200]}...")
        else:
            print(f"   ❓ Unexpected status: {response.status_code}")

    except Exception as e:
        print(f"   ❌ Exception: {e}")

print("\n✨ Test completed!")
