#!/usr/bin/env python3
"""
Validate demo videos against spec requirements.

Checks: duration (10-25s), resolution (720p+), codec (H.264/H.265), format.

Usage:
    python scripts/data_prep/validate.py
    python scripts/data_prep/validate.py path/to/specific/video.mp4
"""

import json
import logging
import subprocess
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEMO_DIR = PROJECT_ROOT / "data" / "demo_videos"

REQUIRED = {
    "min_duration": 10,
    "max_duration": 25,
    "min_height": 720,
    "allowed_codecs": {"h264", "hevc", "h265"},
    "allowed_extensions": {".mp4", ".mov", ".avi"},
}


def validate_video(path: Path) -> dict:
    """Validate a single video file. Returns dict with pass/fail and details."""
    result = {"file": path.name, "passed": True, "errors": [], "info": {}}

    if path.suffix.lower() not in REQUIRED["allowed_extensions"]:
        result["passed"] = False
        result["errors"].append(f"Bad extension: {path.suffix}")
        return result

    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", str(path)],
            capture_output=True, text=True, timeout=15,
        )
        info = json.loads(probe.stdout)
    except Exception as e:
        result["passed"] = False
        result["errors"].append(f"ffprobe failed: {e}")
        return result

    vs = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), None)
    if not vs:
        result["passed"] = False
        result["errors"].append("No video stream found")
        return result

    fmt = info.get("format", {})
    duration = float(fmt.get("duration", 0))
    width = int(vs.get("width", 0))
    height = int(vs.get("height", 0))
    codec = vs.get("codec_name", "unknown")
    fps_parts = vs.get("r_frame_rate", "0/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) else 0
    size_mb = int(fmt.get("size", 0)) / (1024 * 1024)

    result["info"] = {
        "duration": round(duration, 1),
        "resolution": f"{width}x{height}",
        "codec": codec,
        "fps": round(fps, 1),
        "size_mb": round(size_mb, 1),
    }

    if duration < REQUIRED["min_duration"]:
        result["passed"] = False
        result["errors"].append(f"Too short: {duration:.1f}s (min {REQUIRED['min_duration']}s)")

    if duration > REQUIRED["max_duration"]:
        result["passed"] = False
        result["errors"].append(f"Too long: {duration:.1f}s (max {REQUIRED['max_duration']}s)")

    if height < REQUIRED["min_height"]:
        result["passed"] = False
        result["errors"].append(f"Resolution too low: {height}p (min {REQUIRED['min_height']}p)")

    if codec not in REQUIRED["allowed_codecs"]:
        result["passed"] = False
        result["errors"].append(f"Unsupported codec: {codec}")

    return result


def main():
    if len(sys.argv) > 1:
        # Validate specific file(s)
        paths = [Path(p) for p in sys.argv[1:]]
    else:
        # Validate all demo videos
        if not DEMO_DIR.exists():
            logger.error("Demo directory not found: %s", DEMO_DIR)
            logger.info("Run generate_anomalies.py first.")
            sys.exit(1)
        paths = sorted(DEMO_DIR.glob("*.mp4"))

    if not paths:
        logger.warning("No video files found to validate.")
        sys.exit(1)

    all_passed = True
    for path in paths:
        result = validate_video(path)
        status = "PASS" if result["passed"] else "FAIL"
        info = result["info"]
        logger.info(
            "[%s] %s — %s, %s, %s, %.1f fps, %.1f MB",
            status, result["file"],
            info.get("resolution", "?"),
            f"{info.get('duration', 0)}s",
            info.get("codec", "?"),
            info.get("fps", 0),
            info.get("size_mb", 0),
        )
        for err in result["errors"]:
            logger.error("       %s", err)
        if not result["passed"]:
            all_passed = False

    if all_passed:
        logger.info("All %d video(s) passed validation.", len(paths))
    else:
        logger.error("Some videos failed validation.")
        sys.exit(1)


if __name__ == "__main__":
    main()
