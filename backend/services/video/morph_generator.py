"""
Morph generator — creates smooth transitions between prediction states.

Uses cross-fade interpolation between keyframes (current → +30d → +60d → +90d).
Cross-fade produces cleaner results than optical flow (RIFE) when keyframes
are visually different (degradation changes appearance significantly).

Output: sequence of interpolated frames ready for annotation and encoding.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


def load_keyframe(source: str, target_size: tuple = (1920, 1080)) -> Optional[np.ndarray]:
    """
    Load a keyframe from a video file (first frame) or image file.
    Resize to target dimensions.
    """
    path = Path(source)
    if not path.exists():
        logger.warning("Keyframe source not found: %s", source)
        return None

    if path.suffix.lower() in (".mp4", ".mov", ".avi"):
        cap = cv2.VideoCapture(str(path))
        ret, frame = cap.read()
        cap.release()
        if not ret:
            logger.warning("Cannot read frame from video: %s", source)
            return None
    else:
        frame = cv2.imread(str(source))
        if frame is None:
            logger.warning("Cannot read image: %s", source)
            return None

    # Resize to target
    if frame.shape[1] != target_size[0] or frame.shape[0] != target_size[1]:
        frame = cv2.resize(frame, target_size, interpolation=cv2.INTER_LANCZOS4)

    return frame


def generate_crossfade_segment(
    frame_start: np.ndarray,
    frame_end: np.ndarray,
    num_frames: int,
) -> List[np.ndarray]:
    """
    Generate interpolated frames between two keyframes using cross-fade.

    Returns list of num_frames BGR frames including start and end.
    """
    frames = []
    for i in range(num_frames):
        alpha = i / max(num_frames - 1, 1)
        blended = cv2.addWeighted(
            frame_start, 1.0 - alpha,
            frame_end, alpha,
            0,
        )
        frames.append(blended)
    return frames


def generate_morph_sequence(
    keyframes: List[np.ndarray],
    total_duration_sec: int = None,
    output_fps: int = None,
) -> List[np.ndarray]:
    """
    Generate a complete morph sequence from keyframes.

    Keyframes represent: [current, +30d, +60d, +90d]
    Output: smooth cross-fade between each pair.

    Args:
        keyframes: List of 2-4 BGR frames (numpy arrays)
        total_duration_sec: Total output duration in seconds
        output_fps: Output frame rate

    Returns:
        List of interpolated BGR frames
    """
    total_duration_sec = total_duration_sec or settings.MORPH_DURATION_SEC
    output_fps = output_fps or settings.OUTPUT_FPS

    if len(keyframes) < 2:
        logger.warning("Need at least 2 keyframes for morph, got %d", len(keyframes))
        # Repeat single frame for the full duration
        return [keyframes[0].copy()] * (total_duration_sec * output_fps)

    total_frames = total_duration_sec * output_fps
    segments = len(keyframes) - 1
    frames_per_segment = total_frames // segments

    logger.info(
        "Generating morph: %d keyframes, %d segments, %d frames each, %ds @ %dfps",
        len(keyframes), segments, frames_per_segment,
        total_duration_sec, output_fps,
    )

    all_frames = []
    for i in range(segments):
        segment_frames = generate_crossfade_segment(
            keyframes[i],
            keyframes[i + 1],
            frames_per_segment,
        )
        # Avoid duplicate frames at segment boundaries
        if i > 0 and segment_frames:
            segment_frames = segment_frames[1:]
        all_frames.extend(segment_frames)

    # Pad to exact frame count if needed
    while len(all_frames) < total_frames:
        all_frames.append(all_frames[-1].copy())

    logger.info("Generated %d morph frames", len(all_frames))
    return all_frames


def generate_morph_from_sources(
    current_source: str,
    prediction_sources: List[str],
    total_duration_sec: int = None,
    output_fps: int = None,
    target_size: tuple = (1920, 1080),
) -> List[np.ndarray]:
    """
    Generate morph sequence from video/image file paths.

    Args:
        current_source: Path to current state video/image
        prediction_sources: Paths to +30d, +60d, +90d prediction videos/images
        total_duration_sec: Total output duration
        output_fps: Output frame rate
        target_size: (width, height) for all frames

    Returns:
        List of interpolated BGR frames
    """
    keyframes = []

    # Load current state
    current = load_keyframe(current_source, target_size)
    if current is None:
        raise ValueError(f"Cannot load current state from {current_source}")
    keyframes.append(current)

    # Load prediction states
    for src in prediction_sources:
        frame = load_keyframe(src, target_size)
        if frame is not None:
            keyframes.append(frame)
        else:
            logger.warning("Missing prediction source: %s, duplicating last keyframe", src)
            keyframes.append(keyframes[-1].copy())

    return generate_morph_sequence(keyframes, total_duration_sec, output_fps)
