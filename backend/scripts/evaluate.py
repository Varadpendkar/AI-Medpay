#!/usr/bin/env python3
"""
Evaluate a trained LightGBM LTR model on a validation feature set and report NDCG@K.

Usage:
  python scripts/evaluate.py --model /mnt/models/recommender/current/model.txt --val /mnt/data/processed/features.val.feather
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import lightgbm as lgb

def ndcg_at_k_by_group(model, X, y, group_sizes, ks=(1,3,5)):
    preds = model.predict(X)
    offset = 0
    scores = {k: [] for k in ks}
    for g in group_sizes:
        s = preds[offset:offset+g]
        r = y[offset:offset+g]
        offset += g
        order = np.argsort(-s)
        r_sorted = r[order]
        for k in ks:
            rr = r_sorted[:k]
            dcg = np.sum((2**rr - 1) / np.log2(np.arange(2, len(rr)+2)))
            ideal = np.sort(r)[::-1][:k]
            idcg = np.sum((2**ideal - 1) / np.log2(np.arange(2, len(ideal)+2)))
            nd = (dcg / idcg) if idcg > 0 else 0.0
            scores[k].append(nd)
    return {f"ndcg@{k}": float(np.mean(v) if v else 0.0) for k, v in scores.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--val", required=True)
    args = ap.parse_args()

    # Load model
    booster = lgb.Booster(model_file=args.model)

    # Load val features
    val_df = pd.read_feather(args.val)
    feature_cols = [c for c in val_df.columns if c not in ("label","group_id","user_id","plan_id")]
    X_val = val_df[feature_cols].values
    y_val = val_df["label"].astype(int).values
    gval = val_df.groupby("group_id").size().to_numpy()

    scores = ndcg_at_k_by_group(booster, X_val, y_val, gval, ks=(1,3,5))
    print("Validation:", scores)

if __name__ == "__main__":
    main()
