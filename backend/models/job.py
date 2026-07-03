"""
Core data models and enumerations.
"""

from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class JobStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    DETECTING = "DETECTING"
    AWAITING_CONFIRMATION = "AWAITING_CONFIRMATION"
    ANALYZING = "ANALYZING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class EquipmentType(str, enum.Enum):
    TRANSFORMER = "transformer"
    BUSHING = "bushing"
    INSULATOR = "insulator"
    CIRCUIT_BREAKER = "circuit_breaker"
    SWITCHGEAR = "switchgear"
    CAPACITOR_BANK = "capacitor_bank"
    OTHER = "other"


class AnomalyType(str, enum.Enum):
    OIL_LEAK = "oil_leak"
    THERMAL_HOTSPOT = "thermal_hotspot"
    BUSHING_DAMAGE = "bushing_damage"
    CORROSION = "corrosion"
    VEGETATION_ENCROACHMENT = "vegetation_encroachment"
    INSULATOR_DEGRADATION = "insulator_degradation"
    PHYSICAL_DAMAGE = "physical_damage"


class Severity(str, enum.Enum):
    CRITICAL = "CRITICAL"
    WARNING = "WARNING"
    WATCH = "WATCH"
    NORMAL = "NORMAL"


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------

class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int


class VideoMetadata(BaseModel):
    filename: str
    duration_sec: float
    width: int
    height: int
    fps: float
    codec: str
    file_size_bytes: int


class ConfidenceRange(BaseModel):
    low: int
    high: int


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class Equipment(BaseModel):
    equipment_id: str
    type: EquipmentType
    label: str
    bounding_box: BoundingBox
    confidence: float = Field(ge=0.0, le=1.0)
    thumbnail_base64: str = ""


# ---------------------------------------------------------------------------
# Anomaly
# ---------------------------------------------------------------------------

class Anomaly(BaseModel):
    anomaly_type: AnomalyType
    severity: Severity
    confidence: float = Field(ge=0.0, le=1.0)
    location_description: str = ""
    bounding_box: Optional[BoundingBox] = None
    progression_notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Prediction & Results
# ---------------------------------------------------------------------------

class PredictionResult(BaseModel):
    horizon_days: int
    predicted_anomalies: List[Anomaly] = []
    predicted_health_score: int = Field(ge=0, le=100)


class TimeToFailureEstimate(BaseModel):
    days: int
    confidence_range: ConfidenceRange
    failure_mode: str


class CurrentState(BaseModel):
    anomalies_detected: List[Anomaly] = []
    overall_health_score: int = Field(ge=0, le=100)


class EquipmentResult(BaseModel):
    equipment_id: str
    type: EquipmentType
    label: str
    current_state: CurrentState
    predictions: List[PredictionResult] = []
    time_to_failure_estimate: Optional[TimeToFailureEstimate] = None
    recommended_action: str = ""
    reasoning_chain: str = ""


class AnalysisSummary(BaseModel):
    total_equipment_analyzed: int
    critical_findings: int
    warning_findings: int
    watch_findings: int
    nearest_failure_days: Optional[int] = None
    priority_action: str = ""


def _fmt_utc(dt: datetime) -> str:
    """Format a UTC datetime as ISO 8601 with Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Job (mutable runtime object — not Pydantic, plain class)
# ---------------------------------------------------------------------------

class Job:
    """Mutable job state held in memory store."""

    def __init__(
        self,
        job_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        self.job_id = job_id
        self.status = JobStatus.QUEUED
        self.name = name
        self.description = description
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

        # Progress
        self.progress_stage: Optional[str] = None
        self.progress_percent: int = 0
        self.current_operation: Optional[str] = None

        # Input
        self.video_path: Optional[str] = None
        self.video_metadata: Optional[VideoMetadata] = None

        # Intermediate
        self.detected_equipment: List[Equipment] = []
        self.selected_equipment_ids: List[str] = []
        self.frame_preview_base64: Optional[str] = None

        # Results
        self.equipment_results: List[EquipmentResult] = []
        self.analysis_summary: Optional[AnalysisSummary] = None
        self.output_video_path: Optional[str] = None

        # Error
        self.error_message: Optional[str] = None
        self.error_details: Optional[dict] = None

    # -- State transitions ------------------------------------------------

    _VALID_TRANSITIONS = {
        JobStatus.QUEUED: {JobStatus.DETECTING, JobStatus.FAILED},
        JobStatus.DETECTING: {JobStatus.AWAITING_CONFIRMATION, JobStatus.FAILED},
        JobStatus.AWAITING_CONFIRMATION: {
            JobStatus.ANALYZING,
            JobStatus.FAILED,
            JobStatus.CANCELLED,
        },
        JobStatus.ANALYZING: {JobStatus.COMPLETE, JobStatus.FAILED},
        JobStatus.COMPLETE: set(),
        JobStatus.FAILED: set(),
        JobStatus.CANCELLED: set(),
    }

    def transition(self, new_status: JobStatus) -> None:
        """Transition to a new status with validation."""
        allowed = self._VALID_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {self.status.value} → {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, message: str, details: Optional[dict] = None) -> None:
        """Transition to FAILED with error info."""
        self.error_message = message
        self.error_details = details
        # Allow fail from any non-terminal state
        if self.status not in (JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED):
            self.status = JobStatus.FAILED
            self.updated_at = datetime.now(timezone.utc)

    def update_progress(
        self, stage: str, percent: int, operation: str
    ) -> None:
        self.progress_stage = stage
        self.progress_percent = min(max(percent, 0), 100)
        self.current_operation = operation
        self.updated_at = datetime.now(timezone.utc)

    def to_status_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "progress": {
                "stage": self.progress_stage,
                "percent_complete": self.progress_percent,
                "current_operation": self.current_operation,
            },
            "created_at": _fmt_utc(self.created_at),
            "updated_at": _fmt_utc(self.updated_at),
            "error": self.error_message,
        }

    def to_equipment_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "equipment_detected": [
                eq.model_dump() for eq in self.detected_equipment
            ],
            "frame_preview_base64": self.frame_preview_base64 or "",
        }

    def to_results_dict(self) -> dict:
        return {
            "job_id": self.job_id,
            "analysis_completed_at": _fmt_utc(self.updated_at),
            "equipment_results": [
                er.model_dump() for er in self.equipment_results
            ],
            "summary": (
                self.analysis_summary.model_dump()
                if self.analysis_summary
                else {}
            ),
        }
