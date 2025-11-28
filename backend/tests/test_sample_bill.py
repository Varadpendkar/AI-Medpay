"""
Create a sample bill JSON to test the frontend display
This simulates what the backend would return after processing
"""
import json
import os

# Create a sample result that matches what bill_analyzer would produce
sample_result = {
    "status": "completed",
    "job_id": "test-12345",
    "hospital_name": "Apollo Care Hospitals",
    "hospital": "Apollo Care Hospitals",
    "bill_date": "2021-10-25",
    "date": "2021-10-25",
    "invoice_no": "Invoice",
    "invoice_number": "Invoice",
    "total_amount": 312900,
    "grand_total": 312900,
    "subtotal": 298000,
    "gst": 14900,
    "tax": 14900,
    "ocr_confidence": 90.6,
    "line_items": [
        {"desc": "Knee Replacement Surgeon Fees", "qty": 1, "unit": 75000, "amount": 75000},
        {"desc": "Implant (Prosthesis)", "qty": 1, "unit": 60000, "amount": 60000},
        {"desc": "OT Charges (Operation Theatre)", "qty": 1, "unit": 15000, "amount": 15000},
        {"desc": "Room Rent Deluxe A (3 days)", "qty": 3, "unit": 5000, "amount": 15000},
        {"desc": "Physiotherapy Session", "qty": 5, "unit": 2000, "amount": 10000},
        {"desc": "Implant (Prosthesis) Duplicate (erroneous)", "qty": 1, "unit": 60000, "amount": 60000},
        {"desc": "Doctor Consultation Anaesthesia", "qty": 1, "unit": 8000, "amount": 8000},
        {"desc": "Consumables & Dressing", "qty": 1, "unit": 5000, "amount": 5000},
        {"desc": "Misc Charges (inflated)", "qty": 1, "unit": 50000, "amount": 50000},
        {"desc": "Subtotal (0)", "qty": 1, "unit": None, "amount": 298000},
        {"desc": "GST @5% (0)", "qty": 1, "unit": None, "amount": 14900},
        {"desc": "Grand Total (0)", "qty": 1, "unit": None, "amount": 312900}
    ],
    "flagged_items": [
        {
            "type": "duplicate_item",
            "description": "Implant (Prosthesis)",
            "indices": [1, 5],
            "amount": 60000,
            "excess": 60000,
            "reason": "Duplicate charge - same item billed twice"
        },
        {
            "type": "inflated_vs_expected",
            "description": "Implant (Prosthesis)",
            "line_index": 1,
            "actual": 60000,
            "expected": 10500,
            "factor": 5.71,
            "excess": 49500,
            "reason": "Charged ₹60,000 but expected ₹10,500 (571% of expected)"
        },
        {
            "type": "inflated_vs_expected",
            "description": "surgical implants",
            "line_index": 1,
            "actual": 60000,
            "expected": 10500,
            "factor": 5.71,
            "excess": 49500,
            "reason": "Charged ₹60,000 but expected ₹10,500 (571% of expected)"
        },
        {
            "type": "inflated_vs_expected",
            "description": "Implant (Prosthesis) Duplicate (erroneous)",
            "line_index": 5,
            "actual": 60000,
            "expected": 10500,
            "factor": 5.71,
            "excess": 49500,
            "reason": "Charged ₹60,000 but expected ₹10,500 (571% of expected)"
        },
        {
            "type": "inflated_vs_expected",
            "description": "Misc Charges (inflated)",
            "line_index": 8,
            "actual": 50000,
            "expected": 10500,
            "factor": 4.76,
            "excess": 39500,
            "reason": "Charged ₹50,000 but expected ₹10,500 (476% of expected)"
        },
        {
            "type": "inflated_vs_expected",
            "description": "Physiotherapy Session",
            "line_index": 4,
            "actual": 10000,
            "expected": 1680,
            "factor": 5.95,
            "excess": 8320,
            "reason": "Charged ₹10,000 but expected ₹1,680 (595% of expected)"
        },
        {
            "type": "subtotal_mismatch",
            "computed": 258000,
            "found": 298000,
            "diff": 40000,
            "reason": "Subtotal mismatch: computed ₹258,000 but found ₹298,000"
        },
        {
            "type": "grandtotal_mismatch",
            "computed": 272900,
            "found": 312900,
            "diff": 40000,
            "reason": "Grand total mismatch: computed ₹272,900 but found ₹312,900"
        }
    ],
    "potential_savings": 189760,
    "total_savings": 189760,
    "percent_flagged": 66.7,
    "totals_check": {
        "subtotal_computed": 258000,
        "subtotal_found": 298000,
        "gst_computed": 12900,
        "gst_found": 14900,
        "grand_total_computed": 272900,
        "grand_total_found": 312900,
        "subtotal_ok": False,
        "gst_ok": False,
        "grand_total_ok": False
    },
    "analysis": {
        "flagged_items": [
            {
                "type": "duplicate_item",
                "description": "Implant (Prosthesis)",
                "indices": [1, 5],
                "amount": 60000,
                "excess": 60000,
                "reason": "Duplicate charge - same item billed twice"
            }
        ],
        "potential_savings": 189760,
        "totals_check": {
            "subtotal_ok": False,
            "gst_ok": False,
            "grand_total_ok": False
        }
    }
}

# Save to scan results folder
results_folder = "/Users/varadpendkar/Documents/project/backend/uploads/scan_results"
os.makedirs(results_folder, exist_ok=True)

result_path = os.path.join(results_folder, "test-12345.json")
with open(result_path, 'w') as f:
    json.dump(sample_result, f, indent=2)

print(f"✅ Sample result saved to: {result_path}")
print(f"\n📊 Summary:")
print(f"  - Hospital: {sample_result['hospital_name']}")
print(f"  - Total Amount: ₹{sample_result['total_amount']:,}")
print(f"  - Flagged Items: {len(sample_result['flagged_items'])}")
print(f"  - Potential Savings: ₹{sample_result['potential_savings']:,}")
print(f"\n🔗 Test URL: http://127.0.0.1:5001/bill-buster/scan-result/test-12345")
print(f"\n💡 To test in browser:")
print(f"   1. Open browser console")
print(f"   2. Run: fetch('/bill-buster/scan-result/test-12345').then(r=>r.json()).then(console.log)")
