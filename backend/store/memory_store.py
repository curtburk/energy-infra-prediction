"""
In-memory job storage.

Session-persistent: all data lost on service restart.
"""

from __future__ import annotations

import logging
from typing import Dict, Optional

from backend.models.job import Job, JobStatus

logger = logging.getLogger(__name__)


class MemoryStore:
    """In-memory store for jobs. Safe for single-threaded asyncio use."""

    def __init__(self):
        self._jobs: Dict[str, Job] = {}

    # -- CRUD --------------------------------------------------------------

    def create(self, job: Job) -> Job:
        self._jobs[job.job_id] = job
        logger.info("Job created: %s", job.job_id)
        return job

    def get(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def delete(self, job_id: str) -> bool:
        if job_id in self._jobs:
            del self._jobs[job_id]
            logger.info("Job deleted: %s", job_id)
            return True
        return False

    def clear(self) -> None:
        count = len(self._jobs)
        self._jobs.clear()
        logger.info("Store cleared: %d jobs removed", count)

    # -- Queries -----------------------------------------------------------

    def count_active(self) -> int:
        """Count non-terminal jobs."""
        terminal = {JobStatus.COMPLETE, JobStatus.FAILED, JobStatus.CANCELLED}
        return sum(1 for j in self._jobs.values() if j.status not in terminal)


# Singleton instance
job_store = MemoryStore()
