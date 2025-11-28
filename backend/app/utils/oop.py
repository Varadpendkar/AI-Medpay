# backend/app/utils/oop.py
import os
import math
import pandas as pd
from typing import Dict, Any, Tuple, List

# Adjust if your layout differs — this file is in backend/app/utils -> go up to backend/app/ then to backend/models
THIS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_ROOT = os.path.dirname(
    os.path.dirname(THIS_DIR))  # backend/app -> backend
PROCEDURES_PATH = os.path.join(
    BACKEND_ROOT, "models", "procedures_full_50.csv")

_procs_df = None


def load_procedures(force_reload: bool = False) -> pd.DataFrame:
    global _procs_df
    if _procs_df is None or force_reload:
        if not os.path.exists(PROCEDURES_PATH):
            raise FileNotFoundError(
                f"procedures CSV not found at: {PROCEDURES_PATH}")
        _procs_df = pd.read_csv(PROCEDURES_PATH)
    return _procs_df


def _safe_float(x, default=0.0):
    try:
        if x is None:
            return float(default)
        return float(x)
    except Exception:
        return float(default)


def estimate_oop_for_plan(procedure_code: str, user_profile: Dict[str, Any], plan: Dict[str, Any], procedures_df: pd.DataFrame = None) -> Tuple[float, Dict[str, Any]]:
    """
    Heuristic OOP estimator. Returns (oop_value, breakdown_dict).
    Uses: avg_cost from procedures CSV, plan keys: coverage_amount, deductible, copay_pct (0-100) or copay_flat, network_size.
    """
    if procedures_df is None:
        procedures_df = load_procedures()
    proc = procedures_df[procedures_df['procedure_code'] == procedure_code]
    if proc.empty:
        raise ValueError(f"Unknown procedure_code: {procedure_code}")

    total_cost = float(proc.iloc[0]['avg_cost'])

    coverage_amount = _safe_float(plan.get('coverage_amount') or plan.get(
        'coverageamount') or plan.get('plan_coverage') or 0)
    deductible = _safe_float(plan.get('deductible')
                             or plan.get('deductible_amount') or 0)
    copay_pct = _safe_float(plan.get('copay_pct') or plan.get('copay') or 0)
    copay_flat = _safe_float(plan.get('copay_flat') or 0)
    network_size = _safe_float(plan.get('network_size') or plan.get(
        'networksize') or plan.get('plan_network') or 0)

    # Simple network discount assumption
    network_discount = 0.0
    if network_size >= 200:
        network_discount = 0.05
    elif network_size >= 50:
        network_discount = 0.02

    discounted_cost = total_cost * (1 - network_discount)
    covered_by_plan = min(
        coverage_amount, discounted_cost) if coverage_amount > 0 else 0.0
    deductible_applied = min(deductible, discounted_cost)
    remaining_after_deductible = max(discounted_cost - deductible_applied, 0.0)

    if copay_pct > 0:
        copay_amount = remaining_after_deductible * (copay_pct / 100.0)
    else:
        copay_amount = min(copay_flat, remaining_after_deductible)

    reimbursable = max(min(covered_by_plan - deductible_applied -
                       copay_amount, remaining_after_deductible - copay_amount), 0.0)
    oop = max(discounted_cost - reimbursable, 0.0)
    oop = round(oop, 2)

    breakdown = {
        "total_cost": round(discounted_cost, 2),
        "coverage_amount": round(coverage_amount, 2),
        "deductible_applied": round(deductible_applied, 2),
        "copay_amount": round(copay_amount, 2),
        "reimbursable": round(reimbursable, 2),
        "oop": oop,
        "network_discount_pct": round(network_discount * 100, 2)
    }
    return oop, breakdown


def estimate_oop_for_plans(procedure_code: str, user_profile: Dict[str, Any], plans: List[Dict[str, Any]], procedures_df: pd.DataFrame = None):
    df = procedures_df if procedures_df is not None else load_procedures()
    results = []
    for p in plans:
        try:
            oop, breakdown = estimate_oop_for_plan(
                procedure_code, user_profile, p, procedures_df=df)
        except Exception as e:
            oop, breakdown = None, {"error": str(e)}
        results.append({"plan_id": p.get("plan_id") or p.get(
            "planid"), "plan": p, "oop": oop, "breakdown": breakdown})
    return results
