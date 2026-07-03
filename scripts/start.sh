#!/usr/bin/env bash
# ============================================================================
# Grid Infrastructure Anomaly Prediction — Start Services
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Detect host IP for clickable URLs
HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
PORT="${PORT:-8094}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

# Activate venv if available
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

echo "============================================"
echo " Grid Anomaly Prediction — Starting"
echo "============================================"
echo ""
echo " Mode: ${MOCK_MODELS:-true}"
echo ""
echo " Backend API:  http://${HOST_IP}:${PORT}"
echo " API Docs:     http://${HOST_IP}:${PORT}/docs"
echo " Health Check: http://${HOST_IP}:${PORT}/api/v1/health"
echo ""
echo " Frontend:     http://${HOST_IP}:${FRONTEND_PORT}"
echo ""
echo "============================================"
echo ""

cd "$PROJECT_DIR"

export MOCK_MODELS="${MOCK_MODELS:-true}"
export HOST="0.0.0.0"
export PORT="$PORT"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

exec uvicorn backend.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "${LOG_LEVEL,,}" \
    --reload
