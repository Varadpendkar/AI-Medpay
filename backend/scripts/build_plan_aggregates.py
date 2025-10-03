#!/usr/bin/env python3
"""
Build plan aggregates from raw data and write enriched plans parquet.

Inputs:
  /mnt/data/raw/plans.csv
  /mnt/data/raw/hospitals.csv
  /mnt/data/raw/plan_hospital_map.csv

Outputs:
  /mnt/data/processed/plans.enriched.parquet
"""
import pandas as pd
from pathlib import Path

def main():
    raw = Path("/mnt/data/raw")
    proc = Path("/mnt/data/processed")
    proc.mkdir(parents=True, exist_ok=True)

    plans = pd.read_csv(raw/"plans.csv")
    mapdf = pd.read_csv(raw/"plan_hospital_map.csv")
    hosp = pd.read_csv(raw/"hospitals.csv")

    # counts
    counts = (
        mapdf.groupby("plan_id")["hospital_id"].nunique()
        .reset_index()
        .rename(columns={"hospital_id": "network_hospitals_count"})
    )

    # sample top 3 hospital ids by rank if present, else first 3
    ordered = mapdf
    if "rank" in ordered.columns:
        ordered = ordered.sort_values(["plan_id", "rank"])  # ascending rank
    sample = (
        ordered.groupby("plan_id").head(3)
        .groupby("plan_id")["hospital_id"].apply(lambda x: ",".join(map(str, x)))
        .reset_index().rename(columns={"hospital_id": "sample_hospitals"})
    )

    # city aggregation
    map_h = mapdf.merge(hosp[["hospital_id","city","state"]], on="hospital_id", how="left")
    city_agg = (
        map_h.groupby("plan_id")["city"]
        .apply(lambda s: ",".join(sorted(set([str(x) for x in s.dropna()]))))
        .reset_index().rename(columns={"city": "geos_cities_from_hospitals"})
    )

    enriched = (
        plans.merge(counts, on="plan_id", how="left")
             .merge(sample, on="plan_id", how="left")
             .merge(city_agg, on="plan_id", how="left")
    )
    enriched["network_hospitals_count"] = enriched["network_hospitals_count"].fillna(0).astype(int)

    out_path = proc/"plans.enriched.parquet"
    enriched.to_parquet(out_path, index=False)
    print("Wrote:", out_path)

if __name__ == "__main__":
    main()
