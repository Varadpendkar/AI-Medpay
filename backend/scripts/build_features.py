#!/usr/bin/env python3
"""
Build training and validation feature sets from enriched plans, users, hospitals, and mappings.

Outputs:
  /mnt/data/processed/features.train.feather
  /mnt/data/processed/features.val.feather

NOTE: This is a simplified feature builder. Extend with your domain logic as needed.
"""
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
import math
import os


def haversine_km(lat1, lon1, lat2, lon2):
    """Haversine great-circle distance (km). Returns 9999.0 if any input is NaN."""
    try:
        if any(pd.isna([lat1, lon1, lat2, lon2])):
            return 9999.0
        R = 6371.0
        phi1, phi2 = math.radians(float(lat1)), math.radians(float(lat2))
        dphi = math.radians(float(lat2) - float(lat1))
        dlambda = math.radians(float(lon2) - float(lon1))
        a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    except Exception:
        return 9999.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/mnt/data/processed/features.train.feather")
    ap.add_argument("--val_out", default="/mnt/data/processed/features.val.feather")
    args = ap.parse_args()

    # Resolve base data paths: prefer /mnt if present, else fall back to project/data
    project_root = Path(__file__).resolve().parent.parent
    if Path("/mnt/data").exists():
        raw = Path("/mnt/data/raw")
        proc = Path("/mnt/data/processed")
    else:
        raw = project_root / "data"
        proc = project_root / "data" / "processed"
    proc.mkdir(parents=True, exist_ok=True)

    # Load plans: prefer enriched parquet else fallback to CSV
    plans_path_parquet = proc / "plans.enriched.parquet"
    if plans_path_parquet.exists():
        plans = pd.read_parquet(plans_path_parquet)
    else:
        csv_path = raw / "plans.csv"
        if not csv_path.exists():
            raise SystemExit(f"Missing plans file: {plans_path_parquet} or {csv_path}")
        plans = pd.read_csv(csv_path)
        # Normalize common columns
        ren = {
            "planid": "plan_id",
            "coverageamount": "coverage_amount",
            "networksize": "network_hospitals_count",
            "claimrejectionrate": "claim_rejection_rate",
            "waitingperioddays": "waiting_period_days",
        }
        lc = {c.lower(): c for c in plans.columns}
        for src, dst in ren.items():
            if dst not in plans.columns and src in lc:
                plans[dst] = plans[lc[src]]
        # Provide network_hospitals_count if only network_size is present
        if "network_hospitals_count" not in plans.columns and "network_size" in plans.columns:
            plans["network_hospitals_count"] = plans["network_size"]

    # Load users/interactions
    users = pd.read_csv(raw/"users.csv")
    inter = pd.read_csv(raw/"interactions.csv")
    # Normalize interactions columns
    if "plan_id" not in inter.columns and "planid" in inter.columns:
        inter["plan_id"] = inter["planid"].astype(str).str.strip()
    if "user_id" in inter.columns:
        inter["user_id"] = inter["user_id"].astype(str).str.strip()

    # Hospitals and plan-hospital map with tolerant file naming
    hosp_path = raw/"hospitals.csv"
    if not hosp_path.exists():
        alt = raw/"hospitals_large.csv"
        if alt.exists():
            hosp_path = alt
    map_path = raw/"plan_hospital_map.csv"
    if not map_path.exists():
        altm = raw/"plan_hospital_map_large.csv"
        if altm.exists():
            map_path = altm
    hosp = pd.read_csv(hosp_path)
    mapdf = pd.read_csv(map_path)

    # Pre-merge plan-hospital info for faster lookups
    hosp_cols = [c for c in ["hospital_id","city","state","latitude","longitude"] if c in hosp.columns]
    ph = mapdf.merge(hosp[hosp_cols], on="hospital_id", how="left")

    # Basic normalization
    for df in (plans, users, inter):
        for c in df.select_dtypes(include=["object"]).columns:
            df[c] = df[c].astype(str).str.strip()

    # Select interaction relevance (purchase>click>view)
    if "event_type" in inter.columns:
        rel_map = {"purchase": 5, "quote_request": 3, "click": 1, "claim_approved": 5, "view": 0}
        inter["relevance"] = inter["event_type"].astype(str).str.strip().map(rel_map).fillna(0).astype(int)
    else:
        # fallback: chosen column
        inter["relevance"] = inter.get("chosen", 0).fillna(0).astype(int)

    # Candidate generation: for each positive, sample negatives (naive sampling)
    rng = np.random.default_rng(42)
    positives = inter[inter["relevance"] > 0].copy()
    if positives.empty:
        print("No positives in interactions — cannot build supervised ranking dataset.")
        return

    rows = []
    plan_ids = plans["plan_id"].dropna().unique()

    for _, row in positives.iterrows():
        user_id = row["user_id"]
        pos_plan = row["plan_id"]
        # sample 49 negatives
        # filter to plans not equal to positive; (optionally) same state, etc.
        neg_pool = plan_ids[plan_ids != pos_plan]
        if len(neg_pool) == 0:
            candidates = [pos_plan]
        else:
            n = min(49, len(neg_pool))
            negs = rng.choice(neg_pool, size=n, replace=False)
            candidates = [pos_plan] + list(negs)

        u = users[users["user_id"] == user_id]
        if u.empty:
            continue
        urec = u.iloc[0]

        for pid in candidates:
            p = plans[plans["plan_id"] == pid]
            if p.empty:
                continue
            prec = p.iloc[0]

            # Minimal features — extend as needed
            feat = {
                "user_id": user_id,
                "plan_id": pid,
                "group_id": user_id,  # group by user for ranking
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

            # Location features (tolerant to missing columns)
            try:
                user_state = urec.get("state") if "state" in urec else None
                user_city = urec.get("city") if "city" in urec else None
                user_lat = urec.get("latitude") if "latitude" in urec else None
                user_lon = urec.get("longitude") if "longitude" in urec else None

                plan_hospitals = ph[ph["plan_id"] == pid]
                # plan_in_user_state: any hospital state matches
                if user_state is not None and "state" in plan_hospitals.columns:
                    plan_in_user_state = int(plan_hospitals[plan_hospitals["state"] == user_state].shape[0] > 0)
                else:
                    plan_in_user_state = 0
                # network size in user city
                if user_city is not None and "city" in plan_hospitals.columns:
                    plan_network_size_in_user_city = int(plan_hospitals[plan_hospitals["city"] == user_city].shape[0])
                else:
                    plan_network_size_in_user_city = 0
                # fraction in state
                total = max(1, int(plan_hospitals["hospital_id"].nunique())) if "hospital_id" in plan_hospitals.columns else 1
                in_state = int(plan_hospitals[plan_hospitals.get("state") == user_state]["hospital_id"].nunique()) if (user_state is not None and "state" in plan_hospitals.columns and "hospital_id" in plan_hospitals.columns) else 0
                plan_network_fraction_in_user_state = in_state / total
                # distance to nearest in-network hospital
                if (user_lat is not None and user_lon is not None and "latitude" in plan_hospitals.columns and "longitude" in plan_hospitals.columns):
                    dists = []
                    for _, h in plan_hospitals.iterrows():
                        d = haversine_km(urec.get('latitude', float('nan')), urec.get('longitude', float('nan')), h.get('latitude', float('nan')), h.get('longitude', float('nan')))
                        dists.append(d)
                    distance_to_nearest_in_network_hospital = float(min(dists)) if dists else 9999.0
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

            feat["label"] = 5 if pid == pos_plan else 0
            rows.append(feat)

    df = pd.DataFrame(rows)

    # Train/val split by user (holdout 20% users)
    users_all = df["user_id"].drop_duplicates().to_list()
    rng.shuffle(users_all)
    cut = int(0.8 * len(users_all))
    train_users = set(users_all[:cut])
    val_users = set(users_all[cut:])

    train_df = df[df["user_id"].isin(train_users)].reset_index(drop=True)
    val_df = df[df["user_id"].isin(val_users)].reset_index(drop=True)

    # Save
    out_path = Path(args.out)
    val_path = Path(args.val_out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    val_path.parent.mkdir(parents=True, exist_ok=True)

    train_df.to_feather(out_path)
    val_df.to_feather(val_path)
    print("Wrote:", out_path)
    print("Wrote:", val_path)

if __name__ == "__main__":
    main()
