#!/usr/bin/env python3
"""
Test Cosmos3-Nano video generation integration.

Prerequisites:
  pip install diffusers accelerate torch av imageio imageio-ffmpeg
  Model: nvidia/Cosmos3-Nano (auto-downloaded on first use)

Usage:
    python scripts/test_predict.py
    python scripts/test_predict.py --model nvidia/Cosmos3-Nano
    python scripts/test_predict.py --skip-generate  (just check deps)
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


async def main():
    parser = argparse.ArgumentParser(description="Test Cosmos3 Predict integration")
    parser.add_argument("--model", default=None, help="Model ID (default: nvidia/Cosmos3-Nano)")
    parser.add_argument("--skip-generate", action="store_true", help="Only check deps, skip generation")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info(" Cosmos3-Nano Video Generation Test")
    logger.info("=" * 50)

    # Test 1: Check dependencies
    logger.info("")
    logger.info("--- Checking dependencies ---")
    deps_ok = True
    for pkg in ["torch", "diffusers", "accelerate", "av", "imageio"]:
        try:
            mod = __import__(pkg)
            ver = getattr(mod, "__version__", "?")
            logger.info("  ✓ %s %s", pkg, ver)
        except ImportError:
            logger.error("  ✗ %s not installed", pkg)
            deps_ok = False

    if not deps_ok:
        logger.error("")
        logger.error("Missing dependencies. Install with:")
        logger.error("  pip install diffusers accelerate torch av imageio imageio-ffmpeg")
        sys.exit(1)

    # Test 2: Check CUDA
    import torch
    if torch.cuda.is_available():
        logger.info("  ✓ CUDA available: %s", torch.cuda.get_device_name(0))
        logger.info("    Memory: %.1f GB total", torch.cuda.get_device_properties(0).total_mem / 1e9)
    else:
        logger.error("  ✗ CUDA not available")
        sys.exit(1)

    # Test 3: Initialize service
    from backend.services.cosmos_predict import CosmosPredictService

    service = CosmosPredictService(model_id=args.model) if args.model else CosmosPredictService()
    logger.info("")
    logger.info("Model: %s", service.model_id)

    if not service.check_available():
        sys.exit(1)
    logger.info("  ✓ Dependencies available")

    if args.skip_generate:
        logger.info("")
        logger.info("Skipping generation test (--skip-generate)")
        logger.info("=" * 50)
        return

    # Test 4: Load model
    logger.info("")
    logger.info("--- Loading model (first time downloads ~32GB) ---")
    loaded = await service.load_model()
    if not loaded:
        logger.error("  ✗ Failed to load model")
        sys.exit(1)
    logger.info("  ✓ Model loaded")

    # Test 5: Generate a test video
    logger.info("")
    logger.info("--- Generating test video (this may take 2-5 minutes) ---")
    output_dir = str(PROJECT_ROOT / "data" / "test_cosmos3_output")

    result = await service.predict_future_state(
        input_video="",  # Text-to-video, no input needed
        prompt=(
            "A high-definition surveillance camera view of a power transformer "
            "at an electrical substation. The camera is stationary on a tripod. "
            "There is a visible dark oil stain at the base of the transformer, "
            "spreading outward. Drip marks running down the side. "
            "Clear daylight, industrial setting with safety markings visible."
        ),
        output_dir=output_dir,
        name="test_degradation",
        timeout=600,
    )

    if result:
        size_mb = os.path.getsize(result) / (1024 * 1024)
        logger.info("  ✓ Generated: %s (%.1f MB)", result, size_mb)
    else:
        logger.warning("  ✗ Generation failed — check GPU memory")
        logger.info("    If OOM, try stopping the vLLM container first:")
        logger.info("    docker stop cosmos-reason-vllm")

    # Cleanup
    service.unload_model()

    logger.info("")
    logger.info("=" * 50)
    logger.info(" Test complete")
    logger.info("=" * 50)


if __name__ == "__main__":
    import os
    asyncio.run(main())
