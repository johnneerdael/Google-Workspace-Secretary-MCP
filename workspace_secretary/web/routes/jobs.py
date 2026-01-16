"""Background jobs API routes.

Provides endpoints for:
- Starting background batch operations
- Checking job status/progress
- Cancelling running jobs
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException

from workspace_secretary.web.auth import get_session
from workspace_secretary.web.jobs import get_job_manager, JobStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/")
async def list_jobs(include_completed: bool = False):
    """List all background jobs.

    Query params:
        include_completed: Include completed/failed jobs (default: false)
    """
    manager = get_job_manager()
    jobs = manager.list_jobs(include_completed=include_completed)

    return {
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs),
    }


@router.get("/{job_id}")
async def get_job(job_id: str):
    """Get status and progress of a specific job."""
    manager = get_job_manager()
    job = manager.get_job(job_id)

    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return job.to_dict()


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """Request cancellation of a running job."""
    manager = get_job_manager()
    cancelled = manager.cancel_job(job_id)

    if not cancelled:
        job = manager.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel job in status: {job.status.value}"
        )

    job = manager.get_job(job_id)
    return {
        "message": "Cancellation requested",
        "job": job.to_dict() if job else None,
    }


@router.post("/cleanup")
async def cleanup_jobs(max_age_seconds: int = 3600):
    """Remove old completed jobs.

    Args:
        max_age_seconds: Max age of jobs to keep (default: 3600)
    """
    manager = get_job_manager()
    removed = manager.cleanup_old_jobs(max_age_seconds=max_age_seconds)

    return {
        "message": f"Removed {removed} old jobs",
        "removed_count": removed,
    }
