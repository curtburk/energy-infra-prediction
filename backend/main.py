"""
Grid Infrastructure Anomaly Prediction Demo
HP ZGX Nano + NVIDIA Cosmos AI

FastAPI application entry point.
"""

import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.config import settings
from backend.api.v1.routes import router as api_router
from backend.store.memory_store import job_store
from backend.services.model_manager import model_manager

logger = logging.getLogger(__name__)

startup_time: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    global startup_time
    startup_time = time.time()
    logger.info("Starting Grid Anomaly Prediction API on %s:%s", settings.HOST, settings.PORT)

    # Load models if not in mock mode
    if not settings.MOCK_MODELS:
        logger.info("Loading Cosmos models (this may take a few minutes)...")
        try:
            await model_manager.load_all()
            logger.info("All models loaded successfully.")
        except Exception as e:
            logger.error("Failed to load models: %s", e)
            logger.warning("Falling back to mock mode.")
            settings.MOCK_MODELS = True
    else:
        logger.info("Running in MOCK mode — no GPU models loaded.")

    yield

    # Shutdown
    logger.info("Shutting down...")
    if not settings.MOCK_MODELS:
        await model_manager.unload_all()
    job_store.clear()
    logger.info("Shutdown complete.")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Grid Infrastructure Anomaly Prediction",
        description=(
            "On-premises AI demo for predicting equipment degradation "
            "in electrical substation infrastructure using NVIDIA Cosmos models "
            "on HP ZGX Nano hardware."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — allow frontend dev server and same-host access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # API routes
    app.include_router(api_router, prefix="/api/v1")

    # Serve output videos as static files
    output_dir = settings.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    app.mount("/outputs", StaticFiles(directory=output_dir), name="outputs")

    return app


app = create_app()


def get_uptime() -> float:
    """Return server uptime in seconds."""
    if startup_time == 0.0:
        return 0.0
    return time.time() - startup_time
