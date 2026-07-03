#!/usr/bin/env bash
# ============================================================================
# Grid Anomaly Prediction — Prepare Demo Data (Phase 1)
# ============================================================================
# Prerequisites:
#   1. Download base footage to data/raw/ (see scripts/data_prep/README.md)
#   2. ffmpeg installed
#   3. Python with Pillow and numpy installed
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo " Phase 1: Data Preparation"
echo "============================================"
echo ""

# Check raw footage exists
RAW_DIR="$PROJECT_DIR/data/raw"
if [ ! -d "$RAW_DIR" ] || [ -z "$(ls -A "$RAW_DIR" 2>/dev/null)" ]; then
    echo "ERROR: No raw footage found in $RAW_DIR"
    echo ""
    echo "Download base footage first:"
    echo "  See scripts/data_prep/README.md for sources and filenames."
    echo ""
    echo "Quick version:"
    echo "  mkdir -p $RAW_DIR"
    echo "  # Download transformer close-up and bushing detail videos from Pexels"
    echo "  # Save as transformer_closeup.mp4 and bushing_detail.mp4"
    exit 1
fi

echo "Found raw footage:"
ls -lh "$RAW_DIR"/*.mp4 2>/dev/null || true
echo ""

# Activate venv if available
if [ -f "$PROJECT_DIR/.venv/bin/activate" ]; then
    source "$PROJECT_DIR/.venv/bin/activate"
fi

# Step 1: Generate textures + composite videos
echo "--- Step 1: Generating anomaly textures and compositing ---"
python3 "$SCRIPT_DIR/data_prep/generate_anomalies.py"
echo ""

# Step 2: Validate outputs
echo "--- Step 2: Validating demo videos ---"
python3 "$SCRIPT_DIR/data_prep/validate.py"
echo ""

# Step 3: Generate thumbnails
echo "--- Step 3: Generating thumbnails ---"
python3 "$SCRIPT_DIR/data_prep/thumbnails.py"
echo ""

echo "============================================"
echo " Phase 1 complete!"
echo ""
echo " Demo videos: $PROJECT_DIR/data/demo_videos/"
echo " Textures:    $PROJECT_DIR/data/textures/"
echo " Thumbnails:  $PROJECT_DIR/frontend/public/demos/"
echo "============================================"
