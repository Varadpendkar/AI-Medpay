#!/usr/bin/env python3
"""Debug script to check Flask routes and app configuration"""

import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'

try:
    from backend.app.main import app

    print("🔍 Flask App Configuration Debug")
    print("=" * 50)

    print(f"📱 App name: {app.name}")
    print(f"🔧 Debug mode: {app.debug}")
    print(f"🔐 Secret key set: {'Yes' if app.secret_key else 'No'}")

    print("\n📍 Registered Routes:")
    print("-" * 30)
    for rule in app.url_map.iter_rules():
        methods = ', '.join(rule.methods - {'HEAD', 'OPTIONS'})
        print(f"  {rule.endpoint:30} {str(rule.rule):25} [{methods}]")

    print("\n🏭 Registered Blueprints:")
    print("-" * 30)
    for name, blueprint in app.blueprints.items():
        print(f"  {name}: {blueprint.name}")

    # Test if we can create a test client
    print(f"\n🧪 Test Client Creation: ", end="")
    try:
        client = app.test_client()
        print("✅ Success")

        # Test the route
        print(f"\n🌐 Testing GET /get-quote: ", end="")
        response = client.get('/get-quote')
        print(f"Status {response.status_code}")
        if response.status_code == 403:
            print("❌ 403 Forbidden - likely authentication issue")
        elif response.status_code == 404:
            print("❌ 404 Not Found - route not registered")
        elif response.status_code == 200:
            print("✅ 200 OK - route working")

    except Exception as e:
        print(f"❌ Failed: {e}")

except ImportError as e:
    print(f"❌ Import Error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
