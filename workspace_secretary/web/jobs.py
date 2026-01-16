"""Background job manager for long-running IMAP operations.

Provides non-blocking batch operations with progress tracking and cancellation.
Used for large inbox cleanup operations (e.g., archiving 1000+ emails).
"""

import logging
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class JobProgress:
    """Progress state for a background job."""

    total: int = 0
    processed: int = 0
    succeeded: int = 0
    failed: int = 0
    current_item: str = ""
    errors: list[str] = field(default_factory=list)


@dataclass
class BackgroundJob:
    """Represents a background job with progress tracking."""

    id: str
    job_type: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    _cancel_requested: bool = field(default=False, repr=False)

    def request_cancel(self) -> None:
        """Request cancellation of the job."""
        self._cancel_requested = True

    @property
    def is_cancel_requested(self) -> bool:
        """Check if cancellation was requested."""
        return self._cancel_requested

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "job_type": self.job_type,
            "status": self.status.value,
            "progress": {
                "total": self.progress.total,
                "processed": self.progress.processed,
                "succeeded": self.progress.succeeded,
                "failed": self.progress.failed,
                "current_item": self.progress.current_item,
                "errors": self.progress.errors[-10:],  # Last 10 errors only
            },
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "result": self.result,
            "error": self.error,
        }


class BackgroundJobManager:
    """Manages background jobs for long-running operations.

    Thread-safe singleton that manages a pool of worker threads
    for executing IMAP batch operations without blocking the web UI.
    """

    _instance: Optional["BackgroundJobManager"] = None
    _lock = threading.Lock()

    def __new__(cls, max_workers: int = 2) -> "BackgroundJobManager":
        """Singleton pattern - only one job manager per process."""
        with cls._lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._initialized = False
                cls._instance = instance
            return cls._instance

    def __init__(self, max_workers: int = 2) -> None:
        """Initialize the job manager with a thread pool."""
        if getattr(self, "_initialized", False):
            return

        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="bg-job-"
        )
        self._jobs: dict[str, BackgroundJob] = {}
        self._futures: dict[str, Future] = {}
        self._job_lock = threading.Lock()
        self._initialized = True
        logger.info(f"BackgroundJobManager initialized with {max_workers} workers")

    def submit_job(
        self,
        job_type: str,
        work_fn: Callable[[BackgroundJob], dict[str, Any]],
        total_items: int = 0,
    ) -> BackgroundJob:
        """Submit a new background job.

        Args:
            job_type: Type identifier for the job (e.g., "batch_archive")
            work_fn: Function to execute. Receives the job object for progress updates.
                     Must return a dict with results.
            total_items: Total number of items to process (for progress tracking)

        Returns:
            The created BackgroundJob object
        """
        job_id = str(uuid.uuid4())[:8]
        job = BackgroundJob(
            id=job_id,
            job_type=job_type,
            status=JobStatus.PENDING,
            progress=JobProgress(total=total_items),
            created_at=datetime.now(),
        )

        with self._job_lock:
            self._jobs[job_id] = job

        def _run_job() -> None:
            """Wrapper that handles job lifecycle."""
            try:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.now()
                logger.info(f"Job {job_id} started: {job_type}")

                result = work_fn(job)

                if job.is_cancel_requested:
                    job.status = JobStatus.CANCELLED
                    logger.info(f"Job {job_id} cancelled")
                else:
                    job.status = JobStatus.COMPLETED
                    job.result = result
                    logger.info(
                        f"Job {job_id} completed: {job.progress.succeeded} succeeded, {job.progress.failed} failed"
                    )

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error = str(e)
                logger.exception(f"Job {job_id} failed: {e}")
            finally:
                job.completed_at = datetime.now()

        future = self._executor.submit(_run_job)
        with self._job_lock:
            self._futures[job_id] = future

        return job

    def get_job(self, job_id: str) -> Optional[BackgroundJob]:
        """Get a job by ID."""
        with self._job_lock:
            return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        """Request cancellation of a job.

        Returns True if the job was found and cancellation requested.
        """
        with self._job_lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False

            if job.status in (
                JobStatus.COMPLETED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
            ):
                return False

            job.request_cancel()
            logger.info(f"Cancellation requested for job {job_id}")
            return True

    def list_jobs(self, include_completed: bool = False) -> list[BackgroundJob]:
        """List all jobs, optionally including completed ones."""
        with self._job_lock:
            if include_completed:
                return list(self._jobs.values())
            return [
                j
                for j in self._jobs.values()
                if j.status in (JobStatus.PENDING, JobStatus.RUNNING)
            ]

    def cleanup_old_jobs(self, max_age_seconds: int = 3600) -> int:
        """Remove completed jobs older than max_age_seconds.

        Returns the number of jobs removed.
        """
        now = datetime.now()
        to_remove = []

        with self._job_lock:
            for job_id, job in self._jobs.items():
                if job.completed_at:
                    age = (now - job.completed_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                self._futures.pop(job_id, None)

        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old jobs")
        return len(to_remove)

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the executor."""
        logger.info("Shutting down BackgroundJobManager")
        self._executor.shutdown(wait=wait)


# Convenience function to get the singleton instance
def get_job_manager() -> BackgroundJobManager:
    """Get the singleton BackgroundJobManager instance."""
    return BackgroundJobManager()
