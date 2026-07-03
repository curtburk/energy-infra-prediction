"""
Annotation renderer for output video frames.

Draws:
  - Equipment bounding boxes (color-coded by type)
  - Equipment labels
  - Anomaly bounding boxes (color-coded by severity)
  - TTF badges (pill-shaped, severity-colored)
  - Timeline indicator (top-right, showing current prediction day)

Minimal style per spec §10.5.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Color palettes (BGR for OpenCV)
# ---------------------------------------------------------------------------

EQUIPMENT_COLORS = {
    "transformer": (0xF6, 0x82, 0x3B),     # Blue #3B82F6
    "bushing": (0xF6, 0x5C, 0x8B),          # Purple #8B5CF6
    "insulator": (0xD4, 0xB6, 0x06),        # Cyan #06B6D4
    "circuit_breaker": (0x0B, 0x9E, 0xF5),  # Amber #F59E0B
    "other": (0x80, 0x72, 0x6B),            # Gray #6B7280
}

SEVERITY_COLORS = {
    "CRITICAL": (0x44, 0x44, 0xEF),   # Red #EF4444
    "WARNING": (0x0B, 0x9E, 0xF5),    # Amber #F59E0B
    "WATCH": (0xF6, 0x82, 0x3B),      # Blue #3B82F6
    "NORMAL": (0x5E, 0xC5, 0x22),     # Green #22C55E
}

# Font settings
FONT = cv2.FONT_HERSHEY_SIMPLEX
FONT_SCALE_LABEL = 0.5
FONT_SCALE_BADGE = 0.45
FONT_SCALE_TIMELINE = 0.7
FONT_THICKNESS = 1
LINE_TYPE = cv2.LINE_AA


def _get_equipment_color(eq_type: str) -> Tuple[int, int, int]:
    return EQUIPMENT_COLORS.get(eq_type, EQUIPMENT_COLORS["other"])


def _get_severity_color(severity: str) -> Tuple[int, int, int]:
    return SEVERITY_COLORS.get(severity, SEVERITY_COLORS["NORMAL"])


def draw_equipment_bbox(
    frame: np.ndarray,
    x: int, y: int, w: int, h: int,
    eq_type: str,
    label: str,
) -> np.ndarray:
    """Draw equipment bounding box with label."""
    color = _get_equipment_color(eq_type)

    # Bounding box — 2px
    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2, LINE_TYPE)

    # Label background
    text_size = cv2.getTextSize(label, FONT, FONT_SCALE_LABEL, FONT_THICKNESS)[0]
    label_bg_x2 = x + text_size[0] + 8
    label_bg_y2 = y - 2
    label_bg_y1 = y - text_size[1] - 10
    cv2.rectangle(frame, (x, label_bg_y1), (label_bg_x2, label_bg_y2), color, -1, LINE_TYPE)

    # Label text — white on colored background
    cv2.putText(
        frame, label,
        (x + 4, y - 6),
        FONT, FONT_SCALE_LABEL, (255, 255, 255), FONT_THICKNESS, LINE_TYPE,
    )

    return frame


def draw_anomaly_bbox(
    frame: np.ndarray,
    x: int, y: int, w: int, h: int,
    severity: str,
    anomaly_type: str,
) -> np.ndarray:
    """Draw anomaly bounding box with severity color."""
    color = _get_severity_color(severity)

    if severity in ("CRITICAL", "WARNING"):
        # Solid line for high severity
        cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2, LINE_TYPE)
    else:
        # Dashed effect for lower severity (draw corners only)
        dash_len = min(w, h) // 4
        # Top-left
        cv2.line(frame, (x, y), (x + dash_len, y), color, 2, LINE_TYPE)
        cv2.line(frame, (x, y), (x, y + dash_len), color, 2, LINE_TYPE)
        # Top-right
        cv2.line(frame, (x + w, y), (x + w - dash_len, y), color, 2, LINE_TYPE)
        cv2.line(frame, (x + w, y), (x + w, y + dash_len), color, 2, LINE_TYPE)
        # Bottom-left
        cv2.line(frame, (x, y + h), (x + dash_len, y + h), color, 2, LINE_TYPE)
        cv2.line(frame, (x, y + h), (x, y + h - dash_len), color, 2, LINE_TYPE)
        # Bottom-right
        cv2.line(frame, (x + w, y + h), (x + w - dash_len, y + h), color, 2, LINE_TYPE)
        cv2.line(frame, (x + w, y + h), (x + w, y + h - dash_len), color, 2, LINE_TYPE)

    return frame


def draw_ttf_badge(
    frame: np.ndarray,
    x: int, y: int, w: int, h: int,
    ttf_days: int,
    severity: str,
) -> np.ndarray:
    """Draw TTF pill badge at bottom-right of equipment bounding box."""
    color = _get_severity_color(severity)
    text = f"TTF: {ttf_days}d"

    text_size = cv2.getTextSize(text, FONT, FONT_SCALE_BADGE, FONT_THICKNESS)[0]
    badge_w = text_size[0] + 12
    badge_h = text_size[1] + 8

    # Position: bottom-right of bounding box
    bx = x + w - badge_w - 4
    by = y + h - badge_h - 4

    # Background with rounded corners (approximate with filled rectangle)
    overlay = frame.copy()
    cv2.rectangle(overlay, (bx, by), (bx + badge_w, by + badge_h), color, -1, LINE_TYPE)
    # Semi-transparent (90% opacity)
    cv2.addWeighted(overlay, 0.9, frame, 0.1, 0, frame)

    # Text
    cv2.putText(
        frame, text,
        (bx + 6, by + badge_h - 4),
        FONT, FONT_SCALE_BADGE, (255, 255, 255), FONT_THICKNESS, LINE_TYPE,
    )

    return frame


def draw_timeline_indicator(
    frame: np.ndarray,
    current_day: int,
) -> np.ndarray:
    """Draw timeline indicator in top-right corner."""
    h, w = frame.shape[:2]

    if current_day == 0:
        text = "Current State"
    else:
        text = f"Day +{current_day}"

    text_size = cv2.getTextSize(text, FONT, FONT_SCALE_TIMELINE, 2)[0]
    tx = w - text_size[0] - 20
    ty = 35

    # Semi-transparent background
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (tx - 10, ty - text_size[1] - 8),
        (tx + text_size[0] + 10, ty + 8),
        (0, 0, 0), -1, LINE_TYPE,
    )
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Text
    cv2.putText(
        frame, text,
        (tx, ty),
        FONT, FONT_SCALE_TIMELINE, (255, 255, 255), 2, LINE_TYPE,
    )

    return frame


def render_frame(
    frame: np.ndarray,
    equipment_list: list,
    current_day: int,
) -> np.ndarray:
    """
    Composite all annotations onto a single frame.

    Args:
        frame: BGR image (numpy array)
        equipment_list: list of dicts with keys:
            - type, label, bounding_box {x,y,width,height}
            - anomalies: list of {severity, anomaly_type, bounding_box}
            - ttf_days: int or None
            - worst_severity: str
        current_day: 0, 30, 60, or 90
    """
    annotated = frame.copy()

    for eq in equipment_list:
        bbox = eq.get("bounding_box", {})
        x = bbox.get("x", 0)
        y = bbox.get("y", 0)
        w = bbox.get("width", 100)
        h = bbox.get("height", 100)

        # Equipment bounding box + label
        draw_equipment_bbox(
            annotated, x, y, w, h,
            eq.get("type", "other"),
            eq.get("label", "Equipment"),
        )

        # Anomaly bounding boxes
        for anomaly in eq.get("anomalies", []):
            abbox = anomaly.get("bounding_box")
            if abbox:
                draw_anomaly_bbox(
                    annotated,
                    abbox.get("x", x), abbox.get("y", y),
                    abbox.get("width", 40), abbox.get("height", 30),
                    anomaly.get("severity", "NORMAL"),
                    anomaly.get("anomaly_type", ""),
                )

        # TTF badge
        ttf = eq.get("ttf_days")
        if ttf is not None:
            draw_ttf_badge(
                annotated, x, y, w, h,
                ttf,
                eq.get("worst_severity", "WARNING"),
            )

    # Timeline indicator
    draw_timeline_indicator(annotated, current_day)

    return annotated
