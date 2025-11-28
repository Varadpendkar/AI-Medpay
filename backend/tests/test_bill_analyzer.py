"""
Test Bill Analyzer with Sample Data
Tests the robust anomaly detection with synthetic bill data
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.utils.bill_analyzer import analyze_bill, flagged_summary

# Sample bill data matching the screenshot
sample_bill = {
    "merchant": "Apollo Care Hospitals",
    "hospital": "Apollo Care Hospitals",
    "date": "2021-10-25",
    "invoice_number": "INV-2021-1025",
    "line_items": [
        {"description": "consultation charges", "qty": 1, "unit_price": 5000, "amount": 5000},
        {"description": "implant (Prosthesis)", "qty": 1, "unit_price": 60000, "amount": 60000},
        {"description": "MRI Scan", "qty": 1, "unit_price": 8000, "amount": 8000},
        {"description": "surgical implants", "qty": 1, "unit_price": 45000, "amount": 45000},
        {"description": "ward charges (semi-private)", "qty": 3, "unit_price": 3000, "amount": 9000},
        {"description": "implant (Prosthesis) Duplicate (erroneous)", "qty": 1, "unit_price": 60000, "amount": 60000},
        {"description": "anesthesia", "qty": 1, "unit_price": 12000, "amount": 12000},
        {"description": "laboratory tests", "qty": 1, "unit_price": 4000, "amount": 4000},
        {"description": "misc charges (inflated)", "qty": 1, "unit_price": 50000, "amount": 50000},
        {"description": "physiotherapy (2 sessions)", "qty": 2, "unit_price": 2500, "amount": 5000}
    ],
    "subtotal": 298000,
    "gst": 14900,
    "total": 312900,
    "grand_total": 312900
}

print("=" * 80)
print("TESTING BILL ANALYZER")
print("=" * 80)

print("\n📋 Input Bill Data:")
print(f"  Hospital: {sample_bill['merchant']}")
print(f"  Date: {sample_bill['date']}")
print(f"  Invoice: {sample_bill['invoice_number']}")
print(f"  Line Items: {len(sample_bill['line_items'])}")
print(f"  Subtotal: ₹{sample_bill['subtotal']:,}")
print(f"  GST: ₹{sample_bill['gst']:,}")
print(f"  Grand Total: ₹{sample_bill['total']:,}")

print("\n🔍 Running Analysis...")
analysis = analyze_bill(sample_bill)

print("\n" + "=" * 80)
print("ANALYSIS RESULTS")
print("=" * 80)

print(f"\n📊 Summary:")
print(f"  Flagged Items: {len(analysis['flagged_items'])}")
print(f"  Potential Savings: ₹{analysis['potential_savings']:,}")

print(f"\n💰 Financial Details:")
print(f"  Computed Subtotal: ₹{analysis['computed_subtotal']:,}")
print(f"  Found Grand Total: ₹{analysis['grand_total']:,}")

print(f"\n🚨 Flagged Anomalies:")
for idx, flag in enumerate(analysis['flagged_items'], 1):
    print(f"\n  {idx}. {flag['type'].upper().replace('_', ' ')}")
    if flag['type'] == 'duplicate_item':
        print(f"     Indices: {flag['indices']}")
        print(f"     Similarity: {flag['score']:.1%}")
        print(f"     Item 1: {flag['items'][0]['description']} - ₹{flag['items'][0]['amount']:,}")
        print(f"     Item 2: {flag['items'][1]['description']} - ₹{flag['items'][1]['amount']:,}")
        print(f"     💵 Suggested Saving: ₹{flag['suggested_saving']:,}")
    elif flag['type'] == 'inflated_vs_expected':
        print(f"     Description: {flag['description']}")
        print(f"     Actual: ₹{flag['actual']:,}")
        print(f"     Expected: ₹{flag['expected']:,}")
        print(f"     Excess: ₹{flag['excess']:,}")
        print(f"     💵 Suggested Saving: ₹{flag['suggested_saving']:,}")
    else:
        print(f"     Details: {flag}")

print(f"\n📝 Detailed Summary:")
print(flagged_summary(analysis))

print("\n" + "=" * 80)
print("TEST VALIDATION")
print("=" * 80)

# Validate expected results
expected_duplicates = False
expected_inflated = False

for flag in analysis['flagged_items']:
    if flag['type'] == 'duplicate_item':
        expected_duplicates = True
        print("✅ Duplicate detection working - Found implant duplicate")
    elif flag['type'] == 'inflated_vs_expected':
        expected_inflated = True
        print(f"✅ Inflation detection working - Found {flag.get('description', 'item')}")

if analysis['potential_savings'] > 0:
    print(f"✅ Savings calculation working - ₹{analysis['potential_savings']:,} identified")
else:
    print("❌ WARNING: No savings identified (should have duplicates + inflation)")

if expected_duplicates and expected_inflated:
    print("\n🎉 SUCCESS: Bill analyzer correctly detects anomalies!")
else:
    print("\n⚠️  PARTIAL: Some detection may not be working")
    if not expected_duplicates:
        print("   - Duplicate detection issue")
    if not expected_inflated:
        print("   - Inflation detection issue")

print("\n" + "=" * 80)
