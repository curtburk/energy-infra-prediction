"""
Model Manager — owns lifecycle of Cosmos inference services.

In MOCK mode: uses mock_inference.py (no GPU needed).
In production: Cosmos Reason via vLLM HTTP API, Cosmos Predict via subprocess.
"""

from __future__ import annotations

import logging

from backend.config import settings

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages Cosmos model health and inference dispatch."""

    def __init__(self):
        self.reason_loaded: bool = False
        self.predict_loaded: bool = False
        self._reason_service = None
        self._predict_service = None

    async def load_all(self) -> None:
        """Initialize real inference services."""
        await self.load_reason()
        await self.load_predict()

    async def load_reason(self) -> None:
        """Connect to Cosmos-Reason1-7B via vLLM."""
        from backend.services.cosmos_reason import CosmosReasonService

        logger.info("Connecting to Cosmos-Reason1-7B via vLLM...")
        self._reason_service = CosmosReasonService()
        healthy = await self._reason_service.check_health()
        if healthy:
            self.reason_loaded = True
            logger.info("Cosmos-Reason1-7B is ready via vLLM.")
        else:
            logger.error(
                "Cannot reach Cosmos-Reason1-7B vLLM at %s. "
                "Start it with: ./scripts/start_cosmos_reason.sh",
                self._reason_service.vllm_url,
            )
            raise ConnectionError("vLLM not reachable for Cosmos Reason")

    async def load_predict(self) -> None:
        """Load Cosmos3-Nano for video generation via diffusers."""
        from backend.services.cosmos_predict import CosmosPredictService

        logger.info("Initializing Cosmos3-Nano video generation service...")
        self._predict_service = CosmosPredictService()
        if self._predict_service.check_available():
            # Defer actual model loading until first use to save startup time
            self.predict_loaded = True
            logger.info("Cosmos3-Nano service ready (model loads on first generation).")
        else:
            logger.warning(
                "Cosmos3-Nano dependencies not available. "
                "pip install diffusers accelerate torch av imageio imageio-ffmpeg"
            )
            # Don't raise — Predict is optional, Reason is enough for core demo

    async def unload_all(self) -> None:
        """Clean up services."""
        if self._reason_service:
            await self._reason_service.close()
            self._reason_service = None
        self._predict_service = None
        self.reason_loaded = False
        self.predict_loaded = False
        logger.info("All model services released.")

    @property
    def reason(self):
        return self._reason_service

    @property
    def predict(self):
        return self._predict_service

    def get_vram_available_gb(self) -> int:
        """Estimated available VRAM."""
        # TODO: real GPU query via pynvml
        if self.reason_loaded and self.predict_loaded:
            return 56
        elif self.reason_loaded:
            return 104
        elif self.predict_loaded:
            return 80
        return 128


# Singleton
model_manager = ModelManager()
