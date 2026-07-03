"""
Frame extractor — extracts frames at target FPS using ffmpeg.

Phase 4 implementation. Stub for now.
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import List

from backend.config import settings

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: str,
    output_dir: str,
    target_fps: int = None,
) -> List[str]:
    """
    Extract frames from video at target FPS.

    Returns list of frame file paths.
    """
    target_fps = target_fps or settings.INPUT_FPS
    os.makedirs(output_dir, exist_ok=True)

    output_pattern = os.path.join(output_dir, "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", f"fps={target_fps}",
        "-q:v", "2",
        output_pattern,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=60)
    except subprocess.CalledProcessError as e:
        logger.error("Frame extraction failed: %s", e.stderr)
        raise RuntimeError(f"Frame extraction failed: {e.stderr}")

    # Collect output paths
    frames = sorted(
        str(p) for p in Path(output_dir).glob("frame_*.jpg")
    )
    logger.info("Extracted %d frames at %d FPS from %s", len(frames), target_fps, video_path)
    return frames
