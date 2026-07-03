"""
Video processing pipeline.

Orchestrates the full video output flow:
  1. Load keyframes (current state + prediction outputs)
  2. Normalize to 1080p
  3. Generate cross-fade morph sequence
  4. Annotate each frame (bounding boxes, labels, TTF, timeline)
  5. Encode to H.264 MP4

This is called by the job orchestrator after model inference completes.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

import cv2
import numpy as np

from backend.config import settings
from backend.services.video.encoder import encode_frames_to_video
from backend.services.video.morph_generator import (
    generate_morph_sequence,
    load_keyframe,
)
from backend.services.video.normalizer import normalize_frame
from backend.services.video.renderer import render_frame

logger = logging.getLogger(__name__)


def build_equipment_annotations(equipment_results: list) -> list:
    """
    Convert EquipmentResult models to annotation dicts for the renderer.
    """
    annotations = []
    for er in equipment_results:
        # Get worst severity from current anomalies
        severities = [a.severity.value for a in er.current_state.anomalies_detected]
        severity_order = {"CRITICAL": 0, "WARNING": 1, "WATCH": 2, "NORMAL": 3}
        worst = min(severities, key=lambda s: severity_order.get(s, 99)) if severities else "NORMAL"

        # Build anomaly annotation list
        anomaly_annots = []
        for a in er.current_state.anomalies_detected:
            annot = {
                "severity": a.severity.value,
                "anomaly_type": a.anomaly_type.value,
            }
            if a.bounding_box:
                annot["bounding_box"] = {
                    "x": a.bounding_box.x,
                    "y": a.bounding_box.y,
                    "width": a.bounding_box.width,
                    "height": a.bounding_box.height,
                }
            anomaly_annots.append(annot)

        annotations.append({
            "type": er.type.value,
            "label": er.label,
            "bounding_box": {
                "x": 120,  # Default position — updated by detection
                "y": 80,
                "width": 340,
                "height": 280,
            },
            "anomalies": anomaly_annots,
            "ttf_days": er.time_to_failure_estimate.days if er.time_to_failure_estimate else None,
            "worst_severity": worst,
        })

    return annotations


def process_video_output(
    current_video_path: str,
    prediction_video_paths: List[Optional[str]],
    equipment_results: list,
    output_path: str,
    total_duration_sec: int = None,
    output_fps: int = None,
) -> str:
    """
    Full video processing pipeline.

    Args:
        current_video_path: Path to the original uploaded video
        prediction_video_paths: Paths to generated +30/60/90d videos (can be None)
        equipment_results: List of EquipmentResult models
        output_path: Where to save the final MP4
        total_duration_sec: Morph duration
        output_fps: Output frame rate

    Returns:
        Path to the encoded output video
    """
    total_duration_sec = total_duration_sec or settings.MORPH_DURATION_SEC
    output_fps = output_fps or settings.OUTPUT_FPS
    target_size = settings.OUTPUT_RESOLUTION

    logger.info("Starting video pipeline: %s → %s", current_video_path, output_path)

    # 1. Load keyframes
    keyframes = []

    current_frame = load_keyframe(current_video_path, target_size)
    if current_frame is None:
        raise ValueError(f"Cannot load current state from {current_video_path}")
    keyframes.append(normalize_frame(current_frame, *target_size))

    for i, pred_path in enumerate(prediction_video_paths):
        if pred_path and os.path.exists(pred_path):
            frame = load_keyframe(pred_path, target_size)
            if frame is not None:
                keyframes.append(normalize_frame(frame, *target_size))
                continue
        # If prediction unavailable, simulate progressive degradation
        logger.info("No prediction video for horizon %d, synthesizing degradation", i + 1)
        prev = keyframes[-1].copy()
        # Each step gets progressively more degraded
        factor = (i + 1) / len(prediction_video_paths)
        hsv = cv2.cvtColor(prev, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * (1.0 + 0.15 * factor), 0, 255)
        hsv[:, :, 2] = np.clip(hsv[:, :, 2] * (1.0 - 0.08 * factor), 0, 255)
        # Add slight warm tint (shift hue toward orange)
        hsv[:, :, 0] = np.clip(hsv[:, :, 0] + 3 * factor, 0, 179)
        degraded = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
        keyframes.append(degraded)

    logger.info("Loaded %d keyframes", len(keyframes))

    # 2. Generate morph sequence
    morph_frames = generate_morph_sequence(keyframes, total_duration_sec, output_fps)
    logger.info("Generated %d morph frames", len(morph_frames))

    # 3. Build annotations
    annotations = build_equipment_annotations(equipment_results)

    # 4. Annotate each frame with current day indicator
    horizons = [0] + settings.PREDICTION_HORIZONS  # [0, 30, 60, 90]
    total_frames = len(morph_frames)
    segments = len(keyframes) - 1
    frames_per_segment = total_frames // max(segments, 1)

    annotated_frames = []
    for i, frame in enumerate(morph_frames):
        # Calculate current prediction day based on frame position
        segment_idx = min(i // max(frames_per_segment, 1), segments - 1)
        segment_progress = (i % frames_per_segment) / max(frames_per_segment, 1)

        if segment_idx < len(horizons) - 1:
            day_start = horizons[segment_idx]
            day_end = horizons[segment_idx + 1]
            current_day = int(day_start + (day_end - day_start) * segment_progress)
        else:
            current_day = horizons[-1]

        annotated = render_frame(frame, annotations, current_day)
        annotated_frames.append(annotated)

    logger.info("Annotated %d frames", len(annotated_frames))

    # 5. Encode to H.264
    output = encode_frames_to_video(annotated_frames, output_path, output_fps)
    logger.info("Video pipeline complete: %s", output)

    return output
