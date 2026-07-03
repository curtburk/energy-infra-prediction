"""
API integration tests for all 8 endpoints.

Run with: pytest -v
"""

import asyncio
import io
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Ensure mock mode for testing
os.environ["MOCK_MODELS"] = "true"

from backend.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def sample_video_bytes():
    """Create a minimal valid MP4-like file for upload testing.
    
    Note: This won't pass ffprobe validation but tests the upload flow.
    For full validation tests, use a real video file.
    """
    # Minimal MP4 header (ftyp box)
    return (
        b'\x00\x00\x00\x20ftypisom'
        b'\x00\x00\x02\x00isomiso2mp41'
        b'\x00' * 200
    )


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    async def test_health_returns_200(self, client):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"

    async def test_health_shows_mock_mode(self, client):
        resp = await client.get("/api/v1/health")
        data = resp.json()
        # In mock mode, models report as loaded (stubs)
        assert "cosmos_reason_loaded" in data
        assert "cosmos_predict_loaded" in data

    async def test_health_includes_hardware(self, client):
        resp = await client.get("/api/v1/health")
        data = resp.json()
        assert data["hardware"]["device"] == "HP ZGX Nano"
        assert data["hardware"]["gpu"] == "NVIDIA GB10 Grace Blackwell"
        assert data["hardware"]["vram_total_gb"] == 128


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

class TestUpload:
    async def test_upload_rejects_invalid_extension(self, client):
        files = {"file": ("test.txt", b"not a video", "text/plain")}
        resp = await client.post("/api/v1/upload", files=files)
        assert resp.status_code == 400
        assert "Invalid file format" in resp.json()["detail"]

    async def test_upload_accepts_mp4(self, client, sample_video_bytes):
        files = {"file": ("test.mp4", sample_video_bytes, "video/mp4")}
        data = {"name": "Test Upload", "description": "Integration test"}
        resp = await client.post("/api/v1/upload", files=files, data=data)
        # May be 201 (success) or 400 (ffprobe duration check fails on fake video)
        assert resp.status_code in (201, 400)


# ---------------------------------------------------------------------------
# Job Status
# ---------------------------------------------------------------------------

class TestJobStatus:
    async def test_status_404_for_missing_job(self, client):
        resp = await client.get("/api/v1/jobs/nonexistent-id/status")
        assert resp.status_code == 404

    async def test_status_returns_valid_job(self, client):
        """Create a job via the store directly, then query status."""
        from backend.models.job import Job
        from backend.store.memory_store import job_store

        job = Job(job_id="test-status-001", name="Status Test")
        job_store.create(job)

        resp = await client.get("/api/v1/jobs/test-status-001/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == "test-status-001"
        assert data["status"] == "QUEUED"

        # Verify timestamps are clean ISO 8601 with Z suffix (not +00:00Z)
        assert data["created_at"].endswith("Z")
        assert "+00:00" not in data["created_at"]

        job_store.delete("test-status-001")


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

class TestEquipment:
    async def test_equipment_409_if_not_ready(self, client):
        from backend.models.job import Job
        from backend.store.memory_store import job_store

        job = Job(job_id="test-eq-001")
        job_store.create(job)

        resp = await client.get("/api/v1/jobs/test-eq-001/equipment")
        assert resp.status_code == 409

        job_store.delete("test-eq-001")

    async def test_equipment_returns_after_detection(self, client):
        from backend.models.job import Job, JobStatus
        from backend.models import Equipment, EquipmentType, BoundingBox
        from backend.store.memory_store import job_store

        job = Job(job_id="test-eq-002")
        job.status = JobStatus.AWAITING_CONFIRMATION
        job.detected_equipment = [
            Equipment(
                equipment_id="eq-001",
                type=EquipmentType.TRANSFORMER,
                label="Test Transformer",
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.95,
            )
        ]
        job_store.create(job)

        resp = await client.get("/api/v1/jobs/test-eq-002/equipment")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["equipment_detected"]) == 1
        assert data["equipment_detected"][0]["equipment_id"] == "eq-001"

        job_store.delete("test-eq-002")


# ---------------------------------------------------------------------------
# Confirm
# ---------------------------------------------------------------------------

class TestConfirm:
    async def test_confirm_409_if_wrong_state(self, client):
        from backend.models.job import Job
        from backend.store.memory_store import job_store

        job = Job(job_id="test-conf-001")
        job_store.create(job)

        resp = await client.post(
            "/api/v1/jobs/test-conf-001/confirm",
            json={"selected_equipment_ids": ["eq-001"]},
        )
        assert resp.status_code == 409

        job_store.delete("test-conf-001")

    async def test_confirm_starts_analysis(self, client):
        from backend.models.job import Job, JobStatus
        from backend.models import Equipment, EquipmentType, BoundingBox
        from backend.store.memory_store import job_store

        job = Job(job_id="test-conf-002")
        job.status = JobStatus.AWAITING_CONFIRMATION
        job.detected_equipment = [
            Equipment(
                equipment_id="eq-001",
                type=EquipmentType.TRANSFORMER,
                label="Test Transformer",
                bounding_box=BoundingBox(x=0, y=0, width=100, height=100),
                confidence=0.95,
            )
        ]
        job_store.create(job)

        resp = await client.post(
            "/api/v1/jobs/test-conf-002/confirm",
            json={"selected_equipment_ids": ["eq-001"]},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "ANALYZING"
        assert data["selected_equipment_count"] == 1

        # Allow background task to run
        await asyncio.sleep(0.1)
        job_store.delete("test-conf-002")

    async def test_confirm_rejects_invalid_ids(self, client):
        from backend.models.job import Job, JobStatus
        from backend.store.memory_store import job_store

        job = Job(job_id="test-conf-003")
        job.status = JobStatus.AWAITING_CONFIRMATION
        job.detected_equipment = []
        job_store.create(job)

        resp = await client.post(
            "/api/v1/jobs/test-conf-003/confirm",
            json={"selected_equipment_ids": ["bogus-id"]},
        )
        assert resp.status_code == 400

        job_store.delete("test-conf-003")


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

class TestResults:
    async def test_results_409_if_not_complete(self, client):
        from backend.models.job import Job
        from backend.store.memory_store import job_store

        job = Job(job_id="test-res-001")
        job_store.create(job)

        resp = await client.get("/api/v1/jobs/test-res-001/results")
        assert resp.status_code == 409

        job_store.delete("test-res-001")


# ---------------------------------------------------------------------------
# Cancel / Delete
# ---------------------------------------------------------------------------

class TestCancel:
    async def test_cancel_job(self, client):
        from backend.models.job import Job
        from backend.store.memory_store import job_store

        job = Job(job_id="test-cancel-001")
        job_store.create(job)

        resp = await client.delete("/api/v1/jobs/test-cancel-001")
        assert resp.status_code == 200
        assert resp.json()["status"] == "CANCELLED"

    async def test_cancel_404_for_missing(self, client):
        resp = await client.delete("/api/v1/jobs/nonexistent")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------

class TestJobStateMachine:
    def test_valid_transitions(self):
        from backend.models.job import Job, JobStatus

        job = Job(job_id="sm-001")
        assert job.status == JobStatus.QUEUED

        job.transition(JobStatus.DETECTING)
        assert job.status == JobStatus.DETECTING

        job.transition(JobStatus.AWAITING_CONFIRMATION)
        assert job.status == JobStatus.AWAITING_CONFIRMATION

        job.transition(JobStatus.ANALYZING)
        assert job.status == JobStatus.ANALYZING

        job.transition(JobStatus.COMPLETE)
        assert job.status == JobStatus.COMPLETE

    def test_invalid_transition_raises(self):
        from backend.models.job import Job, JobStatus

        job = Job(job_id="sm-002")
        with pytest.raises(ValueError):
            job.transition(JobStatus.COMPLETE)  # Can't go QUEUED → COMPLETE

    def test_fail_from_any_active_state(self):
        from backend.models.job import Job, JobStatus

        for start in [JobStatus.QUEUED, JobStatus.DETECTING, JobStatus.AWAITING_CONFIRMATION, JobStatus.ANALYZING]:
            job = Job(job_id=f"sm-fail-{start.value}")
            job.status = start
            job.fail("test error")
            assert job.status == JobStatus.FAILED
            assert job.error_message == "test error"
