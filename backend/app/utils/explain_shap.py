# utils/explain_shap.py
"""
Optional SHAP explainability helper for LightGBM models.

Usage:
  from utils.explain_shap import shap_top_contributors
  top = shap_top_contributors(model, X_row, feature_names, top_k=3)
Returns a list of {name, value} sorted by absolute contribution.
"""
from typing import List, Dict

def shap_top_contributors(model, X_row, feature_names: List[str], top_k: int = 3) -> List[Dict]:
    try:
        import shap  # type: ignore
    except Exception:
        return []
    try:
        explainer = shap.TreeExplainer(model)
        vals = explainer.shap_values(X_row.reshape(1, -1))
        if isinstance(vals, list):  # for classification list per class
            vals = vals[0]
        vals = vals.flatten()
        pairs = list(zip(feature_names, vals))
        pairs.sort(key=lambda kv: abs(kv[1]), reverse=True)
        top = [{"name": k, "value": float(v)} for k, v in pairs[:top_k]]
        return top
    except Exception:
        return []
