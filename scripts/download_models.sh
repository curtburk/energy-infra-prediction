#!/usr/bin/env bash
# ============================================================================
# Grid Anomaly Prediction — Download Cosmos Models (Phase 2)
# ============================================================================
# Downloads Cosmos-Reason1-7B and Cosmos-Predict2.5-2B from HuggingFace.
# Uses huggingface-cli for resumable downloads with hf_transfer acceleration.
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Enable fast transfers
export HF_HUB_ENABLE_HF_TRANSFER=1

echo "============================================"
echo " Phase 2: Model Downloads"
echo "============================================"
echo ""

# --- Check prerequisites ---
if ! command -v huggingface-cli &>/dev/null; then
    echo "ERROR: huggingface-cli not found."
    echo "  pip install huggingface-hub hf_transfer"
    exit 1
fi

# Check if hf_transfer is available for fast downloads
python3 -c "import hf_transfer" 2>/dev/null && echo "  ✓ hf_transfer enabled (fast mode)" || {
    echo "  ⚠ hf_transfer not installed. Downloads will be slower."
    echo "    pip install hf_transfer"
    export HF_HUB_ENABLE_HF_TRANSFER=0
}

echo ""

# --- Check existing cache ---
echo "Checking HuggingFace cache..."
huggingface-cli scan-cache 2>/dev/null | grep -E "Cosmos|cosmos" || echo "  No Cosmos models in cache."
echo ""

# --- Download Cosmos-Reason1-7B ---
REASON_MODEL="nvidia/Cosmos-Reason1-7B"
echo "--- Downloading ${REASON_MODEL} (~14GB) ---"
echo "  This model handles equipment detection and anomaly classification."
echo ""

huggingface-cli download "${REASON_MODEL}" \
    --resume-download \
    --local-dir-use-symlinks True \
    || {
        echo ""
        echo "ERROR: Failed to download ${REASON_MODEL}"
        echo "  You may need to:"
        echo "    1. Log in: huggingface-cli login"
        echo "    2. Accept the model license at https://huggingface.co/${REASON_MODEL}"
        echo ""
        echo "  Continuing to next model..."
    }

echo ""

# --- Download Cosmos-Predict2.5-2B ---
PREDICT_MODEL="nvidia/Cosmos-Predict2.5-2B"
echo "--- Downloading ${PREDICT_MODEL} (~10GB) ---"
echo "  This model generates future state video predictions."
echo ""

huggingface-cli download "${PREDICT_MODEL}" \
    --resume-download \
    --local-dir-use-symlinks True \
    || {
        echo ""
        echo "ERROR: Failed to download ${PREDICT_MODEL}"
        echo "  You may need to:"
        echo "    1. Log in: huggingface-cli login"
        echo "    2. Accept the model license at https://huggingface.co/${PREDICT_MODEL}"
        echo ""
    }

echo ""

# --- Verify downloads ---
echo "--- Verifying downloads ---"
echo ""
huggingface-cli scan-cache 2>/dev/null | grep -E "Cosmos|cosmos|REPO ID" || echo "  Could not scan cache."
echo ""

echo "============================================"
echo " Download complete."
echo ""
echo " Next steps:"
echo "   1. python3 scripts/test_reason.py   (test Cosmos Reason)"
echo "   2. python3 scripts/test_predict.py  (test Cosmos Predict)"
echo "   3. MOCK_MODELS=false ./scripts/start.sh  (run with real models)"
echo "============================================"
