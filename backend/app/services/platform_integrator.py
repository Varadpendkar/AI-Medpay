# platform_integrator.py
import os
import json
from typing import List, Dict, Any, Optional
import pandas as pd

ROOT = os.path.abspath(os.path.dirname(__file__))
DATA_DIR = os.path.join(ROOT, "data")
PLANS_CSV = os.path.join(DATA_DIR, "plans.csv")
MOCK_PLATFORMS_JSON = os.path.join(DATA_DIR, "mock_platforms.json")

# Canonical plan schema the frontend expects
PLAN_FIELDS = [
    "plan_id", "provider", "plan_name", "monthly_premium",
    "deductible", "network_size", "riders", "coverage_year",
    "source"
]


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=PLAN_FIELDS)


def _load_internal_plans() -> pd.DataFrame:
    """Load internal plans.csv and normalize column names to canonical schema."""
    if not os.path.exists(PLANS_CSV):
        return _empty_df()
    try:
        df = pd.read_csv(PLANS_CSV)
        # Map columns
        df = df.rename(columns={
            "premium": "monthly_premium",
            "addons": "riders",
        })
        # Ensure required columns exist
        for col in ["plan_id", "provider", "plan_name", "monthly_premium", "deductible", "network_size", "riders"]:
            if col not in df.columns:
                df[col] = None
        # Riders: ensure list-like
        if "riders" in df.columns:
            df["riders"] = df["riders"].fillna("").apply(
                lambda s: [] if str(s).strip() == "" else [x.strip() for x in str(s).split(";") if x.strip()]
            )
        # Numeric coercions
        for col in ["monthly_premium", "deductible", "network_size"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        # Plan name fallback to plan_id if missing
        df["plan_name"] = df["plan_name"].fillna(df["plan_id"].astype(str))
        df["coverage_year"] = None
        df["source"] = "internal"
        # Keep only canonical fields
        keep = [c for c in PLAN_FIELDS if c in df.columns]
        return df[keep]
    except Exception:
        return _empty_df()


def _load_mock_platforms() -> List[Dict[str, Any]]:
    """Read mock platforms JSON and normalize values to canonical schema."""
    if not os.path.exists(MOCK_PLATFORMS_JSON):
        return []
    try:
        with open(MOCK_PLATFORMS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for plat in data or []:
        platform_name = plat.get("platform") or "mock_platform"
        for p in plat.get("plans", []) or []:
            plan_id = p.get("id") or p.get("plan_id") or p.get("code")
            provider = p.get("provider") or p.get("issuer") or platform_name
            plan_name = p.get("title") or p.get("plan_name") or p.get("name") or str(plan_id)
            monthly = p.get("price_monthly") or p.get("monthly_premium") or p.get("price") or 0
            deductible = p.get("deductible") or p.get("out_of_pocket") or 0
            network = p.get("network_size") or p.get("network") or 0
            riders = p.get("riders") or []
            out.append({
                "plan_id": str(plan_id),
                "provider": provider,
                "plan_name": plan_name,
                "monthly_premium": float(monthly) if monthly is not None else 0.0,
                "deductible": float(deductible) if deductible is not None else 0.0,
                "network_size": int(network) if network else 0,
                "riders": riders,
                "coverage_year": p.get("coverage_year") or None,
                "source": f"mock::{platform_name}",
            })
    return out


def list_platforms() -> List[Dict[str, str]]:
    plats = [{"id": "internal", "name": "Internal"}]
    if os.path.exists(MOCK_PLATFORMS_JSON):
        try:
            with open(MOCK_PLATFORMS_JSON, "r", encoding="utf-8") as f:
                md = json.load(f) or []
                for m in md:
                    pname = m.get("platform")
                    if pname:
                        plats.append({"id": f"mock::{pname}", "name": pname})
        except Exception:
            pass
    return plats


def get_plans(source: str = "internal", limit: Optional[int] = None) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    if source in ("internal", "all"):
        idf = _load_internal_plans()
        result.extend(idf.to_dict(orient="records"))
    if source.startswith("mock") or source == "all":
        result.extend(_load_mock_platforms())
    if limit is not None:
        result = result[: int(limit)]
    return result


def get_plan_by_id(plan_id: str) -> Optional[Dict[str, Any]]:
    # Check internal first
    idf = _load_internal_plans()
    if not idf.empty:
        m = idf[idf["plan_id"].astype(str) == str(plan_id)]
        if not m.empty:
            return m.iloc[0].to_dict()
    # Check mocks
    for p in _load_mock_platforms():
        if str(p.get("plan_id")) == str(plan_id):
            return p
    return None
