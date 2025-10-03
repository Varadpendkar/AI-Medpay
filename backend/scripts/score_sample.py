#!/usr/bin/env python3
"""
Score a sample user with the current LTR model (or a specified model) and return top-K plan_ids.

Usage:
  python scripts/score_sample.py --user_id U0001 --topk 5 [--model /mnt/models/recommender/current/model.txt]
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

from backend.scripts.build_features import haversine_km  # reuse helper if needed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--user_id", required=True)
    ap.add_argument("--topk", type=int, default=5)
    ap.add_argument(
        "--model", default="/mnt/models/recommender/current/model.txt")
    args = ap.parse_args()

    # Load model
    booster = lgb.Booster(model_file=args.model)

    raw = Path("/mnt/data/raw")
    proc = Path("/mnt/data/processed")

    # Minimal features like in build_features
    plans = pd.read_parquet(proc/"plans.enriched.parquet")
    users = pd.read_csv(raw/"users.csv")
    hosp = pd.read_csv(raw/"hospitals.csv")
    mapdf = pd.read_csv(raw/"plan_hospital_map.csv")

    u = users[users["user_id"].astype(str) == str(args.user_id)]
    if u.empty:
        raise SystemExit(f"User {args.user_id} not found in users.csv")
    urec = u.iloc[0]

    # Candidate generation: top 50 by network_hospitals_count (or random if not present)
    if "network_hospitals_count" not in plans.columns:
        plans["network_hospitals_count"] = 0
    cands = plans.sort_values(
        "network_hospitals_count", ascending=False).head(50)

    # Pre-merge
    hosp_cols = [c for c in ["hospital_id", "city", "state",
                             "latitude", "longitude"] if c in hosp.columns]
    ph = mapdf.merge(hosp[hosp_cols], on="hospital_id", how="left")

    rows = []
    for _, prec in cands.iterrows():
        pid = prec["plan_id"]
        feat = {
            "age": float(urec.get("age", 0) or 0),
            "dependents": float(urec.get("dependents", 0) or 0),
            "premium": float(prec.get("premium", 0) or 0),
            "coverage_amount": float(prec.get("coverage_amount", 0) or 0),
            "deductible": float(prec.get("deductible", 0) or 0),
            "network_hospitals_count": float(prec.get("network_hospitals_count", 0) or 0),
        }
        feat["premium_per_100k_coverage"] = (
            feat["premium"] / (feat["coverage_amount"] / 100000.0 + 1e-9)
        )
        # Basic location features
        try:
            user_state = urec.get("state") if "state" in urec else None
            user_city = urec.get("city") if "city" in urec else None
            user_lat = urec.get("latitude") if "latitude" in urec else None
            user_lon = urec.get("longitude") if "longitude" in urec else None
            plan_hospitals = ph[ph["plan_id"] == pid]
            if user_state is not None and "state" in plan_hospitals.columns:
                plan_in_user_state = int(
                    plan_hospitals[plan_hospitals["state"] == user_state].shape[0] > 0)
            else:
                plan_in_user_state = 0
            if user_city is not None and "city" in plan_hospitals.columns:
                plan_network_size_in_user_city = int(
                    plan_hospitals[plan_hospitals["city"] == user_city].shape[0])
            else:
                plan_network_size_in_user_city = 0
            total = max(1, int(plan_hospitals["hospital_id"].nunique(
            ))) if "hospital_id" in plan_hospitals.columns else 1
            in_state = int(plan_hospitals[plan_hospitals.get("state") == user_state]["hospital_id"].nunique()) if (
                user_state is not None and "state" in plan_hospitals.columns and "hospital_id" in plan_hospitals.columns) else 0
            plan_network_fraction_in_user_state = in_state / total
            if (user_lat is not None and user_lon is not None and "latitude" in plan_hospitals.columns and "longitude" in plan_hospitals.columns):
                dists = []
                for _, h in plan_hospitals.iterrows():
                    d = haversine_km(urec.get('latitude', float('nan')), urec.get('longitude', float(
                        'nan')), h.get('latitude', float('nan')), h.get('longitude', float('nan')))
                    dists.append(d)
                distance_to_nearest_in_network_hospital = float(
                    min(dists)) if dists else 9999.0
            else:
                distance_to_nearest_in_network_hospital = 9999.0
        except Exception:
            plan_in_user_state = 0
            plan_network_size_in_user_city = 0
            plan_network_fraction_in_user_state = 0.0
            distance_to_nearest_in_network_hospital = 9999.0

        feat.update({
            "plan_in_user_state": plan_in_user_state,
            "plan_network_size_in_user_city": plan_network_size_in_user_city,
            "plan_network_fraction_in_user_state": plan_network_fraction_in_user_state,
            "distance_to_nearest_in_network_hospital": distance_to_nearest_in_network_hospital,
        })
        rows.append((pid, feat))

    feat_df = pd.DataFrame([f for _, f in rows])
    # Align features with model expectations if needed — here we assume model was trained with the same columns
    X = feat_df.values
    scores = booster.predict(X)
    out = sorted(list(zip([pid for pid, _ in rows], scores)),
                 key=lambda t: -t[1])[:args.topk]
    print("Top-{}:".format(args.topk))
    for pid, s in out:
        print(pid, float(s))


if __name__ == "__main__":
    main()
}
