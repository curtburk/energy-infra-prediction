"""
Application configuration.

All settings can be overridden via environment variables.
"""

import os
from pathlib import Path
from typing import List


class Settings:
    """Application settings with sensible defaults for HP ZGX Nano."""

    # --- Server ---
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8094"))

    # --- Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "data" / "uploads"))
    OUTPUT_DIR: str = os.getenv("OUTPUT_DIR", str(BASE_DIR / "data" / "outputs"))
    FRAMES_DIR: str = os.getenv("FRAMES_DIR", str(BASE_DIR / "data" / "frames"))
    DEMO_DIR: str = os.getenv("DEMO_DIR", str(BASE_DIR / "frontend" / "public" / "demos"))

    # --- Models ---
    MOCK_MODELS: bool = os.getenv("MOCK_MODELS", "true").lower() in ("true", "1", "yes")
    COSMOS_REASON_MODEL: str = os.getenv(
        "COSMOS_REASON_MODEL", "nvidia/Cosmos-Reason1-7B"
    )
    COSMOS_PREDICT_MODEL: str = os.getenv(
        "COSMOS_PREDICT_MODEL", "nvidia/Cosmos-Predict2.5-2B"
    )
    MODEL_DTYPE: str = os.getenv("MODEL_DTYPE", "bfloat16")
    OFFLOAD_GUARDRAIL: bool = os.getenv("OFFLOAD_GUARDRAIL", "true").lower() in (
        "true", "1", "yes"
    )
    OFFLOAD_PROMPT_REFINER: bool = os.getenv(
        "OFFLOAD_PROMPT_REFINER", "true"
    ).lower() in ("true", "1", "yes")
    VLLM_URL: str = os.getenv("VLLM_URL", "http://localhost:8091/v1")
    COSMOS_PREDICT_DIR: str = os.getenv(
        "COSMOS_PREDICT_DIR", os.path.expanduser("~/cosmos-predict2.5")
    )
    COSMOS3_MODEL: str = os.getenv("COSMOS3_MODEL", "nvidia/Cosmos3-Nano")

    # --- Video Processing ---
    INPUT_FPS: int = int(os.getenv("INPUT_FPS", "5"))
    OUTPUT_FPS: int = int(os.getenv("OUTPUT_FPS", "30"))
    OUTPUT_RESOLUTION: tuple = (1920, 1080)
    MIN_DURATION_SEC: int = int(os.getenv("MIN_DURATION_SEC", "10"))
    MAX_DURATION_SEC: int = int(os.getenv("MAX_DURATION_SEC", "25"))
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "500"))
    MORPH_DURATION_SEC: int = int(os.getenv("MORPH_DURATION_SEC", "15"))
    VIDEO_CRF: int = int(os.getenv("VIDEO_CRF", "18"))
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mov", ".avi"]

    # --- Prediction ---
    PREDICTION_HORIZONS: List[int] = [30, 60, 90]

    # --- Job Processing ---
    MAX_CONCURRENT_JOBS: int = int(os.getenv("MAX_CONCURRENT_JOBS", "2"))

    # --- CORS ---
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",   # Vite dev server
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ]

    # --- Logging ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    def __init__(self):
        """Ensure required directories exist."""
        for dir_path in [self.UPLOAD_DIR, self.OUTPUT_DIR, self.FRAMES_DIR]:
            os.makedirs(dir_path, exist_ok=True)

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


settings = Settings()
