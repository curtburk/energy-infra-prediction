"""
Pydantic schemas for API request/response validation.

Reuses domain models from backend.models where shapes match.
Only defines wrapper schemas for API-specific structure (job_id, message, etc.).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from backend.models.job import (
    Anomaly,
    AnalysisSummary,
    BoundingBox,
    CurrentState,
    Equipment,
    EquipmentResult,
    PredictionResult,
    TimeToFailureEstimate,
)


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class UploadResponse(BaseModel):
    job_id: str
    status: str
    created_at: str
    message: str


# ---------------------------------------------------------------------------
# Job Status
# ---------------------------------------------------------------------------

class ProgressInfo(BaseModel):
    stage: Optional[str] = None
    percent_complete: int = 0
    current_operation: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: ProgressInfo
    created_at: str
    updated_at: str
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class EquipmentResponse(BaseModel):
    job_id: str
    equipment_detected: List[Equipment]
    frame_preview_base64: str = ""


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

class AnalysisOptions(BaseModel):
    prediction_horizons: List[int] = Field(default=[30, 60, 90])
    include_severity_assessment: bool = True


class ConfirmRequest(BaseModel):
    selected_equipment_ids: List[str]
    analysis_options: AnalysisOptions = Field(default_factory=AnalysisOptions)


class ConfirmResponse(BaseModel):
    job_id: str
    status: str
    selected_equipment_count: int
    estimated_completion_seconds: int
    message: str


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class ResultsResponse(BaseModel):
    job_id: str
    analysis_completed_at: str
    equipment_results: List[EquipmentResult]
    summary: AnalysisSummary


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HardwareInfo(BaseModel):
    device: str = "HP ZGX Nano"
    gpu: str = "NVIDIA GB10 Grace Blackwell"
    vram_total_gb: int = 128
    vram_available_gb: int = 0


class HealthResponse(BaseModel):
    status: str
    cosmos_reason_loaded: bool = False
    cosmos_predict_loaded: bool = False
    active_jobs: int = 0
    uptime_seconds: float = 0.0
    hardware: HardwareInfo = Field(default_factory=HardwareInfo)


# ---------------------------------------------------------------------------
# Generic
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    job_id: str
    status: str
    message: str
