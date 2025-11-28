# app/utils/bill_analyzer.py
"""
Bill Analyzer - Detects anomalies in medical bills
- Duplicate charges
- Inflated prices vs reference data
- Subtotal/GST/Grand Total mismatches
"""
import re
import math
import json
from typing import List, Dict, Tuple, Any
from difflib import SequenceMatcher
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

# Try to load procedure price reference (optional)
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
REF_PROC_PATH = os.path.join(PROJECT_ROOT, 'data', 'procedures_full_50.csv')

_proc_price_map = None
try:
    if os.path.exists(REF_PROC_PATH):
        _proc_df = pd.read_csv(REF_PROC_PATH)
        # expect columns: procedure_code, procedure_name, avg_cost
        # create a lowercase name -> avg_cost mapping
        _proc_price_map = {
            str(r['procedure_name']).strip().lower(): float(r['avg_cost'])
            for _, r in _proc_df.iterrows()
            if pd.notnull(r.get('procedure_name')) and pd.notnull(r.get('avg_cost'))
        }
        logger.info("Loaded procedure reference map with %d entries", len(_proc_price_map))
except Exception as e:
    logger.warning("Could not load procedure reference file: %s", e)
    _proc_price_map = None

_currency_re = re.compile(r'[₹Rs.,\s]')

def parse_amount(x: Any) -> float:
    """Robustly parse numeric currency-like strings."""
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x)
    s = _currency_re.sub('', s)
    s = s.replace('(', '').replace(')', '')
    try:
        return float(s)
    except Exception:
        # fallback: find first number
        m = re.search(r'(\d[\d,\.]*)', s)
        if m:
            try:
                return float(m.group(1).replace(',', ''))
            except:
                pass
    return 0.0

def similarity(a: str, b: str) -> float:
    """Calculate string similarity ratio (0-1)."""
    return SequenceMatcher(None, (a or '').lower(), (b or '').lower()).ratio()

def detect_duplicates(line_items: List[Dict[str, Any]], sim_threshold: float = 0.60) -> List[Tuple[int,int,float]]:
    """
    Return list of tuple pairs (i, j, score) where i<j are duplicate/similar items.
    Uses lower threshold (0.60) to catch items with slight variations in description.
    Also checks that prices are within 5% to reduce false positives.
    """
    duplicates = []
    n = len(line_items)
    for i in range(n):
        desc_i = line_items[i].get('desc') or line_items[i].get('description') or ''
        for j in range(i+1, n):
            desc_j = line_items[j].get('desc') or line_items[j].get('description') or ''
            if not desc_i or not desc_j:
                continue
            score = similarity(desc_i, desc_j)
            # also check identical unit price to reduce false positives
            price_i = parse_amount(line_items[i].get('amount') or line_items[i].get('unit_price') or 0)
            price_j = parse_amount(line_items[j].get('amount') or line_items[j].get('unit_price') or 0)
            if score >= sim_threshold and abs(price_i - price_j) / (max(price_i, 1)) < 0.05:
                duplicates.append((i, j, score))
    return duplicates

def detect_inflation(line_items: List[Dict[str, Any]], inflation_factor: float = 1.5) -> List[Dict[str,Any]]:
    """
    Flags items that look inflated:
      - If we have a reference price for the description, compare to avg_cost.
      - Else: compare the line's amount to median of other items of same 'type' (simple fallback).
    Returns list of flagged item dicts with 'index', 'reason', 'expected', 'actual', 'excess'.
    """
    flags = []
    # build baseline medians by unit: fallback
    amounts = [parse_amount(li.get('amount') or li.get('unit_price') or 0) for li in line_items]
    median_all = float(pd.Series([a for a in amounts if a>0]).median()) if any(a>0 for a in amounts) else 0.0

    for idx, li in enumerate(line_items):
        desc = (li.get('desc') or li.get('description') or '').strip().lower()
        if not desc:
            continue
        actual = parse_amount(li.get('amount') or li.get('unit_price') or 0)
        if actual <= 0:
            continue
        expected = None
        # try exact match on procedure map (best)
        if _proc_price_map:
            # try direct key
            if desc in _proc_price_map:
                expected = _proc_price_map[desc]
            else:
                # try fuzzy match against keys quickly
                best = None
                best_score = 0.0
                for k in _proc_price_map.keys():
                    s = similarity(k, desc)
                    if s > best_score:
                        best_score = s
                        best = k
                if best_score >= 0.7:
                    expected = _proc_price_map.get(best)
        # fallback expected = median_all
        if expected is None and median_all > 0:
            expected = median_all

        if expected is None:
            continue

        if actual > expected * inflation_factor:
            flags.append({
                "index": idx,
                "description": li.get('description'),
                "actual": actual,
                "expected": expected,
                "excess": round(actual - expected, 2),
                "reason": "inflated_vs_expected"
            })
    return flags

def check_totals(line_items: List[Dict[str, Any]], found_subtotal: float=None, found_gst: float=None, found_grand_total: float=None) -> Dict[str,Any]:
    """
    Recompute subtotal from line items and compare with found subtotals/GST/grand total.
    Returns mismatch flags and computed numbers.
    """
    computed_subtotal = sum(parse_amount(li.get('amount') or 0) for li in line_items)
    # if GST not present in lines, use provided found_gst else 0
    gst = parse_amount(found_gst) if found_gst is not None else 0.0
    grand = parse_amount(found_grand_total) if found_grand_total is not None else 0.0

    flags = []
    # check subtotal tolerance
    if found_subtotal is not None:
        diff = abs(computed_subtotal - parse_amount(found_subtotal))
        if diff > max(1.0, 0.005 * computed_subtotal):  # >0.5% or > ₹1
            flags.append({
                "type": "subtotal_mismatch",
                "computed_subtotal": computed_subtotal,
                "found_subtotal": parse_amount(found_subtotal),
                "diff": diff
            })

    # check grand total tolerance
    if grand and gst is not None:
        expected_grand = computed_subtotal + gst
        diff2 = abs(expected_grand - grand)
        if diff2 > max(1.0, 0.005 * expected_grand):
            flags.append({
                "type": "grandtotal_mismatch",
                "expected_grand": expected_grand,
                "found_grand": grand,
                "diff": diff2
            })

    return {
        "computed_subtotal": computed_subtotal,
        "found_subtotal": parse_amount(found_subtotal) if found_subtotal is not None else None,
        "found_gst": gst,
        "found_grand": grand,
        "flags": flags
    }

def analyze_bill(ocr_parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    ocr_parsed expected keys:
      - 'merchant' / 'hospital' (opt)
      - 'date'
      - 'total' (grand total from OCR)
      - 'subtotal'
      - 'gst'
      - 'line_items': list of dicts with keys: description, qty, unit_price, amount
    Returns dict with flagged_items list, potential_savings, details
    """
    all_lines = ocr_parsed.get('line_items', []) or []
    subtotal = ocr_parsed.get('subtotal')
    gst = ocr_parsed.get('gst') or ocr_parsed.get('tax')
    grand = ocr_parsed.get('total') or ocr_parsed.get('grand_total')

    # Filter out summary rows (subtotal, gst, total) - keep only actual line items
    summary_keywords = ['subtotal', 'sub-total', 'sub total', 'gst', 'tax', 'vat', 
                        'grand total', 'grandtotal', 'total', 'discount']
    lines = []
    for li in all_lines:
        desc = (li.get('desc') or li.get('description') or '').lower().strip()
        # Skip if description contains summary keywords
        is_summary = any(keyword in desc for keyword in summary_keywords)
        if not is_summary:
            lines.append(li)
    
    # ensure amounts parsed
    for li in lines:
        li['amount_num'] = parse_amount(li.get('amount') or li.get('unit_price') or 0)

    flagged = []
    # duplicates
    dup_pairs = detect_duplicates(lines)
    for i, j, score in dup_pairs:
        desc_i = lines[i].get('desc') or lines[i].get('description') or ''
        amount = lines[i].get('amount_num') or 0
        flagged.append({
            "type": "duplicate_item",
            "description": desc_i,
            "indices": [i, j],
            "amount": amount,
            "excess": amount,  # Assuming one is unnecessary
            "score": round(score, 3),
            "items": [lines[i], lines[j]],
            "reason": f"Duplicate charge - same item billed twice",
            "suggested_saving": round(min(lines[i]['amount_num'], lines[j]['amount_num']), 2)
        })

    # inflation
    infl_flags = detect_inflation(lines)
    for f in infl_flags:
        flagged.append({
            "type": "inflated_vs_expected",
            "line_index": f.get('index'),
            "description": f.get('description'),
            "actual": f.get('actual'),
            "expected": f.get('expected'),
            "factor": round(f.get('actual') / max(f.get('expected'), 1), 2),
            "excess": f.get('excess'),
            "reason": f.get('reason', f"Charged ₹{f.get('actual'):,.0f} but expected ₹{f.get('expected'):,.0f}"),
            "suggested_saving": round(f.get('excess'), 2)
        })

    # totals checks
    totals_check = check_totals(lines, found_subtotal=subtotal, found_gst=gst, found_grand_total=grand)
    for t in totals_check.get('flags', []):
        flagged.append({"type": t['type'], **t})

    # Potential savings: sum of suggested_saving, but be conservative: max 80%
    potential = 0.0
    for f in flagged:
        s = f.get('suggested_saving') or f.get('excess') or 0.0
        potential += s
    potential = round(potential * 0.8, 2)  # conservative factor

    result = {
        "merchant": ocr_parsed.get('merchant') or ocr_parsed.get('hospital'),
        "date": ocr_parsed.get('date'),
        "grand_total": parse_amount(grand),
        "flagged_items": flagged,
        "potential_savings": potential,
        "computed_subtotal": totals_check.get('computed_subtotal'),
        "totals_check": totals_check
    }
    return result

# small helper to pretty print flagged items (for logs)
def flagged_summary(res: Dict[str, Any]) -> str:
    """Generate human-readable summary of flagged items."""
    out = []
    for f in res.get('flagged_items', []):
        if f['type'] == 'duplicate_item':
            out.append(f"Duplicate: items {f['indices']} save~₹{f['suggested_saving']}")
        elif f['type'] == 'inflated_vs_expected':
            out.append(f"Inflated: {f['description']} actual ₹{f['actual']:,} expected ₹{f['expected']:,} excess ₹{f['excess']:,}")
        else:
            out.append(str(f))
    out.append(f"Potential savings estimate: ₹{res.get('potential_savings')}")
    return "\n".join(out)
