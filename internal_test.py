#!/usr/bin/env python3
"""Test the get-quote route using Flask's internal test client"""

import sys
import os
sys.path.insert(0, '/Users/varadpendkar/Documents/project')
os.environ['PYTHONPATH'] = '/Users/varadpendkar/Documents/project'

try:
    from backend.app.main import app

    print("🧪 Flask Internal Test Client")
    print("=" * 50)

    # Create test client
    client = app.test_client()

    print("🔍 Step 1: Testing GET /get-quote")
    get_response = client.get('/get-quote')
    print(f"   Status: {get_response.status_code}")
    print(f"   Content-Type: {get_response.content_type}")

    if get_response.status_code == 200:
        print("   ✅ GET request successful")

        # Check if it contains form elements
        data = get_response.get_data(as_text=True)
        has_form = '<form' in data
        has_orb = 'orb-wrapper' in data
        has_wizard = 'wizard-step' in data

        print(f"   📋 Contains form: {has_form}")
        print(f"   🌟 Contains 3D orb: {has_orb}")
        print(f"   🧙 Contains wizard steps: {has_wizard}")

    elif get_response.status_code == 403:
        print("   ❌ 403 Forbidden")
    else:
        print(f"   ❌ Unexpected status: {get_response.status_code}")

    print("\n🚀 Step 2: Testing POST /get-quote")

    # Form data
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
        print("   ✅ POST request successful")

        # Check response content
        data = post_response.get_data(as_text=True)

        # Check if it's JSON (old behavior) or HTML (new behavior)
        if post_response.content_type and 'application/json' in post_response.content_type:
            print("   ❌ Response is JSON (old behavior)")
            import json
            try:
                json_data = json.loads(data)
                print(
                    f"   📝 JSON content: {json.dumps(json_data, indent=2)[:200]}...")
            except:
                print(f"   📝 Raw content: {data[:200]}...")
            return False
        elif post_response.content_type and 'text/html' in post_response.content_type:
            print("   ✅ Response is HTML (new behavior)")

            # Check for results page elements
            has_recommendations = 'recommendation-card' in data
            has_best_match = 'best-match' in data
            has_confetti = 'confetti' in data
            has_success = 'Perfect Match Found' in data

            print(f"   🎯 Has recommendation cards: {has_recommendations}")
            print(f"   🏆 Has best match highlight: {has_best_match}")
            print(f"   🎉 Has success message: {has_success}")
            print(f"   🎊 Has confetti animation: {has_confetti}")

            if has_recommendations and has_success:
                print("   🎉 SUCCESS: Form returns proper HTML results page!")
                return True
            else:
                print("   ⚠️ HTML returned but missing expected elements")
                return False
        else:
            print(
                f"   ❓ Unexpected content type: {post_response.content_type}")
            print(f"   📝 Content preview: {data[:200]}...")
            return False

    elif post_response.status_code == 403:
        print("   ❌ 403 Forbidden")
        return False
    elif post_response.status_code == 302:
        print("   🔄 Redirect detected")
        location = post_response.headers.get('Location', 'Unknown')
        print(f"   📍 Redirect to: {location}")
        return False
    else:
        print(f"   ❌ Unexpected status: {post_response.status_code}")
        return False

except ImportError as e:
    print(f"❌ Import Error: {e}")
    return False
except Exception as e:
    print(f"❌ Error: {e}")
    return False

if __name__ == "__main__":
    success = True
    try:
        from backend.app.main import app

        print("🧪 Flask Internal Test Client")
        print("=" * 50)

        # Create test client
        client = app.test_client()

        print("🔍 Step 1: Testing GET /get-quote")
        get_response = client.get('/get-quote')
        print(f"   Status: {get_response.status_code}")
        print(f"   Content-Type: {get_response.content_type}")

        if get_response.status_code == 200:
            print("   ✅ GET request successful")

        elif get_response.status_code == 403:
            print("   ❌ 403 Forbidden - Check authentication requirements")
            success = False
        else:
            print(f"   ❌ Unexpected status: {get_response.status_code}")
            success = False

        if success:
            print("\n🚀 Step 2: Testing POST /get-quote")

            # Form data
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
                print("   ✅ POST request successful")

                # Check if it's HTML
                if post_response.content_type and 'text/html' in post_response.content_type:
                    print("   🎉 SUCCESS: Form returns HTML results page!")
                    data = post_response.get_data(as_text=True)
                    if 'Perfect Match Found' in data and 'recommendation-card' in data:
                        print("   ✅ All expected elements found in results page")
                    else:
                        print(
                            "   ⚠️ Some expected elements missing from results page")
                else:
                    print("   ❌ Response is not HTML")
                    success = False
            else:
                print(
                    f"   ❌ POST failed with status: {post_response.status_code}")
                success = False

        print("=" * 50)
        if success:
            print("🎉 ALL TESTS PASSED: Get-Quote form works correctly!")
        else:
            print("💥 TESTS FAILED: Issues detected with form")

    except Exception as e:
        print(f"❌ Test Error: {e}")
        print("💥 TESTS FAILED: Could not run tests")
