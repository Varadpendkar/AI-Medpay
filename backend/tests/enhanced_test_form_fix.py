#!/usr/bin/env python3
"""
Enhanced test script to verify the get-quote form returns HTML instead of JSON
This version handles sessions and CSRF tokens properly
"""
import requests
from bs4 import BeautifulSoup


def test_get_quote_form_with_session():
    """Test form submission with proper session handling"""

    # Create a session to maintain cookies
    session = requests.Session()

    try:
        print("🔍 Step 1: Getting the form page to establish session...")
        # First, get the form page to establish session and get any CSRF tokens
        form_response = session.get('http://127.0.0.1:5000/get-quote')

        if form_response.status_code != 200:
            print(
                f"❌ ERROR: Could not load form page. Status: {form_response.status_code}")
            return False

        print(
            f"✅ Form page loaded successfully (Status: {form_response.status_code})")

        # Parse the form to check for CSRF tokens
        soup = BeautifulSoup(form_response.text, 'html.parser')
        csrf_token = None

        # Look for CSRF token in various places
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        if csrf_input:
            csrf_token = csrf_input.get('value')
            print(f"🔐 Found CSRF token: {csrf_token[:20]}...")
        else:
            print("ℹ️ No CSRF token found in form")

        print("\n🚀 Step 2: Submitting the form...")

        # Form data to submit
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
            'health-condition': 'excellent',
            'conditions': []
        }

        # Add CSRF token if found
        if csrf_token:
            form_data['csrf_token'] = csrf_token

        # Submit the form using the same session
        response = session.post('http://127.0.0.1:5000/get-quote',
                                data=form_data,
                                headers={
                                    'Content-Type': 'application/x-www-form-urlencoded',
                                    'Referer': 'http://127.0.0.1:5000/get-quote'
                                })

        print(f"📊 Status Code: {response.status_code}")
        print(
            f"📋 Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
        print(f"🔗 Final URL: {response.url}")

        # Check response
        if response.status_code == 403:
            print("❌ 403 FORBIDDEN - This might be due to:")
            print("   - Missing CSRF token")
            print("   - Authentication required")
            print("   - Invalid form data")
            print("   - Missing required headers")
            print(f"\n📝 Response preview: {response.text[:200]}...")
            return False
        elif response.status_code == 302:
            print("🔄 REDIRECT detected - Following redirect...")
            final_response = session.get(
                response.headers.get('Location', response.url))
            return analyze_response(final_response)
        elif response.status_code == 200:
            return analyze_response(response)
        else:
            print(f"❓ UNEXPECTED STATUS: {response.status_code}")
            print(f"📝 Response preview: {response.text[:200]}...")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to Flask server. Make sure it's running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


def analyze_response(response):
    """Analyze the response to determine if it's the expected HTML results page"""

    content_type = response.headers.get('content-type', '').lower()

    if 'application/json' in content_type:
        print("❌ FAILED: Response is still JSON!")
        try:
            import json
            data = response.json()
            print(f"📝 JSON content: {json.dumps(data, indent=2)[:300]}...")
        except:
            print(f"📝 Raw content: {response.text[:200]}...")
        return False
    elif 'text/html' in content_type:
        print("✅ SUCCESS: Response is HTML!")

        # Parse HTML to check for results elements
        soup = BeautifulSoup(response.text, 'html.parser')

        # Check for results page elements
        recommendations = soup.find_all(class_='recommendation-card')
        best_match = soup.find(class_='best-match')
        success_header = soup.find('h1')
        confetti_script = any('confetti' in str(script)
                              for script in soup.find_all('script'))

        print(f"🎯 Found {len(recommendations)} recommendation cards")
        print(f"🏆 Best match highlight: {'Yes' if best_match else 'No'}")
        print(
            f"🎉 Success header: {'Yes' if success_header and 'Perfect Match' in success_header.get_text() else 'No'}")
        print(f"🎊 Confetti animation: {'Yes' if confetti_script else 'No'}")

        if len(recommendations) >= 2 and success_header:
            print("✅ Results page rendered successfully with all expected elements!")
            return True
        else:
            print("⚠️ HTML returned but missing expected result elements")
            print(
                f"📝 Page title: {soup.title.get_text() if soup.title else 'No title'}")
            return False
    else:
        print(f"❓ UNKNOWN: Unexpected content type: {content_type}")
        print(f"📝 Content preview: {response.text[:200]}...")
        return False


def test_simple_get():
    """Test that the GET request works properly"""
    try:
        response = requests.get('http://127.0.0.1:5000/get-quote')
        print(f"🌐 GET /get-quote Status: {response.status_code}")

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            form = soup.find('form')
            if form:
                print("✅ Form found on page")
                return True
            else:
                print("❌ No form found on page")
                return False
        return False
    except Exception as e:
        print(f"❌ GET test failed: {e}")
        return False


if __name__ == "__main__":
    print("🧪 Enhanced Get-Quote Form Test")
    print("=" * 60)

    # Test basic connectivity first
    print("🔍 Testing basic form access...")
    get_success = test_simple_get()

    if not get_success:
        print("\n💥 Basic form access failed. Check if Flask server is running.")
        exit(1)

    print("\n🔍 Testing form submission...")
    success = test_get_quote_form_with_session()

    print("=" * 60)
    if success:
        print("🎉 TEST PASSED: Form successfully returns styled HTML results!")
    else:
        print("💥 TEST FAILED: Form submission issue detected")
        print("\n🛠️ Debug suggestions:")
        print("1. Check Flask server logs for errors")
        print("2. Verify route is properly registered")
        print("3. Check for authentication/CSRF requirements")
        print("4. Test form manually in browser")
