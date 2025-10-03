#!/usr/bin/env python3
"""
Validate presence and keys of raw data files under /mnt/data/raw.

Usage:
  python scripts/prepare_data.py

(This script prints counts and basic assertions. It does not mutate files.)
"""
import pandas as pd
from pathlib import Path

def main():
    raw = Path("/mnt/data/raw")
    plans = pd.read_csv(raw / "plans.csv")
    hosp = pd.read_csv(raw / "hospitals.csv")
    mapdf = pd.read_csv(raw / "plan_hospital_map.csv")
    users = pd.read_csv(raw / "users.csv")
    inter = pd.read_csv(raw / "interactions.csv")

    print("plans:", len(plans), "hospitals:", len(hosp), "mappings:", len(mapdf), "users:", len(users), "interactions:", len(inter))

    # Canonical key checks
    assert "plan_id" in plans.columns, "plans.csv must contain plan_id"
    assert "hospital_id" in hosp.columns, "hospitals.csv must contain hospital_id"

    # Mapping to known ids
    unknown_plans = set(mapdf["plan_id"].unique()) - set(plans["plan_id"].unique())
    unknown_hosp = set(mapdf["hospital_id"].unique()) - set(hosp["hospital_id"].unique())
    if unknown_plans:
        raise AssertionError(f"map contains unknown plan_ids: {list(list(unknown_plans)[:5])} ... (total {len(unknown_plans)})")
    if unknown_hosp:
        raise AssertionError(f"map contains unknown hospital_ids: {list(list(unknown_hosp)[:5])} ... (total {len(unknown_hosp)})")

    # Null keys report
    for df, name in [(plans, "plans"), (hosp, "hospitals"), (mapdf, "map")]:
        null_key_rows = df[df.iloc[:, 0].isnull()]
        print(name, "null key rows:", len(null_key_rows))

    print("OK: raw data validation passed.")

if __name__ == "__main__":
    main()
