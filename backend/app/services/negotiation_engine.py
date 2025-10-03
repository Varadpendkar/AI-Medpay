# negotiation_engine.py
from typing import List, Dict, Any, Optional

# Very small, demo-friendly expected price heuristics.
# In production, connect to a real price reference or negotiated rate tables.

def estimate_expected_cost(desc: str) -> float:
    d = (desc or "").lower()
    if "x-ray" in d or "xray" in d or "x ray" in d:
        return 100.0
    if "consult" in d:
        return 50.0
    if "drug" in d or "medicine" in d or "medication" in d or "paracetamol" in d:
        return 30.0
    # generic fallback
    return 75.0


def analyze_parsed_items(parsed_items: List[Dict[str, Any]], user: Optional[Dict[str, Any]] = None, plan_id: Optional[str] = None) -> Dict[str, Any]:
    anomalies: List[Dict[str, Any]] = []
    estimated_savings = 0.0

    for item in parsed_items or []:
        desc = item.get("description", "")
        actual = float(item.get("amount") or 0.0)
        expected = estimate_expected_cost(desc)
        if expected <= 0:
            continue
        # Flag high charges (actual > 1.8x expected and > 20 currency units)
        if actual > max(20.0, 1.8 * expected):
            diff = actual - expected
            anomalies.append({
                "line_id": item.get("line_id"),
                "description": desc,
                "actual_cost": round(actual, 2),
                "expected_cost": round(expected, 2),
                "issue": "high_charge",
                "explanation": f"Charge is {actual:.2f} which is {actual/expected:.1f}x typical ({expected:.2f}).",
            })
            estimated_savings += diff

    if anomalies:
        lines = [f"- {a['description']}: billed {a['actual_cost']:.2f}, typical {a['expected_cost']:.2f}" for a in anomalies]
        bullet_text = "\n".join(lines)
        snippet = (
            "Dear Billing Department,\n\n"
            "I am requesting a review of the following line items on my bill which appear high compared to typical prices:\n\n"
            f"{bullet_text}\n\n"
            "Please provide itemized justification or revise the billed amounts. Thank you.\n"
        )
    else:
        snippet = (
            "No clear anomalies detected. Consider requesting an itemized bill and cross-checking charges if you believe there are errors."
        )

    return {
        "anomalies": anomalies,
        "negotiation_snippet": snippet,
        "estimated_savings": round(estimated_savings, 2),
    }
