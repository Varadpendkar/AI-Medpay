#!/usr/bin/env python3
"""
Preprocess raw CSVs into training matrices for ranking.

Usage:
  python src/preprocess.py \
    --plans /mnt/data/plans.csv \
    --users /mnt/data/users.csv \
    --interactions /mnt/data/interactions.csv \
    --out_dir data/processed

Outputs (in --out_dir):
  train_features.csv, train_labels.csv, group.csv
  And in outputs/: feature_name_list.json, preprocessor.pkl (lightweight metadata)
"""
import argparse
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pickle

FEATURES = [
    # user features
    "age", "dependents", "risk_score",
    "past_claims_count", "past_claims_amount", "income",
    # engineered user-log
    "log_past_claims_amount", "log_income",
    # plan features
    "premium", "deductible", "copay", "coverage_amount",
    "network_size", "claim_rejection_rate", "waiting_period_days",
    # engineered plan
    "addons_count", "premium_income_ratio",
    # interaction/popularity
    "plan_clicks", "plan_enrolls", "plan_views"
]


def load_and_clean(plans_p: str, users_p: str, inter_p: str):
    plans = pd.read_csv(plans_p)
    users = pd.read_csv(users_p)
    inter = pd.read_csv(inter_p)

    # Basic normalization
    for df in (plans, users):
        for c in df.select_dtypes(include=['object']).columns:
            df[c] = df[c].astype(str).str.strip()

    # numeric coercions
    for c in ["premium","deductible","copay","coverage_amount","network_size","claim_rejection_rate","waiting_period_days"]:
        if c in plans.columns:
            plans[c] = pd.to_numeric(plans[c], errors="coerce").fillna(0)
        else:
            plans[c] = 0.0

    # addons list
    if "addons" in plans.columns:
        plans["addons_count"] = plans["addons"].fillna("").apply(lambda s: 0 if str(s).strip()=="" else len([x for x in str(s).replace(";",",").split(",") if x.strip()]))
    else:
        plans["addons_count"] = 0

    # user numerics
    for c in ["age","dependents","risk_score","past_claims_count","past_claims_amount","income"]:
        if c in users.columns:
            users[c] = pd.to_numeric(users[c], errors="coerce").fillna(0)
        else:
            users[c] = 0.0

    users["log_past_claims_amount"] = np.log1p(users.get("past_claims_amount", 0))
    users["log_income"] = np.log1p(users.get("income", 0))

    # popularity from interactions
    inter["clicked"] = pd.to_numeric(inter.get("clicked", 0), errors="coerce").fillna(0)
    inter["chosen"] = pd.to_numeric(inter.get("chosen", 0), errors="coerce").fillna(0)
    pop = inter.groupby("plan_id").agg(plan_clicks=("clicked","sum"), plan_enrolls=("chosen","sum"), plan_views=("plan_id","count")).reset_index()

    # joins
    df = inter.merge(users, on="user_id", how="left").merge(plans, on="plan_id", how="left").merge(pop, on="plan_id", how="left")

    # engineered
    prem = pd.to_numeric(df.get("premium", 0), errors="coerce").fillna(0)
    inc = pd.to_numeric(df.get("income", 0), errors="coerce").fillna(0)
    df["premium_income_ratio"] = prem / inc.replace(0, np.nan)
    df["premium_income_ratio"] = df["premium_income_ratio"].replace([np.inf,-np.inf], np.nan).fillna(0)

    # label
    y = df.get("chosen", 0).fillna(0).astype(int)

    # groups: group by session_id if present, else by user_id
    grp_key = "session_id" if "session_id" in df.columns else "user_id"
    groups = df.groupby(grp_key).size().reset_index(name="cnt")

    # select features
    for f in FEATURES:
        if f not in df.columns:
            df[f] = 0.0
    X = df[FEATURES].replace([np.inf,-np.inf], np.nan).fillna(0)

    return X, y, df[grp_key].values, groups


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plans", required=True)
    ap.add_argument("--users", required=True)
    ap.add_argument("--interactions", required=True)
    ap.add_argument("--out_dir", required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    X, y, grp_ids, groups = load_and_clean(args.plans, args.users, args.interactions)

    # Persist training matrices
    X.to_csv(out_dir/"train_features.csv", index=False)
    pd.Series(y, name="label").to_csv(out_dir/"train_labels.csv", index=False)
    groups.to_csv(out_dir/"group.csv", index=False)

    # Save feature list and a tiny preprocessor metadata
    outputs_dir = Path("outputs")
    outputs_dir.mkdir(exist_ok=True)
    (outputs_dir/"feature_name_list.json").write_text(json.dumps(FEATURES, indent=2))
    with open(outputs_dir/"preprocessor.pkl", "wb") as f:
        pickle.dump({"feature_names": FEATURES, "note": "No-op preprocessor; features numeric and pre-scaled via log transforms."}, f)

    print(f"Wrote: {out_dir/'train_features.csv'}, {out_dir/'train_labels.csv'}, {out_dir/'group.csv'}")
    print(f"Wrote: outputs/feature_name_list.json, outputs/preprocessor.pkl")


if __name__ == "__main__":
    main()
