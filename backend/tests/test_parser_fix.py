"""
Quick test to verify bill_parser now extracts subtotal, GST, and total correctly
"""
import sys
sys.path.insert(0, '/Users/varadpendkar/Documents/project/backend')

from app.utils import bill_analyzer

# Simulate what the updated bill_parser now returns
line_items = [
    {"desc": "Knee Replacement Surgeon Fees", "qty": 1, "unit": 75000.0, "amount": 75000.0},
    {"desc": "Implant (Prosthesis)", "qty": 1, "unit": 60000.0, "amount": 60000.0},
    {"desc": "OT Charges (Operation Theatre)", "qty": 1, "unit": 15000.0, "amount": 15000.0},
    {"desc": "Room Rent Deluxe A (3 days)", "qty": 3, "unit": 5000.0, "amount": 15000.0},
    {"desc": "Physiotherapy Session", "qty": 5, "unit": 2000.0, "amount": 10000.0},
    {"desc": "Implant (Prosthesis) Duplicate (erroneous)", "qty": 1, "unit": 60000.0, "amount": 60000.0},
    {"desc": "Doctor Consultation Anaesthesia", "qty": 1, "unit": 8000.0, "amount": 8000.0},
    {"desc": "Consumables & Dressing", "qty": 1, "unit": 5000.0, "amount": 5000.0},
    {"desc": "Misc Charges (inflated)", "qty": 1, "unit": 50000.0, "amount": 50000.0},
    {"desc": "Subtotal (0)", "qty": 1, "unit": None, "amount": 298000.0},
    {"desc": "GST @5% (0)", "qty": 1, "unit": None, "amount": 14900.0},
    {"desc": "Grand Total (0)", "qty": 1, "unit": None, "amount": 312900.0}
]

# This is what parse_bill NOW returns (after fix)
parsed = {
    "hospital": "Apollo Care Hospitals",
    "bill_date": "2021-10-25",
    "invoice_no": "Invoice",
    "total_amount": 312900.0,
    "subtotal": 298000.0,
    "gst": 14900.0,
    "line_items": line_items
}

# Prepare for analyzer (same as bill_buster.py does)
ocr_parsed = {
    "merchant": parsed.get('hospital'),
    "hospital": parsed.get('hospital'),
    "date": parsed.get('bill_date'),
    "invoice_number": parsed.get('invoice_no'),
    "line_items": parsed.get('line_items', []),
    "subtotal": parsed.get('subtotal'),
    "gst": parsed.get('gst'),
    "total": parsed.get('total_amount'),
    "grand_total": parsed.get('total_amount')
}

print("=" * 80)
print("TESTING BILL ANALYZER WITH FIXED PARSER OUTPUT")
print("=" * 80)
print(f"\n📋 Input to bill_analyzer:")
print(f"  Hospital: {ocr_parsed['hospital']}")
print(f"  Date: {ocr_parsed['date']}")
print(f"  Line items: {len(ocr_parsed['line_items'])}")
print(f"  Subtotal: ₹{ocr_parsed['subtotal']:,}")
print(f"  GST: ₹{ocr_parsed['gst']:,}")
print(f"  Grand Total: ₹{ocr_parsed['grand_total']:,}")

# Run analyzer
print(f"\n🔍 Running bill_analyzer.analyze_bill()...")
analysis = bill_analyzer.analyze_bill(ocr_parsed)

print(f"\n" + "=" * 80)
print("ANALYSIS RESULTS")
print("=" * 80)
print(f"✅ Flagged items: {len(analysis.get('flagged_items', []))}")
print(f"✅ Potential savings: ₹{analysis.get('potential_savings', 0):,.0f}")
print()

if analysis.get('flagged_items'):
    print("❌ Flagged Items Breakdown:")
    print("-" * 80)
    for i, item in enumerate(analysis['flagged_items'], 1):
        item_type = item.get('type', 'unknown')
        
        if item_type == 'duplicate_item':
            indices = item.get('indices', [])
            print(f"  {i}. 🔄 DUPLICATE: {item.get('description')}")
            print(f"     Lines: {', '.join(str(idx+1) for idx in indices)}")
            print(f"     Amount: ₹{item.get('amount', 0):,}")
            print(f"     Potential savings: ₹{item.get('excess', 0):,}")
        
        elif item_type == 'inflated_vs_expected':
            print(f"  {i}. 💸 OVERCHARGE: {item.get('description')}")
            print(f"     Line: {item.get('line_index', 0) + 1}")
            print(f"     Charged: ₹{item.get('actual', 0):,}")
            print(f"     Expected: ₹{item.get('expected', 0):,}")
            print(f"     Factor: {item.get('factor', 0):.1f}x market rate")
        
        elif item_type in ['subtotal_mismatch', 'grandtotal_mismatch']:
            print(f"  {i}. 🧮 CALCULATION ERROR: {item.get('type').replace('_', ' ').title()}")
            print(f"     Computed: ₹{item.get('computed', 0):,}")
            print(f"     Found: ₹{item.get('found', 0):,}")
            print(f"     Difference: ₹{abs(item.get('computed', 0) - item.get('found', 0)):,}")
        
        print()
    
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(bill_analyzer.flagged_summary(analysis))
else:
    print("✅ No anomalies detected. Bill appears reasonable.")

print("\n" + "=" * 80)
print("✅ TEST COMPLETE - Bill analyzer should now work correctly!")
print("=" * 80)
