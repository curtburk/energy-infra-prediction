# Grid Infrastructure Anomaly Prediction — Demo Runbook

## Pre-Demo Setup (30 minutes before)

### 1. Start services
```bash
cd ~/Desktop/DoE-demo
./scripts/start_all.sh --real
```

### 2. Run preflight check
```bash
./scripts/preflight.sh
```
All checks must pass. If vLLM or backend fail, check `/tmp/grid-anomaly-backend.log`.

### 3. Prepare terminals
Open 3 terminal windows, arranged side-by-side:
- **Terminal 1:** Browser with frontend (`http://<ip>:5173`)
- **Terminal 2:** `watch -n 1 nvidia-smi` (GPU monitoring)
- **Terminal 3:** `tail -f /tmp/grid-anomaly-backend.log` (pipeline logs)

### 4. Test Quick Demo
Click "Launch Quick Demo" to verify pre-rendered results and video load correctly.

---

## Demo Script (10-15 minutes)

### Opening (1 minute)
> "I'm going to show you an on-premises AI system that predicts equipment degradation
> in electrical substation infrastructure. Everything you're about to see runs on this
> HP ZGX Nano — a $4,000 box with an NVIDIA GB10 GPU. No cloud. No API calls.
> Your data never leaves the building."

### Act 1: The Result (2 minutes)
1. Click **"Launch Quick Demo"**
2. Walk through the results page:
   - Point to the **morph video**: "This is what Cosmos AI predicts your transformer
     will look like in 30, 60, and 90 days if this oil leak goes unaddressed."
   - Play the video — let it morph from clean to degraded
   - Point to the **Health Score chart**: "Health drops from 85 to 49 over 90 days,
     crossing the critical threshold around day 85."
   - Point to the **anomaly cards**: "Five anomalies detected — oil leak, thermal
     hotspots, corrosion, bushing damage, insulator degradation. Each with confidence
     scores and specific locations."
   - Expand **AI Reasoning** section
   - Point to **Recommended Action**: "The system tells your maintenance team exactly
     what to do and when."

### Act 2: How It Works (2 minutes)
> "Let me show you what's happening under the hood."

1. Click **"New Analysis"**
2. Upload `data/raw/transformer_closeup.mp4` (or drag and drop)
3. Point to Terminal 2 (nvidia-smi): "Watch the GPU light up — 96% utilization.
   That's Cosmos-Reason1-7B analyzing the footage right now."
4. Point to Terminal 3 (logs): "You can see each stage of the pipeline."
5. While detection runs (~2 min), narrate:
   > "The first model, Cosmos Reason, is a 7-billion parameter vision-language model.
   > It looks at each frame and identifies every piece of equipment — transformers,
   > bushings, insulators, circuit breakers. Then it classifies any visible anomalies
   > with chain-of-thought reasoning."

### Act 3: Equipment Confirmation (1 minute)
1. When detection completes, show the **Equipment Selection** page
2. Point to detected equipment with confidence scores
3. "The operator confirms which equipment to analyze in depth."
4. Click **"Start Analysis"**

### Act 4: Live Processing (3-4 minutes)
1. Show the **Processing** page with stages advancing
2. Point to nvidia-smi showing GPU activity
3. Narrate during processing:
   > "Now Cosmos3-Nano, a 16-billion parameter video generation model, is creating
   > what this transformer will look like in 30, 60, and 90 days based on the
   > detected anomalies. Both models are running simultaneously on this single device."
4. When complete, show live results

### Act 5: The Value Proposition (2 minutes)
> "What you just saw is Compliance by Architecture. The video never left this device.
> There were zero cloud API calls. No per-token costs.
>
> For DOE and national lab facilities:
> - FEDRAMP and CMMC compliance by design — data never leaves the network
> - No internet required — works in air-gapped environments
> - Predictive maintenance on thousands of hours of existing camera footage
> - $4,000 hardware running two AI models simultaneously
>
> The same pipeline that analyzed one transformer can process your entire
> substation camera infrastructure on a fleet of these boxes."

### Closing
> "Questions?"

---

## Troubleshooting During Demo

| Problem | Quick Fix |
|---------|-----------|
| Upload shows "Detection failed" | Backend timeout — wait and retry, or fall back to Quick Demo |
| Video player is black | Video still rendering — wait 30 seconds, or use Quick Demo |
| Frontend not loading | `cd frontend && npm run dev` in a terminal |
| vLLM crashed | `docker restart cosmos-reason-vllm` — takes 2 min to reload |
| GPU out of memory | `docker stop cosmos-reason-vllm`, wait 30 sec, restart |
| Everything broken | Quick Demo always works — click "Launch Quick Demo" |

## Key Numbers for Q&A

| Metric | Value |
|--------|-------|
| Hardware cost | ~$3,999 (HP ZGX Nano) |
| GPU | NVIDIA GB10 Grace Blackwell, 128GB unified memory |
| Detection model | Cosmos-Reason1-7B (7B params, via vLLM) |
| Video generation model | Cosmos3-Nano (16B params, via diffusers) |
| Combined GPU usage | ~78GB of 128GB |
| Detection time | ~2-3 minutes |
| Full pipeline | ~8-10 minutes |
| Cloud dependency | Zero |
| Data exfiltration risk | Zero — on-premises only |
| Per-token cost | $0 (no metered API) |
| Software licensing | ZGX Toolkit included free (vs $625-$4,500/yr NVIDIA AI Enterprise) |
