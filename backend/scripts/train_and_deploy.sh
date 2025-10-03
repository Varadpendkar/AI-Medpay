#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Activate venv
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirement.txt

# Preprocess (optional external paths via env)
PLANS_PATH=${PLANS_PATH:-data/plans.csv}
USERS_PATH=${USERS_PATH:-data/users.csv}
INTER_PATH=${INTER_PATH:-data/interactions.csv}
OUT_DIR=${OUT_DIR:-data/processed}

python3 src/preprocess.py --plans "$PLANS_PATH" --users "$USERS_PATH" --interactions "$INTER_PATH" --out_dir "$OUT_DIR"

# Train ranker (uses default data paths)
python3 src/train_ranker.py

echo "Training complete. Artifacts in models/ and outputs/. Restart app to use the new model."
