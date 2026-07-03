"""
H.264 video encoder.

Encodes a sequence of frames to MP4 using ffmpeg subprocess.
Settings per spec §10.6: H.264, CRF 18, yuv420p, faststart.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List

import cv2
import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


def encode_frames_to_video(
    frames: List[np.ndarray],
    output_path: str,
    fps: int = None,
    crf: int = None,
) -> str:
    """
    Encode a list of BGR frames to an H.264 MP4 file.

    Args:
        frames: List of BGR numpy arrays (all same dimensions)
        output_path: Where to save the MP4
        fps: Frame rate (default: settings.OUTPUT_FPS)
        crf: Quality (default: settings.VIDEO_CRF, lower = better)

    Returns:
        Path to the encoded video file
    """
    fps = fps or settings.OUTPUT_FPS
    crf = crf or settings.VIDEO_CRF

    if not frames:
        raise ValueError("No frames to encode")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    height, width = frames[0].shape[:2]

    # Write frames to temporary JPEG directory, then encode with ffmpeg.
    # This avoids piping raw frames through stdin which can be unreliable.
    with tempfile.TemporaryDirectory(prefix="encode_") as tmp_dir:
        # Write frames as JPEG
        for i, frame in enumerate(frames):
            frame_path = os.path.join(tmp_dir, f"frame_{i:05d}.jpg")
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 95])

        # Encode with ffmpeg
        pattern = os.path.join(tmp_dir, "frame_%05d.jpg")
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(fps),
            "-i", pattern,
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", str(crf),
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            output_path,
        ]

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
            )
            if result.returncode != 0:
                logger.error("ffmpeg encoding failed: %s", result.stderr[-500:])
                raise RuntimeError(f"ffmpeg failed: {result.stderr[-200:]}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffmpeg encoding timed out")

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(
        "Encoded %d frames to %s (%.1f MB, %dx%d @ %dfps, CRF %d)",
        len(frames), output_path, file_size, width, height, fps, crf,
    )
    return output_path
