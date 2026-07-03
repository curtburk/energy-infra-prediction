# Backup & Recovery Plan

## Failure Scenarios and Recovery

### Tier 1: Quick Recovery (<30 seconds)

**Frontend not loading**
```bash
cd ~/Desktop/DoE-demo/frontend && npm run dev
```

**Backend not responding**
```bash
fuser -k 8094/tcp
MOCK_MODELS=false ./scripts/start.sh
```

**Upload rejected**
- Check video duration (must be 8-25 seconds)
- Check format (MP4, MOV, AVI only)
- Fall back to Quick Demo

---

### Tier 2: Moderate Recovery (1-3 minutes)

**vLLM crashed or unresponsive**
```bash
docker rm -f cosmos-reason-vllm
./scripts/start_cosmos_reason.sh
# Wait ~2.5 minutes for model to load
```

**Detection timeout**
- The model takes 2-3 minutes — wait it out
- If >5 minutes, check backend logs: `tail -f /tmp/grid-anomaly-backend.log`
- Fall back to Quick Demo while it recovers

**GPU out of memory**
```bash
docker stop cosmos-reason-vllm
sleep 10
# Restart with reduced memory
docker rm -f cosmos-reason-vllm
./scripts/start_cosmos_reason.sh
```

---

### Tier 3: Full Reset (5 minutes)

**Everything broken — nuclear option**
```bash
# Stop everything
./scripts/stop_all.sh  # Say yes to stop vLLM
docker rm -f cosmos-reason-vllm 2>/dev/null

# Clear GPU state
sleep 10

# Restart everything
./scripts/start_all.sh --real
./scripts/preflight.sh
```

---

### Tier 4: Hardware Failure

**GPU not detected**
- Check nvidia-smi — if no GPU, hardware issue
- Reboot the ZGX Nano
- Fall back to Mock mode: `./scripts/start_all.sh` (no --real flag)
- Quick Demo still works in mock mode

**Network issues at venue**
- Demo is fully offline — no internet required
- Quick Demo works with no backend at all (static data)
- If DNS issues prevent font loading, the UI falls back to system-ui sans-serif

---

## The Golden Rule

**Quick Demo always works.** No GPU, no backend, no models needed. If anything goes wrong during a live demo, click "New Analysis" → "Launch Quick Demo" and you're back to the full results page with pre-rendered AI output in under 1 second.

---

## Pre-Event Checklist

- [ ] Run `./scripts/preflight.sh` — all checks pass
- [ ] Test Quick Demo — video plays, charts render, cards show data
- [ ] Test live upload — detection completes, results display
- [ ] Verify `watch -n 1 nvidia-smi` shows GPU activity during processing
- [ ] Check venue monitor resolution (demo optimized for 1280px+)
- [ ] Bring power cable for ZGX Nano
- [ ] Bring ethernet cable (WiFi not guaranteed at venues)
- [ ] Have backup video files on USB drive
