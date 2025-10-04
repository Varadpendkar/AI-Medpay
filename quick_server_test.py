#!/usr/bin/env python3
"""
Quick test to verify Flask server is working on port 5001.
"""
import requests
import json


def test_server():
    """Test the Flask server."""
    try:
        # Test GET first
        print("🧪 Testing GET /get-quote...")
        response = requests.get("http://127.0.0.1:5001/get-quote", timeout=5)
        print(f"GET Status: {response.status_code}")

        # Test POST
        print("\n🧪 Testing POST /get-quote...")
        data = {
            'age': '32',
            'dependents': '2',
            'location': 'Mumbai',
            'max_premium': '15000'
        }
        response = requests.post(
            "http://127.0.0.1:5001/get-quote", data=data, timeout=5)
        print(f"POST Status: {response.status_code}")
        print(f"Response length: {len(response.text)} chars")

        if response.status_code == 200:
            print("✅ Server is responding!")
            if "plan" in response.text.lower() or "insurance" in response.text.lower():
                print("✅ Response contains insurance-related content")
            else:
                print("⚠️ Response may not contain expected content")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text[:200]}...")

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server on port 5001")
    except requests.exceptions.Timeout:
        print("❌ Server request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")


if __name__ == "__main__":
    test_server()
