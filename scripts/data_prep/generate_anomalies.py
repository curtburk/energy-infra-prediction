#!/usr/bin/env python3
"""
Procedural anomaly texture generator and video compositor.

Generates realistic-looking anomaly overlays (oil leaks, corrosion, thermal
hotspots, bushing contamination) and composites them onto base substation
footage to create demo input videos.

Usage:
    python scripts/data_prep/generate_anomalies.py

Reads from:  data/raw/*.mp4
Writes to:   data/demo_videos/*.mp4
             data/textures/*.png  (intermediate anomaly textures)
"""

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Resolve project root
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
TEXTURE_DIR = PROJECT_ROOT / "data" / "textures"
DEMO_DIR = PROJECT_ROOT / "data" / "demo_videos"
FRAMES_DIR = PROJECT_ROOT / "data" / "composite_frames"


# ---------------------------------------------------------------------------
# Anomaly texture generators
# ---------------------------------------------------------------------------

def _noise_layer(width: int, height: int, scale: float = 0.05) -> np.ndarray:
    """Generate a smooth noise pattern using random + gaussian blur."""
    noise = np.random.rand(height, width).astype(np.float32)
    img = Image.fromarray((noise * 255).astype(np.uint8), mode="L")
    img = img.filter(ImageFilter.GaussianBlur(radius=max(width, height) * scale))
    return np.array(img).astype(np.float32) / 255.0


def generate_oil_leak(
    width: int = 400,
    height: int = 300,
    severity: int = 1,
) -> Image.Image:
    """
    Generate oil leak texture with alpha channel.

    severity: 1=subtle, 2=moderate, 3=severe
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Base stain — dark ellipses with soft edges
    cx, cy = width // 2, height // 2
    stain_sizes = {
        1: [(0.3, 0.2)],
        2: [(0.4, 0.3), (0.25, 0.15)],
        3: [(0.5, 0.4), (0.35, 0.25), (0.2, 0.15)],
    }

    for i, (sw, sh) in enumerate(stain_sizes.get(severity, [(0.3, 0.2)])):
        rx = int(width * sw)
        ry = int(height * sh)
        offset_x = int(width * 0.1 * i)
        offset_y = int(height * 0.08 * i)
        draw.ellipse(
            [cx - rx + offset_x, cy - ry + offset_y,
             cx + rx + offset_x, cy + ry + offset_y],
            fill=(20, 15, 10, int(120 + severity * 30)),
        )

    # Drip lines for severity >= 2
    if severity >= 2:
        for dx in range(-2, 3):
            drip_x = cx + dx * 15
            drip_len = int(height * (0.2 + severity * 0.1))
            draw.line(
                [(drip_x, cy + int(height * 0.15)),
                 (drip_x + 5, cy + int(height * 0.15) + drip_len)],
                fill=(15, 10, 8, int(80 + severity * 25)),
                width=3 + severity,
            )

    # Soften edges
    img = img.filter(ImageFilter.GaussianBlur(radius=8 + severity * 3))

    # Add noise for realism
    noise = _noise_layer(width, height, scale=0.03)
    arr = np.array(img).astype(np.float32)
    arr[:, :, 3] *= noise  # modulate alpha with noise
    img = Image.fromarray(arr.astype(np.uint8))

    return img


def generate_corrosion(
    width: int = 300,
    height: int = 200,
    severity: int = 1,
) -> Image.Image:
    """
    Generate rust/corrosion texture with alpha channel.

    severity: 1=surface rust, 2=moderate oxidation, 3=heavy flaking
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Rust colors: orange-brown palette
    rust_colors = [
        (139, 69, 19),   # saddle brown
        (178, 102, 34),  # rust orange
        (160, 82, 45),   # sienna
        (205, 133, 63),  # peru
        (210, 105, 30),  # chocolate
    ]

    # Generate noise-based rust patches
    noise1 = _noise_layer(width, height, scale=0.04)
    noise2 = _noise_layer(width, height, scale=0.08)

    arr = np.zeros((height, width, 4), dtype=np.float32)

    # Threshold noise to create patches
    threshold = {1: 0.48, 2: 0.43, 3: 0.35}[severity]
    mask = noise1 > threshold

    for y in range(height):
        for x in range(width):
            if mask[y, x]:
                color_idx = int(noise2[y, x] * (len(rust_colors) - 1))
                r, g, b = rust_colors[color_idx]
                alpha = int((noise1[y, x] - threshold) / (1 - threshold) * (150 + severity * 30))
                arr[y, x] = [r, g, b, min(alpha, 255)]

    img = Image.fromarray(arr.astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=2 + severity))

    return img


def generate_thermal_hotspot(
    width: int = 200,
    height: int = 200,
    severity: int = 1,
) -> Image.Image:
    """
    Generate thermal discoloration gradient with alpha channel.

    severity: 1=warm spot, 2=hot zone, 3=critical heat
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    cx, cy = width // 2, height // 2
    max_radius = min(width, height) // 2

    # Color gradient: center=hot, edge=warm
    colors_by_severity = {
        1: [(255, 200, 50), (200, 150, 30)],     # warm yellow
        2: [(255, 140, 0), (255, 200, 50)],       # orange to yellow
        3: [(255, 50, 50), (255, 140, 0)],        # red to orange
    }

    center_color, edge_color = colors_by_severity[severity]
    arr = np.zeros((height, width, 4), dtype=np.float32)

    for y in range(height):
        for x in range(width):
            dist = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_radius
            if dist <= 1.0:
                t = dist  # 0 at center, 1 at edge
                r = center_color[0] * (1 - t) + edge_color[0] * t
                g = center_color[1] * (1 - t) + edge_color[1] * t
                b = center_color[2] * (1 - t) + edge_color[2] * t
                alpha = (1 - dist) * (80 + severity * 30)
                arr[y, x] = [r, g, b, min(alpha, 255)]

    img = Image.fromarray(arr.astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=5 + severity * 2))

    return img


def generate_contamination(
    width: int = 250,
    height: int = 150,
    severity: int = 1,
) -> Image.Image:
    """
    Generate bushing surface contamination/deposit texture.

    severity: 1=light deposits, 2=moderate buildup, 3=heavy contamination
    """
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))

    # Brownish-gray deposit colors
    noise = _noise_layer(width, height, scale=0.05)
    arr = np.zeros((height, width, 4), dtype=np.float32)

    threshold = {1: 0.48, 2: 0.42, 3: 0.30}[severity]

    for y in range(height):
        for x in range(width):
            if noise[y, x] > threshold:
                intensity = (noise[y, x] - threshold) / (1 - threshold)
                # Gray-brown deposit color
                r = 100 + int(30 * intensity)
                g = 85 + int(20 * intensity)
                b = 70 + int(15 * intensity)
                alpha = int(intensity * (100 + severity * 35))
                arr[y, x] = [r, g, b, min(alpha, 255)]

    img = Image.fromarray(arr.astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(radius=3 + severity))

    return img


# ---------------------------------------------------------------------------
# Texture library generation (Tasks 1.3–1.6)
# ---------------------------------------------------------------------------

TEXTURE_SPECS = {
    "oil_leak": {"fn": generate_oil_leak, "sizes": [(400, 300), (300, 200), (250, 180)]},
    "corrosion": {"fn": generate_corrosion, "sizes": [(300, 200), (250, 180), (200, 150)]},
    "thermal_hotspot": {"fn": generate_thermal_hotspot, "sizes": [(200, 200), (160, 160), (120, 120)]},
    "contamination": {"fn": generate_contamination, "sizes": [(250, 150), (200, 120), (180, 100)]},
}


def generate_texture_library():
    """Generate all anomaly textures at 3 severity levels (Tasks 1.3–1.6)."""
    TEXTURE_DIR.mkdir(parents=True, exist_ok=True)

    for anomaly_type, spec in TEXTURE_SPECS.items():
        for severity in (1, 2, 3):
            w, h = spec["sizes"][severity - 1]
            texture = spec["fn"](width=w, height=h, severity=severity)
            filename = f"{anomaly_type}_s{severity}.png"
            path = TEXTURE_DIR / filename
            texture.save(str(path))
            logger.info("Generated %s (%dx%d)", filename, w, h)

    logger.info("Texture library saved to %s", TEXTURE_DIR)


# ---------------------------------------------------------------------------
# Video compositing (Tasks 1.7–1.8)
# ---------------------------------------------------------------------------

def _get_video_info(video_path: str) -> dict:
    """Get video metadata via ffprobe."""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", video_path],
        capture_output=True, text=True, timeout=15,
    )
    info = json.loads(result.stdout)
    vs = next((s for s in info.get("streams", []) if s["codec_type"] == "video"), {})
    return {
        "width": int(vs.get("width", 1920)),
        "height": int(vs.get("height", 1080)),
        "duration": float(info.get("format", {}).get("duration", 15)),
    }


def _extract_frames(video_path: str, output_dir: str, fps: int = 5) -> list:
    """Extract frames from video at target FPS."""
    os.makedirs(output_dir, exist_ok=True)
    pattern = os.path.join(output_dir, "frame_%04d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-i", video_path, "-vf", f"fps={fps}", "-q:v", "2", pattern],
        capture_output=True, check=True, timeout=120,
    )
    return sorted(str(p) for p in Path(output_dir).glob("frame_*.jpg"))


def _encode_video(frames_dir: str, output_path: str, fps: int = 5):
    """Encode frames back to H.264 MP4."""
    pattern = os.path.join(frames_dir, "frame_%04d.jpg")
    subprocess.run(
        ["ffmpeg", "-y", "-framerate", str(fps), "-i", pattern,
         "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-movflags", "+faststart",
         "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2",
         output_path],
        capture_output=True, check=True, timeout=120,
    )


def composite_anomaly_on_video(
    video_path: str,
    output_path: str,
    anomaly_type: str,
    severity: int,
    position: tuple = None,
    name: str = "demo",
):
    """
    Composite an anomaly texture onto every frame of a video.

    Args:
        video_path: Path to base video
        output_path: Where to save composited video
        anomaly_type: One of oil_leak, corrosion, thermal_hotspot, contamination
        severity: 1-3
        position: (x, y) pixel position for overlay center. If None, auto-placed.
        name: Identifier for temp directory
    """
    # Load texture
    texture_path = TEXTURE_DIR / f"{anomaly_type}_s{severity}.png"
    if not texture_path.exists():
        logger.error("Texture not found: %s. Run generate_texture_library() first.", texture_path)
        return

    texture = Image.open(str(texture_path)).convert("RGBA")

    # Get video info
    info = _get_video_info(video_path)
    vw, vh = info["width"], info["height"]

    # Auto-position: lower-center of frame (typical transformer base location)
    if position is None:
        position = (vw // 2 - texture.width // 2, int(vh * 0.55))

    # Extract frames
    frames_dir = str(FRAMES_DIR / name)
    logger.info("Extracting frames from %s...", video_path)
    frames = _extract_frames(video_path, frames_dir, fps=5)

    if not frames:
        logger.error("No frames extracted from %s", video_path)
        return

    logger.info("Compositing %s (severity %d) onto %d frames...", anomaly_type, severity, len(frames))

    # Composite texture onto each frame
    for frame_path in frames:
        frame = Image.open(frame_path).convert("RGBA")

        # Scale texture relative to frame size if needed
        max_dim = max(frame.width, frame.height)
        scale = max_dim / 1920  # normalize to 1080p reference
        if scale != 1.0:
            tw = int(texture.width * scale)
            th = int(texture.height * scale)
            scaled_texture = texture.resize((tw, th), Image.LANCZOS)
        else:
            scaled_texture = texture

        # Paste with alpha compositing
        px = min(max(0, position[0]), frame.width - scaled_texture.width)
        py = min(max(0, position[1]), frame.height - scaled_texture.height)
        frame.paste(scaled_texture, (px, py), scaled_texture)

        # Save back as RGB JPEG
        frame.convert("RGB").save(frame_path, "JPEG", quality=95)

    # Encode back to video
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("Encoding composited video to %s...", output_path)
    _encode_video(frames_dir, output_path, fps=5)
    logger.info("Done: %s", output_path)


# ---------------------------------------------------------------------------
# Demo video presets (Tasks 1.7–1.8)
# ---------------------------------------------------------------------------

DEMO_PRESETS = [
    {
        "name": "transformer_oil_leak",
        "source": "transformer_closeup.mp4",
        "anomaly_type": "oil_leak",
        "severity": 2,
        "position": None,  # auto-place at lower center
        "description": "Progressive oil seal degradation over 90 days",
    },
    {
        "name": "bushing_contamination",
        "source": "bushing_detail.mp4",
        "anomaly_type": "contamination",
        "severity": 2,
        "position": None,
        "description": "Surface deposit accumulation leading to flashover risk",
    },
]


def composite_all_demos():
    """Generate all demo videos from presets."""
    for preset in DEMO_PRESETS:
        source = RAW_DIR / preset["source"]
        if not source.exists():
            logger.warning("Source not found: %s — skipping. Download it first (see README).", source)
            continue

        output = DEMO_DIR / f"{preset['name']}.mp4"
        composite_anomaly_on_video(
            video_path=str(source),
            output_path=str(output),
            anomaly_type=preset["anomaly_type"],
            severity=preset["severity"],
            position=preset["position"],
            name=preset["name"],
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info("=== Phase 1: Data Preparation ===")
    logger.info("")

    # Step 1: Generate texture library
    logger.info("--- Step 1: Generating anomaly texture library ---")
    generate_texture_library()
    logger.info("")

    # Step 2: Composite demo videos
    logger.info("--- Step 2: Compositing demo videos ---")
    composite_all_demos()
    logger.info("")

    logger.info("=== Data preparation complete ===")
    logger.info("Textures: %s", TEXTURE_DIR)
    logger.info("Demo videos: %s", DEMO_DIR)
