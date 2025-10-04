# utils/ranker.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
from lightgbm import Booster

# Updated feature list to match the trained model (11 features)
FEATURES = [
    "age", "dependents", "risk_score", "income",
    "premium", "deductible", "copay", "coverage_amount",
    "network_size", "claim_rejection_rate", "waiting_period_days"
]


def _add_features(user: dict, plans: pd.DataFrame) -> pd.DataFrame:
    df = plans.copy()

    # Ensure required plan columns exist
    for col, default in [
        ("premium", 0.0), ("deductible",
                           0.0), ("copay", 0.0), ("coverage_amount", 0.0),
        ("network_size", 0.0), ("claim_rejection_rate",
                                0.0), ("waiting_period_days", 0.0)
    ]:
        if col not in df.columns:
            df[col] = default

    # Add user features (simplified to match training data)
    df["age"] = int(user.get("age", 30))
    df["dependents"] = int(user.get("dependents", 0))
    df["risk_score"] = float(user.get("risk_score", 0.2))
    # Default to middle income
    df["income"] = float(user.get("income", 800000))

    # Ensure all features are numeric and handle missing values
    df[FEATURES] = df[FEATURES].replace([np.inf, -np.inf], np.nan).fillna(0)
    return df


def _bullets(user, r):
    bullets = []
    pir = r["premium"] / max(float(user.get("income", 1)), 1.0)
    bullets.append("Affordable premium for your income." if pir < 0.03 else
                   "Premium is balanced for your income." if pir < 0.06 else
                   "Higher premium relative to income.")
    if r.get("network_size", 0) >= 100:
        bullets.append("Good hospital network.")
    if r.get("claim_rejection_rate", 1.0) <= 0.1:
        bullets.append("Low claim rejection rate.")
    if r.get("deductible", 0) <= 15000:
        bullets.append("Reasonable deductible.")
    return bullets[:4]


class PlanRanker:
    def __init__(self, project_root: Path):
        self.root = Path(project_root)
        # Resolve model path with multiple fallbacks
        env_model = os.environ.get(
            "RANKER_MODEL_PATH") or os.environ.get("LTR_MODEL_PATH")
        candidates = [
            env_model,
            str(self.root / "models" / "ltr_model.txt"),
            "/mnt/models/recommender/current/model.txt",
            str(self.root / "ltr_model.txt"),
        ]
        model_path = next((Path(p)
                          for p in candidates if p and Path(p).exists()), None)
        if not model_path:
            # Last resort: raise a clear error
            raise FileNotFoundError(
                "No LTR model file found. Set RANKER_MODEL_PATH or place models/ltr_model.txt."
            )
        self.booster = Booster(model_file=str(model_path))

        data_dir = self.root.parent/"data"  # backend/data instead of backend/app/data
        self.plans = pd.read_csv(data_dir / "plans.csv")
        # Normalize column names expected by features
        colmap = {
            "planid": "plan_id",
            "coverageamount": "coverage_amount",
            "networksize": "network_size",
            "claimrejectionrate": "claim_rejection_rate",
            "waitingperioddays": "waiting_period_days",
        }
        lower_cols = {c.lower(): c for c in self.plans.columns}
        for src_lower, dst in colmap.items():
            if dst not in self.plans.columns and src_lower in lower_cols:
                self.plans[dst] = self.plans[lower_cols[src_lower]]
        # Ensure provider exists as string
        if "provider" in self.plans.columns:
            self.plans["provider"] = self.plans["provider"].astype(
                str).fillna("")
        # Coerce numeric fields
        for nc in [
            "premium", "deductible", "copay", "coverage_amount", "network_size",
            "claim_rejection_rate", "waiting_period_days"
        ]:
            if nc in self.plans.columns:
                self.plans[nc] = pd.to_numeric(
                    self.plans[nc], errors="coerce").fillna(0)

    def _explain(self, plans_df: pd.DataFrame, row: pd.Series) -> dict:
        # Compute simple contributions for demo explainability
        # Normalize components against the candidate set
        def safe_minmax(series):
            try:
                s = pd.to_numeric(series, errors="coerce").replace(
                    [np.inf, -np.inf], np.nan).dropna()
                if s.empty:
                    return 0.0, 1.0
                return float(s.min()), float(s.max())
            except Exception:
                return 0.0, 1.0
        pmin, pmax = safe_minmax(plans_df.get("premium", 0))
        nmin, nmax = safe_minmax(plans_df.get("network_size", 0))
        rrmin, rrmax = safe_minmax(plans_df.get("claim_rejection_rate", 0))

        premium = float(row.get("premium") or 0.0)
        network = float(row.get("network_size") or 0.0)
        rej = float(row.get("claim_rejection_rate") or 0.0)
        prov = int(row.get("provider_match") or 0)

        # Invert premium: lower premium -> higher contribution
        if pmax == pmin:
            premium_norm = 0.5
        else:
            premium_norm = 1.0 - (premium - pmin) / max(1e-9, (pmax - pmin))
        premium_norm = float(np.clip(premium_norm, 0.0, 1.0))

        # Network: larger is better
        if nmax == nmin:
            network_norm = 0.5
        else:
            network_norm = (network - nmin) / max(1e-9, (nmax - nmin))
        network_norm = float(np.clip(network_norm, 0.0, 1.0))

        # Rejection rate: lower is better, invert
        if rrmax == rrmin:
            rej_norm = 0.5
        else:
            rej_norm = 1.0 - (rej - rrmin) / max(1e-9, (rrmax - rrmin))
        rej_norm = float(np.clip(rej_norm, 0.0, 1.0))

        provider_norm = float(1.0 if prov == 1 else 0.0)

        # weights for demo
        w = {
            "low_premium": 0.5,
            "large_network": 0.3,
            "provider_match": 0.1,
            "low_rejections": 0.1,
        }
        raw = {
            "low_premium": premium_norm * w["low_premium"],
            "large_network": network_norm * w["large_network"],
            "provider_match": provider_norm * w["provider_match"],
            "low_rejections": rej_norm * w["low_rejections"],
        }
        total = sum(raw.values()) or 1.0
        contrib = {k: float(v/total) for k, v in raw.items()}
        # Build top-3 list with human text
        texts = {
            "low_premium": "Low premium relative to peers",
            "large_network": "Large hospital network",
            "provider_match": "Matches your preferred provider",
            "low_rejections": "Low claim rejection rate",
        }
        top = sorted(contrib.items(), key=lambda kv: kv[1], reverse=True)[:3]
        top_features = [{"name": k, "contribution": round(
            v, 4), "text": texts.get(k, k)} for k, v in top]
        explain_text = ", ".join(
            [f"{f['text']} ({int(round(f['contribution']*100))}%)" for f in top_features])
        return {"scores": contrib, "top_features": top_features, "text": explain_text}

    def rank(self, user: dict, k: int = 8):
        state = user.get("state")
        plans = self.plans
        if state and "geos" in plans.columns:
            filt = plans["geos"].astype(str).str.contains(
                str(state), case=False, na=False)
            plans = plans[filt] if filt.any() else plans

        cap = user.get("max_premium") or 0
        if cap and cap > 0 and "premium" in plans.columns:
            plans = plans[pd.to_numeric(
                plans["premium"], errors="coerce").fillna(np.inf) <= cap]

        feats = _add_features(user, plans)

        if feats.empty:
            return []

        scores = self.booster.predict(feats[FEATURES].values)

        # attach only the columns that exist
        ranked = plans.copy().reset_index(drop=True)
        ranked["provider_match"] = feats["provider_match"].values
        ranked["premium_income_ratio"] = feats["premium_income_ratio"].values
        ranked["score"] = scores

        # Precompute explain normalization from candidate set
        norm_df = ranked.copy()

        ranked = ranked.sort_values("score", ascending=False).head(
            k).reset_index(drop=True)

        recs = []
        for _, r in ranked.iterrows():
            rec_item = r.to_dict()
            rec_item["bullets"] = _bullets(user, r)
            rec_item["score"] = float(r["score"])
            for key in ["coverage_amount", "premium", "deductible", "network_size"]:
                if key in rec_item:
                    rec_item[key] = int(rec_item[key])
            # Explainability
            expl = self._explain(norm_df, r)
            rec_item["explain_scores"] = expl["scores"]
            rec_item["explain_top_features"] = expl["top_features"]
            rec_item["explain_text"] = expl["text"]
            recs.append(rec_item)

        return recs
