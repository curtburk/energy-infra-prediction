"""
Cosmos 3 video generation service.

Uses Cosmos3-Nano (16B) via HuggingFace diffusers for generating
future state video predictions showing equipment degradation.

Architecture:
  - Cosmos-Reason1-7B (via vLLM) handles reasoning (detection, classification)
  - Cosmos3-Nano (via diffusers, in-process) handles video generation

Requires:
  pip install diffusers accelerate torch av imageio imageio-ffmpeg
  Model downloaded: nvidia/Cosmos3-Nano
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

from backend.config import settings

logger = logging.getLogger(__name__)

COSMOS3_MODEL_ID = os.getenv("COSMOS3_MODEL", "nvidia/Cosmos3-Nano")


class CosmosPredictService:
    """Generates future state videos using Cosmos3-Nano via diffusers."""

    def __init__(self, model_id: str = None):
        self.model_id = model_id or COSMOS3_MODEL_ID
        self._pipe = None
        self._loaded = False

    def check_available(self) -> bool:
        """Check if diffusers and the model are accessible."""
        try:
            import diffusers  # noqa: F401
            import torch  # noqa: F401
            return True
        except ImportError:
            logger.warning(
                "diffusers or torch not installed. "
                "pip install diffusers accelerate torch av imageio imageio-ffmpeg"
            )
            return False

    async def load_model(self) -> bool:
        """Load Cosmos3-Nano pipeline into GPU memory."""
        if self._loaded:
            return True

        if not self.check_available():
            return False

        logger.info("Loading %s via diffusers (this may take a few minutes)...", self.model_id)

        # Run model loading in a thread to avoid blocking the event loop
        loop = asyncio.get_event_loop()
        try:
            self._pipe = await loop.run_in_executor(None, self._load_pipeline)
            self._loaded = True
            logger.info("%s loaded successfully.", self.model_id)
            return True
        except Exception as e:
            logger.error("Failed to load %s: %s", self.model_id, e)
            return False

    def _load_pipeline(self):
        """Synchronous pipeline loading (runs in thread)."""
        import torch
        from diffusers import Cosmos3OmniPipeline
        from diffusers.schedulers.scheduling_unipc_multistep import UniPCMultistepScheduler

        pipe = Cosmos3OmniPipeline.from_pretrained(
            self.model_id,
            torch_dtype=torch.bfloat16,
            device_map="cuda",
            enable_safety_checker=False,  # Demo environment
        )
        pipe.scheduler = UniPCMultistepScheduler.from_config(
            pipe.scheduler.config, flow_shift=10.0
        )
        return pipe

    def unload_model(self):
        """Release GPU memory."""
        if self._pipe is not None:
            del self._pipe
            self._pipe = None
            self._loaded = False
            import torch
            torch.cuda.empty_cache()
            logger.info("Cosmos3 pipeline unloaded.")

    async def predict_future_state(
        self,
        input_video: str,
        prompt: str,
        output_dir: str,
        name: str = "prediction",
        timeout: int = 600,
    ) -> Optional[str]:
        """
        Generate a future state video.

        Args:
            input_video: Path to input video (used for context, not direct conditioning)
            prompt: Detailed description of the degraded future state
            output_dir: Directory to save output video
            name: Identifier for this prediction
            timeout: Max seconds for generation

        Returns:
            Path to generated video file, or None on failure.
        """
        if not self._loaded:
            loaded = await self.load_model()
            if not loaded:
                return None

        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"{name}.mp4")

        logger.info("Generating future state video: %s", name)
        logger.info("Prompt: %s", prompt[:200])

        loop = asyncio.get_event_loop()
        try:
            result_path = await asyncio.wait_for(
                loop.run_in_executor(
                    None, self._generate_video, prompt, output_path
                ),
                timeout=timeout,
            )
            if result_path and os.path.exists(result_path):
                logger.info("Generated video: %s", result_path)
                return result_path
            return None
        except asyncio.TimeoutError:
            logger.error("Video generation timed out after %ds", timeout)
            return None
        except Exception as e:
            logger.error("Video generation failed: %s", e)
            return None

    def _generate_video(self, prompt: str, output_path: str) -> Optional[str]:
        """Synchronous video generation (runs in thread)."""
        import torch
        from diffusers.utils import export_to_video

        try:
            result = self._pipe(
                prompt=prompt,
                num_frames=49,       # ~2 seconds at 24fps, keeps memory manageable
                height=480,          # Lower res for speed; upscale later if needed
                width=640,
                num_inference_steps=25,  # Balance quality vs speed
                guidance_scale=6.0,
                generator=torch.Generator(device="cuda").manual_seed(42),
            )

            export_to_video(result.video, output_path, fps=24)
            return output_path

        except Exception as e:
            logger.error("Generation error: %s", e)
            return None

    async def generate_degradation_sequence(
        self,
        input_video: str,
        equipment_type: str,
        anomaly_type: str,
        horizons: List[int],
        output_dir: str,
    ) -> List[Optional[str]]:
        """
        Generate future state videos for multiple time horizons.

        Returns list of output video paths (one per horizon).
        """
        results = []
        for days in horizons:
            prompt = self._build_degradation_prompt(
                equipment_type, anomaly_type, days
            )
            name = f"{equipment_type}_{anomaly_type}_{days}d"
            horizon_dir = os.path.join(output_dir, name)

            logger.info(
                "Generating +%d day prediction for %s (%s)",
                days, equipment_type, anomaly_type,
            )

            result = await self.predict_future_state(
                input_video=input_video,
                prompt=prompt,
                output_dir=horizon_dir,
                name=name,
            )
            results.append(result)

        return results

    def _build_degradation_prompt(
        self,
        equipment_type: str,
        anomaly_type: str,
        horizon_days: int,
    ) -> str:
        """Build a detailed prompt for future state generation."""
        prompts = {
            "oil_leak": {
                30: (
                    f"A high-definition surveillance camera view of a power {equipment_type} "
                    f"at an electrical substation. The camera is stationary on a tripod. "
                    f"There is a visible dark oil stain at the base of the {equipment_type}, "
                    f"spreading outward about 6 inches from the base seal. Drip marks are visible "
                    f"running down the side. The stain has a wet, glossy appearance. "
                    f"Clear daylight, industrial setting with safety markings visible."
                ),
                60: (
                    f"A high-definition surveillance camera view of a power {equipment_type} "
                    f"at an electrical substation. The camera is stationary on a tripod. "
                    f"A large dark oil stain covers the base area, with pooling on the ground below. "
                    f"Oil level gauge shows significant depletion. Surface discoloration extends "
                    f"up the sides from heat. Multiple drip paths visible. "
                    f"Clear daylight, industrial setting with safety markings visible."
                ),
                90: (
                    f"A high-definition surveillance camera view of a power {equipment_type} "
                    f"at an electrical substation. The camera is stationary on a tripod. "
                    f"Extensive dark oil staining covers the entire base and ground. "
                    f"Visible thermal discoloration and warping on the {equipment_type} body "
                    f"from overheating due to critical oil loss. Secondary rust forming. "
                    f"Clear daylight, industrial setting with safety markings visible."
                ),
            },
            "contamination": {
                30: (
                    f"A high-definition surveillance camera view of a {equipment_type} bushing "
                    f"at an electrical substation. The camera is stationary. "
                    f"Light brown-gray deposits are visible on the ceramic surface, "
                    f"concentrated on the lower skirts. Early-stage contamination. "
                    f"Clear daylight, industrial setting."
                ),
                60: (
                    f"A high-definition surveillance camera view of a {equipment_type} bushing "
                    f"at an electrical substation. The camera is stationary. "
                    f"Dense contamination deposits cover multiple ceramic skirts. "
                    f"Faint tracking paths visible between skirts. Moderate buildup. "
                    f"Clear daylight, industrial setting."
                ),
                90: (
                    f"A high-definition surveillance camera view of a {equipment_type} bushing "
                    f"at an electrical substation. The camera is stationary. "
                    f"Heavy contamination with thick dark deposits on all skirts. "
                    f"Clear tracking marks and flashover risk indicators visible. "
                    f"Clear daylight, industrial setting."
                ),
            },
        }

        type_prompts = prompts.get(anomaly_type, {})
        if horizon_days in type_prompts:
            return type_prompts[horizon_days]

        return (
            f"A high-definition surveillance camera view of a {equipment_type} "
            f"at an electrical substation showing {anomaly_type.replace('_', ' ')} "
            f"degradation after {horizon_days} days. The damage is clearly visible. "
            f"Stationary camera, clear daylight, industrial setting."
        )
