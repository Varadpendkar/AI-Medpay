#!/usr/bin/env python3
"""
Simple test to verify the get-quote route works with the trained model.
"""
from pathlib import Path
import json
import requests
import sys
import os
sys.path.append('/Users/varadpendkar/Documents/project/backend/app')


def test_quote_api():
    """Test the /get-quote API endpoint."""
    print("Testing /get-quote API endpoint...")

    # Sample form data
    test_data = {
        'age': '32',
        'dependents': '2',
        'location': 'Mumbai',
        'existing_conditions': '',
        'coverage_amount': '1000000',
        'max_premium': '15000',
        'preferred_hospitals': ''
    }

    try:
        # Try to make POST request to get-quote endpoint
        url = 'http://127.0.0.1:5000/get-quote'
        response = requests.post(url, data=test_data, timeout=10)

        if response.status_code == 200:
            print("✅ API endpoint working successfully")
            print(f"Response length: {len(response.text)} characters")

            # Check if response contains expected elements
            if 'plan' in response.text.lower() or 'recommendation' in response.text.lower():
                print("✅ Response contains plan recommendations")
                return True
            else:
                print("⚠️ Response doesn't contain expected content")
                return False
        else:
            print(f"❌ API returned status {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Flask server")
        print("Make sure the server is running on http://127.0.0.1:5000")
        return False
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False


def test_model_directly():
    """Test the model directly without Flask."""
    print("\nTesting model directly...")

    try:
        from utils.simple_ranker import PlanRanker

        project_root = Path(
            '/Users/varadpendkar/Documents/project/backend/app')
        ranker = PlanRanker(project_root)

        # Test user profile
        user = {
            'age': 32,
            'dependents': 2,
            'income': 1200000,
            'risk_score': 0.3
        }

        # Get recommendations
        recommendations = ranker.rank(user, k=5)

        print(f"✅ Got {len(recommendations)} recommendations")
        if recommendations:
            print(
                f"Top plan: {recommendations[0].get('plan_name', 'N/A')} (Score: {recommendations[0].get('score', 0):.3f})")
            return True
        else:
            print("❌ No recommendations returned")
            return False

    except Exception as e:
        print(f"❌ Direct model test failed: {e}")
        return False


if __name__ == "__main__":
    print("🔍 Testing LTR Model Integration\n")

    # Test model directly first
    model_works = test_model_directly()

    if model_works:
        print("\n" + "="*50)
        # Test Flask API
        api_works = test_quote_api()

        if api_works:
            print("\n🎉 Full integration test passed!")
            print("✅ Model training successful")
            print("✅ Flask integration working")
            print("✅ API endpoint responding")
        else:
            print("\n⚠️ Model works but Flask API has issues")
            print("Check Flask server logs for details")
    else:
        print("\n💥 Model integration failed")
        print("Need to debug the model loading")
