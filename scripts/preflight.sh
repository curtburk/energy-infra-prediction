#!/usr/bin/env bash
# ============================================================================
# Grid Anomaly Prediction — Preflight Check
# ============================================================================
# Run before any demo to verify all services are ready.
# Usage: ./scripts/preflight.sh
# ============================================================================

BACKEND_PORT="${PORT:-8094}"
PASS=0
FAIL=0

check() {
    local name="$1"
    local result="$2"
    if [ "$result" = "ok" ]; then
        echo "  ✓ $name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $name — $result"
        FAIL=$((FAIL + 1))
    fi
}

echo "╔══════════════════════════════════════════════╗"
echo "║   Preflight Check                            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# GPU
if nvidia-smi >/dev/null 2>&1; then
    GPU_NAME=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null)
    GPU_TEMP=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader 2>/dev/null)
    check "GPU: ${GPU_NAME} (${GPU_TEMP}°C)" "ok"
else
    check "GPU" "nvidia-smi not found"
fi

# GPU Memory
if python3 -c "import torch" 2>/dev/null; then
    FREE_GB=$(python3 -c "import torch; print(f'{torch.cuda.mem_get_info()[0]/1e9:.0f}')" 2>/dev/null)
    if [ "${FREE_GB:-0}" -gt 30 ]; then
        check "GPU Memory: ${FREE_GB}GB free" "ok"
    else
        check "GPU Memory: ${FREE_GB}GB free" "need >30GB for Cosmos3-Nano"
    fi
else
    check "GPU Memory" "torch not available"
fi

# vLLM
if curl -s http://localhost:8091/health >/dev/null 2>&1; then
    MODEL=$(curl -s http://localhost:8091/v1/models 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['data'][0]['id'])" 2>/dev/null || echo "unknown")
    check "vLLM: ${MODEL}" "ok"
else
    check "vLLM (port 8091)" "not running — ./scripts/start_cosmos_reason.sh"
fi

# Backend
if curl -s "http://localhost:${BACKEND_PORT}/api/v1/health" >/dev/null 2>&1; then
    HEALTH=$(curl -s "http://localhost:${BACKEND_PORT}/api/v1/health" 2>/dev/null)
    REASON=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['cosmos_reason_loaded'])" 2>/dev/null)
    PREDICT=$(echo "$HEALTH" | python3 -c "import sys,json; print(json.load(sys.stdin)['cosmos_predict_loaded'])" 2>/dev/null)
    MOCK=$([ "$REASON" = "False" ] && echo "MOCK" || echo "REAL")
    check "Backend: ${MOCK} mode (Reason=${REASON}, Predict=${PREDICT})" "ok"
else
    check "Backend (port ${BACKEND_PORT})" "not running — ./scripts/start.sh"
fi

# Frontend
if curl -s http://localhost:5173 >/dev/null 2>&1; then
    check "Frontend (port 5173)" "ok"
else
    check "Frontend (port 5173)" "not running — cd frontend && npm run dev"
fi

# Quick Demo video
if [ -f "frontend/public/demos/demo-morph.mp4" ]; then
    SIZE=$(du -h frontend/public/demos/demo-morph.mp4 | awk '{print $1}')
    check "Quick Demo video: ${SIZE}" "ok"
else
    check "Quick Demo video" "missing — cp data/outputs/analysis-*.mp4 frontend/public/demos/demo-morph.mp4"
fi

# Demo data
if [ -f "frontend/src/data/demo-results.ts" ]; then
    check "Quick Demo data" "ok"
else
    check "Quick Demo data" "missing"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $FAIL -eq 0 ]; then
    echo "  ALL ${PASS} CHECKS PASSED — ready to demo"
else
    echo "  ${PASS} passed, ${FAIL} failed — fix issues above"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
