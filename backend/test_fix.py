#!/usr/bin/env python3
"""
Quick test to verify the bug is fixed
"""
from app.utils.new_ranker import NewPlanRanker
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))


print("Testing the fix...")

# Initialize ranker
project_root = Path(__file__).parent / 'app'
ranker = NewPlanRanker(project_root)

# Test with minimal user data (simulating frontend form data)
test_user = {
    "user_id": "anonymous",
    "age": 30,
    "gender": "male",
    "region": "Maharashtra",
    "income_band": "6-10L"
}

print(f"Testing with user: {test_user}")

try:
    recommendations = ranker.rank(test_user, k=5)
    print(f"✅ SUCCESS! Generated {len(recommendations)} recommendations")

    for rec in recommendations[:3]:
        print(f"\n  {rec['rank']}. {rec['plan_name'][:50]}")
        print(f"     Premium: ₹{rec['premium']:,.0f}/year")
        print(f"     Score: {rec['score']:.4f}")

    print("\n🎉 The bug is FIXED! Frontend form should work now.")

except Exception as e:
    print(f"❌ FAILED: {str(e)}")
    import traceback
    traceback.print_exc()
