# ============================================================================
# Grid Infrastructure Anomaly Prediction — Backend Dockerfile
# Target: HP ZGX Nano (ARM64, NVIDIA GB10 Grace Blackwell)
# ============================================================================
# Build for ARM64 explicitly
FROM --platform=linux/arm64 python:3.11-slim AS base

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Application code
COPY backend/ /app/backend/

# Data directories
RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/frames /app/data/models

# Environment defaults
ENV HOST=0.0.0.0
ENV PORT=8094
ENV MOCK_MODELS=true
ENV LOG_LEVEL=INFO
ENV UPLOAD_DIR=/app/data/uploads
ENV OUTPUT_DIR=/app/data/outputs
ENV FRAMES_DIR=/app/data/frames

EXPOSE 8094

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8094"]

# ============================================================================
# GPU variant — uncomment Phase 2 deps in requirements.txt before building
# ============================================================================
FROM base AS gpu

ENV MOCK_MODELS=false
# Models mount point — map host model cache to avoid re-downloading
VOLUME ["/app/data/models"]

# NVIDIA runtime requirement
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
