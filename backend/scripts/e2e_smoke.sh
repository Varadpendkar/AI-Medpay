#!/usr/bin/env bash
set -e
BASE="http://127.0.0.1:5000"

echo "=== e2e_smoke — quick API smoke tests ==="

check() {
  url=$1
  shift
  echo -n "GET $url ... "
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url")
  echo $status
  if [ "$status" != "200" ]; then
    echo "FAIL: $url returned $status"
    exit 2
  fi
}

# 1) recommendations
check "$BASE/api/recommendations?user_id=U0001&limit=3"

# 2) platform list
check "$BASE/api/platforms"

# 3) platforms plans
check "$BASE/api/platforms/plans?source=internal&limit=2"

# 4) plan detail (pick one from sample)
PLAN=$(curl -s "$BASE/api/platforms/plans?source=internal&limit=1" | python3 -c "import sys, json; d=json.load(sys.stdin); print(d['plans'][0]['plan_id'])")
echo "Found plan id: $PLAN"

check "$BASE/api/plan/$PLAN"

# 5) bill parse (text)
printf '{"text":"X-ray chest 340.00\nConsultation 120.00"}' > /tmp/_e2e_bill.json
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" -d @/tmp/_e2e_bill.json $BASE/api/bill/parse)
echo "POST /api/bill/parse -> $STATUS"
if [ "$STATUS" != "200" ]; then exit 2; fi

# 6) bill analyze
PARSED='[{"line_id":1,"description":"X-ray chest","amount":340.0},{"line_id":2,"description":"Consultation","amount":120.0}]'
printf '{"user_id":"U0001","parsed_items":%s}' "$PARSED" > /tmp/_e2e_analyze.json
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H "Content-Type: application/json" -d @/tmp/_e2e_analyze.json $BASE/api/bill/analyze)
echo "POST /api/bill/analyze -> $STATUS"
if [ "$STATUS" != "200" ]; then exit 2; fi

echo "All smoke tests passed."
