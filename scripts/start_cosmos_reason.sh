#!/usr/bin/env bash
# ============================================================================
# Start Cosmos-Reason1-7B via vLLM
# ============================================================================
# Serves the model on port 8091 with OpenAI-compatible API.
# Must stop any existing vLLM instance first (one at a time on GB10).
# ============================================================================
set -euo pipefail

MODEL="nvidia/Cosmos-Reason1-7B"
PORT="${VLLM_PORT:-8091}"
CONTAINER_NAME="cosmos-reason-vllm"
VLLM_IMAGE="nvcr.io/nvidia/vllm:26.01-py3"

echo "============================================"
echo " Cosmos-Reason1-7B via vLLM"
echo "============================================"

# --- Preflight: check for existing vLLM instances ---
if docker ps --format '{{.Names}}' | grep -q "vllm"; then
    echo ""
    echo "WARNING: Existing vLLM container(s) detected:"
    docker ps --format '  {{.Names}} ({{.Status}})' | grep vllm
    echo ""
    read -p "Stop existing vLLM containers? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker ps --format '{{.Names}}' | grep vllm | xargs -r docker stop
        echo "  Stopped existing vLLM containers."
    else
        echo "  Aborting. Stop existing vLLM first."
        exit 1
    fi
fi

# --- Check if port is available ---
if ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo "ERROR: Port ${PORT} is already in use."
    echo "  Check: ss -tlnp | grep ${PORT}"
    exit 1
fi

echo ""
echo "Starting ${MODEL} on port ${PORT}..."
echo "  Container: ${CONTAINER_NAME}"
echo "  Image: ${VLLM_IMAGE}"
echo ""

# --- Start vLLM container ---
docker run -d \
    --name "${CONTAINER_NAME}" \
    --gpus all \
    --shm-size=16g \
    -p "${PORT}:8000" \
    -v "${HOME}/.cache/huggingface:/root/.cache/huggingface" \
    -e HUGGING_FACE_HUB_TOKEN="${HUGGING_FACE_HUB_TOKEN:-}" \
    "${VLLM_IMAGE}" \
    python3 -m vllm.entrypoints.openai.api_server \
        --model "${MODEL}" \
        --dtype bfloat16 \
        --max-model-len 8192 \
        --trust-remote-code \
        --host 0.0.0.0 \
        --port 8000

echo ""
echo "Container started. Waiting for model to load..."

# --- Poll for readiness ---
MAX_WAIT=300
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s "http://localhost:${PORT}/health" >/dev/null 2>&1; then
        echo ""
        echo "============================================"
        echo " Cosmos-Reason1-7B is ready!"
        echo ""
        echo " API:     http://localhost:${PORT}/v1"
        echo " Health:  http://localhost:${PORT}/health"
        echo " Models:  http://localhost:${PORT}/v1/models"
        echo ""
        echo " Test:"
        echo "   curl http://localhost:${PORT}/v1/models"
        echo "============================================"
        exit 0
    fi
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    echo "  Waiting... (${ELAPSED}s / ${MAX_WAIT}s)"
done

echo ""
echo "ERROR: vLLM did not become ready within ${MAX_WAIT}s."
echo "  Check logs: docker logs ${CONTAINER_NAME}"
exit 1
