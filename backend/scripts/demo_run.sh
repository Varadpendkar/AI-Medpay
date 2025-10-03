#!/usr/bin/env bash
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "=== demo_run.sh — prepare demo environment ==="

# venv bootstrap
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirement.txt

# copy .env if missing
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "Copied .env.example -> .env (edit if you need custom settings)"
fi

# run migrations
export FLASK_APP=app.py
export FLASK_ENV=development
echo "Running DB migrations..."
flask db upgrade || echo "flask db upgrade failed (no migrations?)"

# seed demo data
echo "Seeding demo data..."
python3 scripts/seed_demo.py

# ensure outputs exists and sample ranking
mkdir -p outputs
if [ ! -f "outputs/sample_ranking.csv" ]; then
  python3 - <<'PY'
import pandas as pd, os
if os.path.exists('data/plans.csv'):
    plans = pd.read_csv('data/plans.csv')
    if 'monthly_premium' in plans.columns:
        sc = 1.0 / plans['monthly_premium'].astype(float).replace(0,1)
    else:
        sc = pd.Series([1.0]*len(plans))
    plans['score'] = sc
    plans = plans.sort_values('score', ascending=False)
    keep = [c for c in ['plan_id','provider','plan_name','monthly_premium','score'] if c in plans.columns]
    plans[keep].to_csv('outputs/sample_ranking.csv', index=False)
    print('Wrote outputs/sample_ranking.csv')
else:
    print('No data/plans.csv; skipped sample ranking')
PY
fi

echo "Demo setup complete.\n"
echo "Start the server with:"
echo "  source .venv/bin/activate"
echo "  export FLASK_APP=app.py"
echo "  export FLASK_ENV=development"
echo "  flask run"
echo
echo "Demo accounts (CSV-based demo):"
echo "  alice / alice@example.com (user_id U0001)"
echo "  bob / bob@example.com (user_id U0002)"
echo "  carol / carol@example.com (user_id U0003)"
echo
echo "Quick smoke test: scripts/e2e_smoke.sh (ensure server running)"
