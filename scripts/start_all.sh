#!/usr/bin/env bash
# ============================================================================
# Grid Anomaly Prediction — Start All Services
# ============================================================================
# Starts everything in the correct order:
#   1. Cosmos-Reason1-7B via vLLM (Docker)
#   2. Backend API (FastAPI)
#   3. Frontend (Vite dev server)
#
# Usage:
#   ./scripts/start_all.sh              # Mock mode (no GPU)
#   ./scripts/start_all.sh --real       # Real models (GPU required)
#   ./scripts/start_all.sh --demo-only  # Quick Demo only (no uploads)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

HOST_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
BACKEND_PORT="${PORT:-8094}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
MODE="mock"

# Parse args
for arg in "$@"; do
    case $arg in
        --real) MODE="real" ;;
        --demo-only) MODE="demo-only" ;;
    esac
done

echo "╔══════════════════════════════════════════════════════╗"
echo "║   Grid Infrastructure Anomaly Prediction             ║"
echo "║   HP ZGX Nano · NVIDIA Cosmos AI                     ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║   Mode: $(printf '%-44s' "$MODE")║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ---- Step 1: Start vLLM (real mode only) ----
if [ "$MODE" = "real" ]; then
    echo "[1/3] Starting Cosmos-Reason1-7B via vLLM..."

    # Check if already running
    if curl -s http://localhost:8091/health >/dev/null 2>&1; then
        echo "  ✓ vLLM already running"
    else
        # Clean up any stopped container
        docker rm -f cosmos-reason-vllm 2>/dev/null || true

        "$SCRIPT_DIR/start_cosmos_reason.sh"
    fi
    echo ""
else
    echo "[1/3] Skipping vLLM (${MODE} mode)"
    echo ""
fi

# ---- Step 2: Start Backend ----
echo "[2/3] Starting backend API..."

# Kill existing backend if running
fuser -k "${BACKEND_PORT}/tcp" 2>/dev/null || true
sleep 1

if [ "$MODE" = "real" ]; then
    export MOCK_MODELS=false
else
    export MOCK_MODELS=true
fi

export HOST="0.0.0.0"
export PORT="$BACKEND_PORT"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Start backend in background
cd "$PROJECT_DIR"
nohup uvicorn backend.main:app \
    --host "$HOST" \
    --port "$PORT" \
    --log-level "${LOG_LEVEL,,}" \
    > /tmp/grid-anomaly-backend.log 2>&1 &

BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
echo "  Log: /tmp/grid-anomaly-backend.log"

# Wait for backend to be ready
echo -n "  Waiting for backend"
for i in $(seq 1 30); do
    if curl -s "http://localhost:${BACKEND_PORT}/api/v1/health" >/dev/null 2>&1; then
        echo ""
        echo "  ✓ Backend ready"
        break
    fi
    echo -n "."
    sleep 2
done
echo ""

# ---- Step 3: Start Frontend ----
echo "[3/3] Starting frontend..."

cd "$PROJECT_DIR/frontend"
if [ ! -d "node_modules" ]; then
    echo "  Installing dependencies..."
    npm install --silent 2>/dev/null
fi

nohup npm run dev -- --host 0.0.0.0 > /tmp/grid-anomaly-frontend.log 2>&1 &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
echo "  Log: /tmp/grid-anomaly-frontend.log"
sleep 3
echo "  ✓ Frontend started"
echo ""

# ---- Summary ----
echo "╔══════════════════════════════════════════════════════╗"
echo "║   All services running                               ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║   Frontend:  http://${HOST_IP}:${FRONTEND_PORT}            ║"
echo "║   API Docs:  http://${HOST_IP}:${BACKEND_PORT}/docs        ║"
echo "║   Health:    http://${HOST_IP}:${BACKEND_PORT}/api/v1/health║"
echo "║                                                      ║"
echo "║   Logs:                                              ║"
echo "║     tail -f /tmp/grid-anomaly-backend.log            ║"
echo "║     tail -f /tmp/grid-anomaly-frontend.log           ║"
echo "║                                                      ║"
echo "║   Stop all:  ./scripts/stop_all.sh                   ║"
echo "╚══════════════════════════════════════════════════════╝"

# Save PIDs for stop script
echo "$BACKEND_PID" > /tmp/grid-anomaly-backend.pid
echo "$FRONTEND_PID" > /tmp/grid-anomaly-frontend.pid
