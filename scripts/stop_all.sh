#!/usr/bin/env bash
# ============================================================================
# Grid Anomaly Prediction — Stop All Services
# ============================================================================
set -euo pipefail

echo "Stopping Grid Anomaly Prediction services..."

# Stop frontend
if [ -f /tmp/grid-anomaly-frontend.pid ]; then
    FPID=$(cat /tmp/grid-anomaly-frontend.pid)
    kill "$FPID" 2>/dev/null && echo "  ✓ Frontend stopped (PID $FPID)" || echo "  - Frontend not running"
    rm -f /tmp/grid-anomaly-frontend.pid
fi

# Stop backend
if [ -f /tmp/grid-anomaly-backend.pid ]; then
    BPID=$(cat /tmp/grid-anomaly-backend.pid)
    kill "$BPID" 2>/dev/null && echo "  ✓ Backend stopped (PID $BPID)" || echo "  - Backend not running"
    rm -f /tmp/grid-anomaly-backend.pid
fi

# Clean up any remaining processes on the ports
fuser -k 8094/tcp 2>/dev/null || true
fuser -k 5173/tcp 2>/dev/null || true

# Stop vLLM (optional — leave running if doing multiple demo runs)
read -p "  Stop vLLM container? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop cosmos-reason-vllm 2>/dev/null && echo "  ✓ vLLM stopped" || echo "  - vLLM not running"
fi

echo ""
echo "All services stopped."
