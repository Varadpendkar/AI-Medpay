#!/usr/bin/env python3
"""
Train LightGBM LambdaRank on prepared features.

Usage:
  python scripts/train_ltr.py \
    --train /mnt/data/processed/features.train.feather \
    --val /mnt/data/processed/features.val.feather \
    --out_dir /mnt/models/recommender/$(date +%Y%m%d_%H%M%S)

Outputs:
  out_dir/model.txt
  out_dir/feature_columns.pkl
  out_dir/training_metadata.json

(Optionally create a symlink /mnt/models/recommender/current → out_dir.)
"""
import argparse
import json
import time
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd


def ndcg_eval_at(model, X, y, group, ks=(1,3,5)):
    # simple in-memory NDCG computation on the provided set
    preds = model.predict(X)
    # split predictions by group sizes
    offset = 0
    scores = {k: [] for k in ks}
    for g in group:
        s = preds[offset:offset+g]
        r = y[offset:offset+g]
        offset += g
        # ranking indices
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
    ap.add_argument("--train", default="/mnt/data/processed/features.train.feather")
    ap.add_argument("--val", default="/mnt/data/processed/features.val.feather")
    ap.add_argument("--out_dir", default=f"/mnt/models/recommender/{time.strftime('%Y%m%d_%H%M%S')}")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    train_df = pd.read_feather(args.train)
    val_df = pd.read_feather(args.val)

    feature_cols = [c for c in train_df.columns if c not in ("label","group_id","user_id","plan_id")]

    X_train = train_df[feature_cols].values
    y_train = train_df["label"].astype(int).values
    X_val = val_df[feature_cols].values
    y_val = val_df["label"].astype(int).values

    # group vectors (counts per group_id)
    gtrain = train_df.groupby("group_id").size().to_numpy()
    gval = val_df.groupby("group_id").size().to_numpy()

    dtrain = lgb.Dataset(X_train, label=y_train, group=gtrain, free_raw_data=False)
    dval = lgb.Dataset(X_val, label=y_val, group=gval, reference=dtrain, free_raw_data=False)

    params = {
        "objective": "lambdarank",
        "metric": "ndcg",
        "ndcg_eval_at": [1,3,5],
        "boosting": "gbdt",
        "num_leaves": 128,
        "learning_rate": 0.03,
        "min_data_in_leaf": 20,
        "feature_fraction": 0.7,
        "bagging_fraction": 0.7,
        "bagging_freq": 5,
        "verbosity": 1
    }

    model = lgb.train(
        params,
        dtrain,
        num_boost_round=2000,
        valid_sets=[dtrain, dval],
        valid_names=["train","val"],
        callbacks=[lgb.early_stopping(100, verbose=False)]
    )

    # Save artifacts
    model.save_model(str(out_dir/"model.txt"))
    joblib.dump(feature_cols, str(out_dir/"feature_columns.pkl"))

    # Evaluate NDCG on val
    val_scores = ndcg_eval_at(model, X_val, y_val, gval, ks=(1,3,5))

    meta = {
        "params": params,
        "feature_columns": feature_cols,
        "val_metrics": val_scores,
        "train_rows": int(len(train_df)),
        "val_rows": int(len(val_df)),
    }
    (out_dir/"training_metadata.json").write_text(json.dumps(meta, indent=2))

    print("Saved model to:", out_dir)
    print("Validation:", val_scores)

if __name__ == "__main__":
    main()
