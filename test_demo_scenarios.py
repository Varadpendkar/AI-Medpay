#!/usr/bin/env python3
"""
Test script to verify the demo lecturer scenarios work correctly.
"""
import sys
import requests
import json


def test_demo_scenario(age, dependents, income):
    """Test a demo lecturer scenario."""
    url = "http://127.0.0.1:5001/get-quote"

    data = {
        "age": age,
        "dependents": dependents,
        "annual_income": income,
        "demo_lecturer": "1"
    }

    print(
        f"\n🎓 Testing lecturer: age={age}, dependents={dependents}, income={income}")

    try:
        response = requests.post(url, data=data)
        if response.status_code == 200:
            # Check if demo recommendations are returned
            if "Educator Plus Family" in response.text:
                print("✅ Found 'Educator Plus Family' - demo scenario working!")
            elif "Academic Family Premier" in response.text:
                print("✅ Found 'Academic Family Premier' - demo scenario working!")
            elif "CampusCare Essential" in response.text:
                print("✅ Found 'CampusCare Essential' - demo scenario working!")
            elif "Young Pro Protect" in response.text:
                print("✅ Found 'Young Pro Protect' - demo scenario working!")
            elif "Executive Health Premier" in response.text:
                print("✅ Found 'Executive Health Premier' - demo scenario working!")
            else:
                print("⚠️  Demo scenario may not be triggered - using regular ranker")

            return True
        else:
            print(f"❌ HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    print("Testing demo lecturer scenarios...")

    # Test cases from the scenarios
    test_cases = [
        (28, 0, 600000),   # Scenario 1
        (30, 1, 720000),   # Scenario 2
        (32, 2, 850000),   # Scenario 3
        (35, 0, 1200000),  # Scenario 5
    ]

    for age, dependents, income in test_cases:
        test_demo_scenario(age, dependents, income)

    print("\n✅ All tests completed!")


if __name__ == "__main__":
    main()
