#!/usr/bin/env python3
"""
Test Cosmos-Reason1-7B integration.

Prerequisites:
  1. vLLM serving Cosmos-Reason1-7B (./scripts/start_cosmos_reason.sh)
  2. Demo videos in data/demo_videos/

Usage:
    python scripts/test_reason.py
    python scripts/test_reason.py --url http://localhost:8091/v1
    python scripts/test_reason.py --frame path/to/frame.jpg
"""

import argparse
import asyncio
import base64
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


async def test_health(url: str) -> bool:
    """Test if vLLM is reachable."""
    import httpx

    health_url = url.replace("/v1", "/health")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                logger.info("✓ vLLM is healthy at %s", health_url)
                return True
    except Exception as e:
        logger.error("✗ Cannot reach vLLM at %s: %s", health_url, e)
    return False


async def test_models_endpoint(url: str) -> bool:
    """Check which model is loaded."""
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{url}/models")
            data = resp.json()
            models = [m["id"] for m in data.get("data", [])]
            logger.info("✓ Loaded models: %s", models)
            return bool(models)
    except Exception as e:
        logger.error("✗ Cannot list models: %s", e)
    return False


async def test_equipment_detection(url: str, frame_path: str) -> bool:
    """Test equipment detection on a frame."""
    os.environ["VLLM_URL"] = url
    from backend.services.cosmos_reason import CosmosReasonService

    service = CosmosReasonService(vllm_url=url)

    try:
        logger.info("Testing equipment detection on %s", frame_path)
        results = await service.detect_equipment([frame_path])
        logger.info("✓ Detected %d equipment items:", len(results))
        for item in results:
            logger.info(
                "  - %s (%s) confidence=%.2f",
                item.get("label", "?"),
                item.get("type", "?"),
                item.get("confidence", 0),
            )
        return bool(results)
    except Exception as e:
        logger.error("✗ Equipment detection failed: %s", e)
        return False
    finally:
        await service.close()


async def test_anomaly_classification(url: str, frame_path: str) -> bool:
    """Test anomaly classification on a frame."""
    os.environ["VLLM_URL"] = url
    from backend.services.cosmos_reason import CosmosReasonService

    service = CosmosReasonService(vllm_url=url)

    try:
        logger.info("Testing anomaly classification on %s", frame_path)
        result = await service.classify_anomalies(
            frame_path=frame_path,
            equipment_type="transformer",
        )
        health = result.get("overall_health_score", "?")
        anomalies = result.get("anomalies_detected", [])
        action = result.get("recommended_action", "?")
        logger.info("✓ Health score: %s, Anomalies: %d", health, len(anomalies))
        for a in anomalies:
            logger.info(
                "  - %s (%s) confidence=%.2f",
                a.get("anomaly_type", "?"),
                a.get("severity", "?"),
                a.get("confidence", 0),
            )
        logger.info("  Action: %s", action)
        return True
    except Exception as e:
        logger.error("✗ Anomaly classification failed: %s", e)
        return False
    finally:
        await service.close()


def extract_test_frame(video_path: str) -> str:
    """Extract a single frame from a video for testing."""
    output = "/tmp/test_frame.jpg"
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-frames:v", "1", "-q:v", "2", output],
        capture_output=True, check=True,
    )
    return output


async def main():
    parser = argparse.ArgumentParser(description="Test Cosmos Reason integration")
    parser.add_argument("--url", default="http://localhost:8091/v1", help="vLLM API URL")
    parser.add_argument("--frame", help="Path to a test frame (JPEG)")
    args = parser.parse_args()

    logger.info("=" * 50)
    logger.info(" Cosmos Reason Integration Test")
    logger.info("=" * 50)
    logger.info("vLLM URL: %s", args.url)
    logger.info("")

    # Test 1: Health check
    if not await test_health(args.url):
        logger.error("vLLM is not reachable. Start it first:")
        logger.error("  ./scripts/start_cosmos_reason.sh")
        sys.exit(1)

    # Test 2: Model listing
    await test_models_endpoint(args.url)

    # Get a test frame
    frame_path = args.frame
    if not frame_path:
        # Try to extract from demo video
        demo_dir = PROJECT_ROOT / "data" / "demo_videos"
        demos = list(demo_dir.glob("*.mp4")) if demo_dir.exists() else []
        if demos:
            logger.info("Extracting test frame from %s", demos[0].name)
            frame_path = extract_test_frame(str(demos[0]))
        else:
            logger.error("No test frame available. Provide --frame or run Phase 1 first.")
            sys.exit(1)

    logger.info("Test frame: %s", frame_path)
    logger.info("")

    # Test 3: Equipment detection
    detect_ok = await test_equipment_detection(args.url, frame_path)

    # Test 4: Anomaly classification
    classify_ok = await test_anomaly_classification(args.url, frame_path)

    logger.info("")
    logger.info("=" * 50)
    if detect_ok and classify_ok:
        logger.info(" ALL TESTS PASSED")
    else:
        logger.error(" SOME TESTS FAILED")
        sys.exit(1)
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
