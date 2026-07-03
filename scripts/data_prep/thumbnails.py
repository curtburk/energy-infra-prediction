#!/usr/bin/env python3
"""
Generate thumbnails from demo videos for the Quick Demo UI.

Extracts a representative frame from each demo video and saves as JPEG.

Usage:
    python scripts/data_prep/thumbnails.py
"""

import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEMO_DIR = PROJECT_ROOT / "data" / "demo_videos"
THUMB_DIR = PROJECT_ROOT / "frontend" / "public" / "demos"


def generate_thumbnail(video_path: Path, output_path: Path, timestamp: str = "00:00:02"):
    """Extract a single frame as a JPEG thumbnail."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video_path),
         "-ss", timestamp, "-frames:v", "1",
         "-vf", "scale=640:360",
         "-q:v", "2", str(output_path)],
        capture_output=True, check=True, timeout=30,
    )
    logger.info("Thumbnail: %s → %s", video_path.name, output_path)


def main():
    if not DEMO_DIR.exists():
        logger.error("Demo directory not found: %s", DEMO_DIR)
        logger.info("Run generate_anomalies.py first.")
        sys.exit(1)

    videos = sorted(DEMO_DIR.glob("*.mp4"))
    if not videos:
        logger.warning("No demo videos found in %s", DEMO_DIR)
        sys.exit(1)

    for video in videos:
        stem = video.stem  # e.g. "transformer_oil_leak"
        # Save thumbnail alongside demo data
        thumb_dir = THUMB_DIR / stem.replace("_", "-")
        thumb_path = thumb_dir / "thumbnail.jpg"
        generate_thumbnail(video, thumb_path)

    logger.info("Generated %d thumbnail(s)", len(videos))


if __name__ == "__main__":
    main()
