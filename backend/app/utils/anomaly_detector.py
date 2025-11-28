"""
Anomaly Detector - Flag suspicious charges in medical bills
Detects duplicates, overcharges, and other billing anomalies
"""
import logging
import pandas as pd
from typing import Dict, List
from difflib import SequenceMatcher

LOG = logging.getLogger(__name__)


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings (0-1)"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def detect_duplicates(line_items: List[Dict]) -> List[Dict]:
    """
    Detect duplicate or near-duplicate line items
    
    Args:
        line_items: List of parsed line items
    
    Returns:
        List of flagged items with duplicate anomalies
    """
    flags = []
    
    for i in range(len(line_items)):
        for j in range(i + 1, len(line_items)):
            item_i = line_items[i]
            item_j = line_items[j]
            
            # Check description similarity
            sim = similarity(item_i['desc'], item_j['desc'])
            
            # Check if amounts are similar (±5%)
            amount_i = item_i['amount']
            amount_j = item_j['amount']
            amount_diff_pct = abs(amount_i - amount_j) / max(amount_i, amount_j) * 100
            
            if sim > 0.85 and amount_diff_pct < 5:
                # Likely duplicate
                recovery = min(amount_i, amount_j)
                flags.append({
                    "line_id": j,
                    "reason": f"Possible duplicate of line {i+1}: '{item_i['desc'][:40]}'",
                    "severity": "high" if sim > 0.95 else "medium",
                    "recovery": recovery,
                    "type": "duplicate"
                })
                LOG.warning(f"Duplicate detected: Line {i+1} and {j+1} ({sim*100:.0f}% similar)")
    
    return flags


def detect_overcharges(line_items: List[Dict], procedures_df: pd.DataFrame = None) -> List[Dict]:
    """
    Detect overcharged items by comparing with typical procedure costs
    
    Args:
        line_items: List of parsed line items
        procedures_df: DataFrame with procedure names and average costs
    
    Returns:
        List of flagged items with overcharge anomalies
    """
    flags = []
    
    if procedures_df is None or procedures_df.empty:
        LOG.warning("No procedures reference data provided, skipping overcharge detection")
        return flags
    
    # Build lookup dictionary for faster matching
    procedures_dict = {}
    for _, row in procedures_df.iterrows():
        proc_name = str(row.get('procedure_name', '') or row.get('name', '')).lower()
        avg_cost = float(row.get('avg_cost', 0) or row.get('cost', 0))
        if proc_name and avg_cost > 0:
            procedures_dict[proc_name] = avg_cost
    
    for idx, item in enumerate(line_items):
        desc = item['desc'].lower()
        actual_amount = item['amount']
        
        # Try to match with known procedures
        best_match = None
        best_sim = 0
        expected_cost = None
        
        for proc_name, avg_cost in procedures_dict.items():
            sim = similarity(desc, proc_name)
            if sim > best_sim:
                best_sim = sim
                best_match = proc_name
                expected_cost = avg_cost
        
        # If good match found and actual is significantly higher
        if best_match and best_sim > 0.6 and expected_cost:
            overcharge_ratio = actual_amount / expected_cost
            
            if overcharge_ratio > 1.5:  # More than 50% above average
                recovery = actual_amount - expected_cost
                flags.append({
                    "line_id": idx,
                    "reason": f"Overcharged by {(overcharge_ratio-1)*100:.0f}% vs typical cost of ₹{expected_cost:.0f} for '{best_match}'",
                    "severity": "high" if overcharge_ratio > 2.0 else "medium",
                    "recovery": recovery,
                    "type": "overcharge"
                })
                LOG.warning(f"Overcharge detected: '{desc}' charged ₹{actual_amount} vs expected ₹{expected_cost}")
    
    return flags


def detect_total_mismatch(line_items: List[Dict], declared_total: float) -> List[Dict]:
    """
    Check if sum of line items matches declared total
    
    Args:
        line_items: List of parsed line items
        declared_total: Total amount stated on bill
    
    Returns:
        List with flag if mismatch detected
    """
    flags = []
    
    if not line_items or declared_total == 0:
        return flags
    
    calculated_total = sum(item['amount'] for item in line_items)
    diff = abs(calculated_total - declared_total)
    diff_pct = (diff / declared_total) * 100
    
    if diff_pct > 2:  # More than 2% difference
        flags.append({
            "line_id": -1,  # Applies to overall bill
            "reason": f"Total mismatch: Line items sum to ₹{calculated_total:.2f} but bill shows ₹{declared_total:.2f} ({diff_pct:.1f}% difference)",
            "severity": "high" if diff_pct > 10 else "medium",
            "recovery": diff if calculated_total > declared_total else 0,
            "type": "total_mismatch"
        })
        LOG.warning(f"Total mismatch: Calculated ₹{calculated_total} vs Declared ₹{declared_total}")
    
    return flags


def detect_high_room_rent(line_items: List[Dict]) -> List[Dict]:
    """
    Flag unusually high room rent charges
    
    Args:
        line_items: List of parsed line items
    
    Returns:
        List of flagged high room rent items
    """
    flags = []
    
    room_keywords = ['room', 'bed', 'ward', 'accommodation']
    threshold_per_day = 5000  # ₹5000 per day
    
    for idx, item in enumerate(line_items):
        desc_lower = item['desc'].lower()
        
        if any(kw in desc_lower for kw in room_keywords):
            qty = item['qty'] or 1
            total = item['amount']
            per_day = total / qty if qty > 0 else total
            
            if per_day > threshold_per_day:
                excess = (per_day - threshold_per_day) * qty
                flags.append({
                    "line_id": idx,
                    "reason": f"High room rent: ₹{per_day:.0f}/day exceeds typical rate of ₹{threshold_per_day}/day",
                    "severity": "medium",
                    "recovery": excess,
                    "type": "high_room_rent"
                })
                LOG.warning(f"High room rent: ₹{per_day:.0f}/day for '{item['desc']}'")
    
    return flags


def detect_anomalies(parsed_bill: Dict, procedures_df: pd.DataFrame = None) -> Dict:
    """
    Main anomaly detection function - run all checks
    
    Args:
        parsed_bill: Output from bill_parser.parse_bill()
        procedures_df: Optional DataFrame with reference procedure costs
    
    Returns:
        Dictionary with:
            - flagged_lines: List of anomalies detected
            - total_savings: Total recoverable amount
            - percent_flagged: Percentage of line items flagged
    """
    try:
        line_items = parsed_bill.get('line_items', [])
        declared_total = parsed_bill.get('total_amount', 0)
        
        if not line_items:
            LOG.warning("No line items to analyze")
            return {
                "flagged_lines": [],
                "total_savings": 0.0,
                "percent_flagged": 0.0
            }
        
        # Run all detection checks
        all_flags = []
        
        # 1. Duplicate detection
        all_flags.extend(detect_duplicates(line_items))
        
        # 2. Overcharge detection
        if procedures_df is not None:
            all_flags.extend(detect_overcharges(line_items, procedures_df))
        
        # 3. Total mismatch
        all_flags.extend(detect_total_mismatch(line_items, declared_total))
        
        # 4. High room rent
        all_flags.extend(detect_high_room_rent(line_items))
        
        # Calculate totals
        total_savings = sum(flag.get('recovery', 0) for flag in all_flags)
        unique_flagged_lines = len(set(flag['line_id'] for flag in all_flags if flag['line_id'] >= 0))
        percent_flagged = (unique_flagged_lines / len(line_items)) * 100 if line_items else 0
        
        LOG.info(f"Anomaly detection complete: {len(all_flags)} issues found, ₹{total_savings:.2f} potential savings")
        
        return {
            "flagged_lines": all_flags,
            "total_savings": round(total_savings, 2),
            "percent_flagged": round(percent_flagged, 1)
        }
        
    except Exception as e:
        LOG.exception(f"Error in detect_anomalies: {e}")
        return {
            "flagged_lines": [],
            "total_savings": 0.0,
            "percent_flagged": 0.0
        }


if __name__ == "__main__":
    # Test script
    logging.basicConfig(level=logging.INFO)
    
    # Mock parsed bill
    mock_bill = {
        "hospital": "Test Hospital",
        "bill_date": "2024-03-15",
        "invoice_no": "INV-001",
        "total_amount": 12000.0,
        "line_items": [
            {"desc": "Consultation Fee", "qty": 1, "unit": 500, "amount": 500, "code": None},
            {"desc": "Blood Test CBC", "qty": 1, "unit": 800, "amount": 800, "code": None},
            {"desc": "Blood Test - CBC", "qty": 1, "unit": 850, "amount": 850, "code": None},  # Duplicate
            {"desc": "Room Rent", "qty": 2, "unit": 4000, "amount": 8000, "code": None},  # High rent
            {"desc": "Medicines", "qty": 1, "unit": 1500, "amount": 1500, "code": None},
        ]
    }
    
    # Mock procedures dataframe
    mock_procedures = pd.DataFrame({
        'procedure_name': ['consultation', 'blood test', 'x-ray'],
        'avg_cost': [400, 600, 1000]
    })
    
    result = detect_anomalies(mock_bill, mock_procedures)
    
    print(f"\nAnomaly Detection Results:")
    print(f"Total Savings: ₹{result['total_savings']}")
    print(f"Percent Flagged: {result['percent_flagged']}%")
    print(f"\nFlagged Items:")
    for flag in result['flagged_lines']:
        print(f"  Line {flag['line_id']}: {flag['reason']} (₹{flag['recovery']:.2f})")
