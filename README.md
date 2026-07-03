# Grid Infrastructure Anomaly Prediction Demo

**On-premises AI for predicting equipment degradation in electrical substation infrastructure.**

Uses NVIDIA Cosmos AI models on HP ZGX Nano hardware to detect anomalies, predict future equipment states (+30/60/90 days), and generate animated degradation visualizations — all without cloud dependencies.

**Target audience:** US Department of Energy / Sandia National Laboratories

---

## Architecture

```
Upload Video → Cosmos Reason (detect equipment)
                    ↓
             User confirms equipment
                    ↓
             Cosmos Predict (generate +30/60/90 day futures)
                    ↓
             Cosmos Reason (classify anomalies per timeframe)
                    ↓
             RIFE morph interpolation → Annotated output video
```

**Backend:** FastAPI (Python) with async job orchestration  
**Frontend:** React + TypeScript + Tailwind CSS (dark mode)  
**Models:** Cosmos-Reason1-7B (VLM) + Cosmos-Predict2.5-2B (video diffusion)  
**Hardware:** HP ZGX Nano — NVIDIA GB10 Grace Blackwell, ARM64, 128GB unified memory

---

## Prerequisites

| Component       | Version    | Notes                          |
|-----------------|------------|--------------------------------|
| Python          | 3.11+      | System or pyenv                |
| Node.js         | 20 LTS     | For frontend build             |
| ffmpeg          | 5.x+       | H.264/H.265 codec support     |
| NVIDIA Driver   | 560+       | For GB10 Blackwell             |
| CUDA            | 13.0       | Bundled with driver             |
| Docker          | 24+        | Optional, for containerized deploy |
| nvidia-container-toolkit | Latest | Optional, for GPU in Docker |

---

## Quick Start

### 1. Clone and setup

```bash
git clone <repo-url> grid-anomaly-prediction
cd grid-anomaly-prediction
chmod +x scripts/*.sh
./scripts/setup.sh
```

### 2. Start backend (mock mode — no GPU required)

```bash
./scripts/start.sh
```

This starts the API at `http://<host-ip>:8094` with mock inference enabled.  
API docs available at `http://<host-ip>:8094/docs`.

### 3. Start frontend (separate terminal)

```bash
cd frontend
npm install
npm run dev
```

Frontend at `http://localhost:5173`.

### 4. Run with real models (on HP ZGX Nano)

```bash
MOCK_MODELS=false ./scripts/start.sh
```

Requires Cosmos models downloaded to `data/models/`.

---

## Environment Variables

| Variable                | Default | Description                              |
|-------------------------|---------|------------------------------------------|
| `MOCK_MODELS`           | `true`  | Use mock inference (no GPU needed)       |
| `HOST`                  | `0.0.0.0` | Server bind address                   |
| `PORT`                  | `8000`  | Server port                              |
| `LOG_LEVEL`             | `INFO`  | Logging level                            |
| `MAX_CONCURRENT_JOBS`   | `2`     | Max simultaneous processing jobs         |
| `UPLOAD_DIR`            | `data/uploads` | Video upload storage              |
| `OUTPUT_DIR`            | `data/outputs` | Rendered video output             |
| `COSMOS_REASON_MODEL`   | `nvidia/Cosmos-Reason1-7B` | HuggingFace model ID   |
| `COSMOS_PREDICT_MODEL`  | `nvidia/Cosmos-Predict2.5-2B` | HuggingFace model ID |
| `OFFLOAD_GUARDRAIL`     | `true`  | Offload guardrail model to save VRAM    |
| `OFFLOAD_PROMPT_REFINER` | `true` | Offload prompt refiner to save VRAM     |

---

## API Endpoints

| Endpoint                          | Method | Purpose                         |
|-----------------------------------|--------|---------------------------------|
| `/api/v1/upload`                  | POST   | Upload video for analysis       |
| `/api/v1/jobs/{id}/status`        | GET    | Poll job status and progress    |
| `/api/v1/jobs/{id}/equipment`     | GET    | Get detected equipment list     |
| `/api/v1/jobs/{id}/confirm`       | POST   | Confirm equipment, start analysis |
| `/api/v1/jobs/{id}/results`       | GET    | Get final analysis results      |
| `/api/v1/jobs/{id}/video`         | GET    | Download annotated morph video  |
| `/api/v1/jobs/{id}`               | DELETE | Cancel job                      |
| `/api/v1/health`                  | GET    | Service health check            |

---

## Project Structure

```
grid-anomaly-prediction/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── config.py               # Configuration
│   ├── models/                 # Data models (Job, Equipment, Anomaly)
│   ├── api/v1/                 # Routes and schemas
│   ├── services/               # Business logic
│   │   ├── orchestrator.py     # Async job management
│   │   ├── model_manager.py    # Cosmos model lifecycle
│   │   ├── mock_inference.py   # Mock results for dev/testing
│   │   └── video/              # Video processing pipeline
│   └── store/                  # In-memory job storage
├── frontend/                   # React SPA (Phase 5)
├── scripts/
│   ├── setup.sh                # Environment setup
│   └── start.sh                # Start services
├── tasks/
│   ├── todo.md                 # Implementation tracking
│   └── lessons.md              # Learnings and gotchas
├── data/                       # Runtime data (gitignored)
│   ├── uploads/
│   ├── outputs/
│   ├── frames/
│   └── models/
├── docs/
│   ├── BACKEND_SPEC.md
│   └── IMPLEMENTATION_PLAN.md
└── docker-compose.yml
```

---

## Hardware Verification (HP ZGX Nano)

After setup, verify:

```bash
# GPU detected with 128GB memory
nvidia-smi

# CUDA version
nvcc --version

# Architecture (should be aarch64)
uname -m

# ffmpeg codecs
ffmpeg -codecs 2>/dev/null | grep -E "h264|h265"
```

Expected output from `nvidia-smi`:
- GPU: NVIDIA GB10 Grace Blackwell
- Memory: ~128GB
- Driver: 560+

---

## Docker Deployment

```bash
docker-compose up --build -d
```

Backend: `http://localhost:8094`  
Frontend: `http://localhost:5173`

To run with GPU:
```bash
docker-compose --profile gpu up --build -d
```

---

## Development

```bash
# Run backend tests
cd backend && pytest -v

# Run with auto-reload
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Check API health
curl http://localhost:8094/api/v1/health | python3 -m json.tool
```

---

## Key Design Decisions

- **Mock mode by default** — Full API works without GPU for frontend/integration dev
- **In-memory storage** — Data clears on restart; appropriate for demo use
- **Async processing** — Jobs run as asyncio background tasks, polled via status endpoint
- **Modular monolith** — Single FastAPI process for demo simplicity
- **Sequential user flow** — Upload → Detect → Confirm → Analyze → Results gives presenter natural pause points

---

## Spec Documents

- [Backend Technical Specification](docs/BACKEND_SPEC.md)
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md)
