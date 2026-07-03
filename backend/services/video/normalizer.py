"""
Resolution normalizer — scales frames to 1920x1080 using Lanczos.
"""

from __future__ import annotations

import logging
from typing import List

import cv2
import numpy as np

from backend.config import settings

logger = logging.getLogger(__name__)


def normalize_frame(
    frame: np.ndarray,
    target_width: int = 1920,
    target_height: int = 1080,
) -> np.ndarray:
    """Resize a single frame to target resolution using Lanczos."""
    h, w = frame.shape[:2]
    if w == target_width and h == target_height:
        return frame
    return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_LANCZOS4)


def normalize_frames(
    frames: List[np.ndarray],
    target_width: int = 1920,
    target_height: int = 1080,
) -> List[np.ndarray]:
    """Normalize a list of frames to target resolution."""
    result = []
    for frame in frames:
        result.append(normalize_frame(frame, target_width, target_height))
    return result
