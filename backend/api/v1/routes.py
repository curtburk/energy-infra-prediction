"""
API v1 route definitions.

All 8 endpoints per BACKEND_SPEC.md §6.
"""

from __future__ import annotations

import logging
import os
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from backend.config import settings
from backend.models.job import Job, JobStatus, VideoMetadata
from backend.store.memory_store import job_store
from backend.services.orchestrator import orchestrator
from backend.api.v1.schemas import (
    ConfirmRequest,
    ConfirmResponse,
    EquipmentResponse,
    HealthResponse,
    HardwareInfo,
    JobStatusResponse,
    MessageResponse,
    ResultsResponse,
    UploadResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_job_or_404(job_id: str) -> Job:
    job = job_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def _probe_video_metadata(file_path: str, filename: str, file_size: int) -> VideoMetadata:
    """Extract video metadata using ffprobe. Falls back to defaults."""
    import subprocess
    import json

    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format", "-show_streams",
                file_path,
            ],
            capture_output=True, text=True, timeout=15,
        )
        info = json.loads(result.stdout)
        video_stream = next(
            (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
            {},
        )
        fmt = info.get("format", {})
        fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
        fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 and float(fps_parts[1]) else 30.0

        return VideoMetadata(
            filename=filename,
            duration_sec=float(fmt.get("duration", 15)),
            width=int(video_stream.get("width", 1920)),
            height=int(video_stream.get("height", 1080)),
            fps=fps,
            codec=video_stream.get("codec_name", "h264"),
            file_size_bytes=file_size,
        )
    except Exception as e:
        logger.warning("ffprobe failed, using defaults: %s", e)
        return VideoMetadata(
            filename=filename,
            duration_sec=15.0,
            width=1920,
            height=1080,
            fps=30.0,
            codec="h264",
            file_size_bytes=file_size,
        )


# ---------------------------------------------------------------------------
# 6.2.1  Upload Video
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_video(
    file: UploadFile = File(...),
    name: str = Form(default=None),
    description: str = Form(default=None),
):
    """Upload a video for analysis."""
    # Validate content type
    ext = Path(file.filename or "").suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format '{ext}'. Accepted: {settings.ALLOWED_EXTENSIONS}",
        )

    # Check queue capacity
    if job_store.count_active() >= settings.MAX_CONCURRENT_JOBS:
        raise HTTPException(status_code=503, detail="Processing queue full")

    # Save upload
    job_id = str(uuid.uuid4())
    upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename or f"upload{ext}")

    file_size = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            file_size += len(chunk)
            if file_size > settings.max_upload_bytes:
                os.remove(file_path)
                raise HTTPException(
                    status_code=400,
                    detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB}MB limit",
                )
            f.write(chunk)

    # Probe video metadata
    metadata = _probe_video_metadata(file_path, file.filename or "upload", file_size)

    # Validate duration
    if metadata.duration_sec < settings.MIN_DURATION_SEC:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Video too short ({metadata.duration_sec:.1f}s). Minimum: {settings.MIN_DURATION_SEC}s",
        )
    if metadata.duration_sec > settings.MAX_DURATION_SEC:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Video too long ({metadata.duration_sec:.1f}s). Maximum: {settings.MAX_DURATION_SEC}s",
        )

    # Validate resolution
    if metadata.height < 720:
        os.remove(file_path)
        raise HTTPException(
            status_code=400,
            detail=f"Resolution too low ({metadata.width}x{metadata.height}). Minimum: 720p",
        )

    # Create job
    job = Job(job_id=job_id, name=name, description=description)
    job.video_path = file_path
    job.video_metadata = metadata
    job_store.create(job)

    # Kick off detection
    await orchestrator.start_detection(job_id)

    return UploadResponse(
        job_id=job_id,
        status=job.status.value,
        created_at=job.created_at.isoformat() + "Z",
        message="Video uploaded successfully. Processing will begin shortly.",
    )


# ---------------------------------------------------------------------------
# 6.2.2  Poll Job Status
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """Poll job status and progress."""
    job = _get_job_or_404(job_id)
    return job.to_status_dict()


# ---------------------------------------------------------------------------
# 6.2.3  Get Detected Equipment
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/equipment", response_model=EquipmentResponse)
async def get_detected_equipment(job_id: str):
    """Retrieve detected equipment list."""
    job = _get_job_or_404(job_id)

    if job.status not in (
        JobStatus.AWAITING_CONFIRMATION,
        JobStatus.ANALYZING,
        JobStatus.COMPLETE,
    ):
        raise HTTPException(
            status_code=409,
            detail=f"Equipment not available in state '{job.status.value}'. "
                   f"Must be AWAITING_CONFIRMATION or later.",
        )

    return job.to_equipment_dict()


# ---------------------------------------------------------------------------
# 6.2.4  Confirm Equipment Selection
# ---------------------------------------------------------------------------

@router.post("/jobs/{job_id}/confirm", response_model=ConfirmResponse, status_code=202)
async def confirm_equipment(job_id: str, body: ConfirmRequest):
    """Confirm equipment selection and start analysis."""
    job = _get_job_or_404(job_id)

    if job.status != JobStatus.AWAITING_CONFIRMATION:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot confirm in state '{job.status.value}'. Must be AWAITING_CONFIRMATION.",
        )

    # Validate IDs
    valid_ids = {eq.equipment_id for eq in job.detected_equipment}
    invalid = set(body.selected_equipment_ids) - valid_ids
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid equipment IDs: {invalid}",
        )
    if not body.selected_equipment_ids:
        raise HTTPException(status_code=400, detail="No equipment selected")

    job.selected_equipment_ids = body.selected_equipment_ids
    job.transition(JobStatus.ANALYZING)

    # Start analysis pipeline
    await orchestrator.start_analysis(job_id)

    est_seconds = len(body.selected_equipment_ids) * 90  # rough estimate

    return ConfirmResponse(
        job_id=job_id,
        status=job.status.value,
        selected_equipment_count=len(body.selected_equipment_ids),
        estimated_completion_seconds=est_seconds,
        message=f"Analysis started for {len(body.selected_equipment_ids)} equipment items.",
    )


# ---------------------------------------------------------------------------
# 6.2.5  Get Analysis Results
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/results", response_model=ResultsResponse)
async def get_results(job_id: str):
    """Retrieve final analysis results."""
    job = _get_job_or_404(job_id)

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Results not available in state '{job.status.value}'. Must be COMPLETE.",
        )

    return job.to_results_dict()


# ---------------------------------------------------------------------------
# 6.2.6  Get Annotated Video
# ---------------------------------------------------------------------------

@router.get("/jobs/{job_id}/video")
async def get_video(job_id: str):
    """Stream/download annotated morph video."""
    job = _get_job_or_404(job_id)

    if job.status != JobStatus.COMPLETE:
        raise HTTPException(
            status_code=409,
            detail=f"Video not available in state '{job.status.value}'. Must be COMPLETE.",
        )

    if not job.output_video_path or not os.path.exists(job.output_video_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    return FileResponse(
        path=job.output_video_path,
        media_type="video/mp4",
        filename=f"analysis-{job_id}.mp4",
    )


# ---------------------------------------------------------------------------
# 6.2.7  Cancel / Delete Job
# ---------------------------------------------------------------------------

@router.delete("/jobs/{job_id}", response_model=MessageResponse)
async def cancel_job(job_id: str):
    """Cancel a job and clean up resources."""
    job = _get_job_or_404(job_id)

    await orchestrator.cancel(job_id)

    # Transition to CANCELLED if not already terminal
    terminal = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
    if job.status not in terminal:
        job.status = JobStatus.CANCELLED

    # Clean up upload files
    upload_dir = os.path.join(settings.UPLOAD_DIR, job_id)
    if os.path.exists(upload_dir):
        shutil.rmtree(upload_dir, ignore_errors=True)

    return MessageResponse(
        job_id=job_id,
        status="CANCELLED",
        message="Job cancelled and resources cleaned up",
    )


# ---------------------------------------------------------------------------
# 6.2.8  Health Check
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Service health check."""
    from backend.main import get_uptime
    from backend.services.model_manager import model_manager

    return HealthResponse(
        status="healthy",
        cosmos_reason_loaded=model_manager.reason_loaded,
        cosmos_predict_loaded=model_manager.predict_loaded,
        active_jobs=job_store.count_active(),
        uptime_seconds=round(get_uptime(), 1),
        hardware=HardwareInfo(
            vram_available_gb=model_manager.get_vram_available_gb(),
        ),
    )
