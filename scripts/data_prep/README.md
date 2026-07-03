# Data Preparation — Stock Footage Sources

## Step 1: Download Base Footage

Download these free clips from Pexels. Save them to `data/raw/` with the filenames shown.

```bash
mkdir -p data/raw
```

### Required Clips

| Filename | Source | What to look for |
|----------|--------|------------------|
| `transformer_closeup.mp4` | [Pexels: substation transformer](https://www.pexels.com/search/videos/substation%20transformer/) | Close-up of a power transformer body, 10-25s, stable camera |
| `bushing_detail.mp4` | [Pexels: high voltage bushing](https://www.pexels.com/search/videos/high%20voltage%20bushing/) | Ceramic/porcelain bushings visible, 10-25s |
| `substation_wide.mp4` | [Pexels: electrical substation](https://www.pexels.com/search/videos/electrical%20substation/) | Wide shot showing multiple equipment, 10-25s |
| `insulator_closeup.mp4` | [Pexels: insulator substation](https://www.pexels.com/video/close-up-shot-of-insulators-in-substation-10058463/) | Disc insulator string close-up, 10-25s |

### Selection Criteria

- **Resolution:** 1080p minimum (4K preferred — will be downscaled)
- **Duration:** 10-25 seconds
- **Camera:** Stable (tripod or gimbal) — no handheld shake
- **Lighting:** Daylight, clear visibility
- **Content:** Equipment clearly visible, no people blocking view
- **Format:** MP4 (H.264)

### Pexels Download Tips

1. Go to the search link above
2. Click a video that meets the criteria
3. Click "Free Download" → select HD or 4K
4. Save to `data/raw/` with the filename from the table

## Step 2: Generate Composited Demo Videos

Once raw clips are in `data/raw/`, run:

```bash
python scripts/data_prep/generate_anomalies.py
```

This will:
- Generate procedural anomaly textures (oil leak, corrosion, thermal, contamination)
- Composite them onto the base footage
- Encode output as 1080p H.264
- Save to `data/demo_videos/`

## Step 3: Validate and Generate Thumbnails

```bash
python scripts/data_prep/validate.py
python scripts/data_prep/thumbnails.py
```

## Or run everything at once:

```bash
./scripts/prepare_demo_data.sh
```
