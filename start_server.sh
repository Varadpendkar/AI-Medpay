#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$ROOT"
export FLASK_APP=backend.app.main
export FLASK_ENV=development

PORT=5001
HOST=0.0.0.0

echo "🚀 Starting AI-MEDPAY Application"
echo "================================="

# Activate virtual environment if it exists
if [ -d "AImedenv/bin" ]; then
    source AImedenv/bin/activate
    echo "✅ Virtual environment activated"
fi

echo "Starting Flask (dev) on http://${HOST}:${PORT} (PYTHONPATH=$PYTHONPATH)"
# Run in foreground so logs are easy to see (ctrl+c to stop)
python -m flask run --debug --host="$HOST" --port="$PORT" &
FLASK_PID=$!

# give server a few seconds to start
sleep 2

echo -e "\n-- Quick sanity checks --"
echo "Root route headers:"
curl -s -I "http://localhost:${PORT}/" | sed -n '1,10p' || true
echo -e "\nget-quote headers:"
curl -s -I "http://localhost:${PORT}/get-quote" | sed -n '1,10p' || true
echo -e "\nmain.js headers:"
curl -s -I "http://localhost:${PORT}/static/js/main.js" | sed -n '1,10p' || true
echo -e "\nget_quote_enhanced.js headers:"
curl -s -I "http://localhost:${PORT}/backend/app/frontend_routes/static/js/get_quote_enhanced.js" | sed -n '1,10p' || true

echo -e "\n🌐 Your application is available at:"
echo "   • http://localhost:${PORT}"
echo "   • http://127.0.0.1:${PORT}"
echo "   • http://0.0.0.0:${PORT}"
echo ""
echo "🎯 Enhanced Get-Quote form: http://localhost:${PORT}/get-quote"
echo "� Debug endpoints: http://localhost:${PORT}/_dev/endpoints"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "Server PID: $FLASK_PID"
wait $FLASK_PID