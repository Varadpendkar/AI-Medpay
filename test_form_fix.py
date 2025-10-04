#!/usr/bin/env python3
"""
Test script to verify the get-quote form returns HTML instead of JSON
"""
import requests
import json
from bs4 import BeautifulSoup

# Test the get-quote form submission


def test_get_quote_form():
    """Test that form submission returns HTML results page instead of raw JSON"""

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

    try:
        # Submit the form
        response = requests.post(
            'http://127.0.0.1:5000/get-quote', data=form_data)

        print(f"Status Code: {response.status_code}")
        print(
            f"Content-Type: {response.headers.get('Content-Type', 'Unknown')}")

        # Check if response is HTML (not JSON)
        content_type = response.headers.get('content-type', '').lower()

        if 'application/json' in content_type:
            print("❌ FAILED: Response is still JSON!")
            print("Response content:", response.text[:200] + "...")
            return False
        elif 'text/html' in content_type:
            print("✅ SUCCESS: Response is HTML!")

            # Parse HTML to check for results elements
            soup = BeautifulSoup(response.text, 'html.parser')

            # Check for results page elements
            recommendations = soup.find_all(class_='recommendation-card')
            best_match = soup.find(class_='best-match')
            confetti = soup.find_all('script')

            print(f"Found {len(recommendations)} recommendation cards")
            print(f"Best match highlight: {'Yes' if best_match else 'No'}")
            print(
                f"Confetti animation: {'Yes' if any('confetti' in str(script) for script in confetti) else 'No'}")

            if len(recommendations) >= 2:
                print("✅ Results page rendered successfully with recommendations!")
                return True
            else:
                print("⚠️ HTML returned but missing recommendation elements")
                return False
        else:
            print(f"❓ UNKNOWN: Unexpected content type: {content_type}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ ERROR: Could not connect to Flask server. Make sure it's running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False


if __name__ == "__main__":
    print("🧪 Testing Get-Quote Form Response Format...")
    print("=" * 50)

    success = test_get_quote_form()

    print("=" * 50)
    if success:
        print("🎉 TEST PASSED: Form now returns styled HTML results instead of raw JSON!")
    else:
        print("💥 TEST FAILED: Issue still exists")
