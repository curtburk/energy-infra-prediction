#!/usr/bin/env bash
# ============================================================================
# Grid Infrastructure Anomaly Prediction — Environment Setup
# Target: HP ZGX Nano (ARM64, NVIDIA GB10 Grace Blackwell)
# ============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo " Grid Anomaly Prediction — Setup"
echo "============================================"
echo "Project dir: $PROJECT_DIR"
echo ""

# --- Check GPU ---
echo "[1/7] Checking GPU..."
if command -v nvidia-smi &>/dev/null; then
    nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
    echo "  ✓ GPU detected"
else
    echo "  ⚠ nvidia-smi not found. GPU features will be unavailable."
    echo "    Set MOCK_MODELS=true to run without GPU."
fi
echo ""

# --- Check ffmpeg ---
echo "[2/7] Checking ffmpeg..."
if command -v ffmpeg &>/dev/null; then
    ffmpeg -version | head -1
    echo "  ✓ ffmpeg available"
else
    echo "  ✗ ffmpeg not found. Installing..."
    sudo apt-get update -qq && sudo apt-get install -y -qq ffmpeg
    echo "  ✓ ffmpeg installed"
fi
echo ""

# --- Python virtual environment ---
echo "[3/7] Setting up Python environment..."
VENV_DIR="$PROJECT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  Created virtual environment at $VENV_DIR"
else
    echo "  Virtual environment already exists"
fi
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
echo "  Python: $(python3 --version)"
echo "  ✓ Virtual environment active"
echo ""

# --- Install backend dependencies ---
echo "[4/7] Installing backend dependencies..."
pip install -r "$PROJECT_DIR/backend/requirements.txt" -q
echo "  ✓ Backend dependencies installed"
echo ""

# --- Check Node.js ---
echo "[5/7] Checking Node.js..."
if command -v node &>/dev/null; then
    echo "  Node.js: $(node --version)"
    echo "  npm: $(npm --version)"
    echo "  ✓ Node.js available"
else
    echo "  ✗ Node.js not found."
    echo "    Install Node.js 20 LTS: https://nodejs.org/"
    echo "    Or: curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -"
    echo "    Then: sudo apt-get install -y nodejs"
fi
echo ""

# --- Create data directories ---
echo "[6/7] Creating data directories..."
mkdir -p "$PROJECT_DIR/data/uploads"
mkdir -p "$PROJECT_DIR/data/outputs"
mkdir -p "$PROJECT_DIR/data/frames"
mkdir -p "$PROJECT_DIR/data/models"
echo "  ✓ Data directories created"
echo ""

# --- Verify installation ---
echo "[7/7] Verifying installation..."
python3 -c "import fastapi; print(f'  FastAPI {fastapi.__version__}')"
python3 -c "import uvicorn; print(f'  Uvicorn {uvicorn.__version__}')"
python3 -c "import pydantic; print(f'  Pydantic {pydantic.__version__}')"
echo "  ✓ All core packages verified"
echo ""

echo "============================================"
echo " Setup complete!"
echo ""
echo " To start the backend:"
echo "   cd $PROJECT_DIR && source .venv/bin/activate"
echo "   ./scripts/start.sh"
echo ""
echo " Or manually:"
echo "   uvicorn backend.main:app --host 0.0.0.0 --port 8094 --reload"
echo "============================================"
