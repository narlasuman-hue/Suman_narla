"""Helpers for recording the latest run of a synced job.

Source systems (mainframe schedulers, Ab Initio Control>Center) report the
latest run of a job alongside its definition. Storing that run as a
``JobExecution`` lets the lineage view show run state (failed, running,
succeeded) next to each job without a separate run-history feed.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from src.catalog.models import Job, JobExecution

RUN_SUCCESS = "SUCCESS"
RUN_FAILED = "FAILED"
RUN_RUNNING = "RUNNING"


def record_last_run(
    db: Session,
    job: Job,
    start_time: Optional[datetime],
    status: str,
    duration_seconds: Optional[int] = None,
    error_message: Optional[str] = None,
) -> Optional[JobExecution]:
    """Upsert the run of ``job`` that started at ``start_time``.

    Re-syncing the same run updates it in place (e.g. RUNNING -> SUCCESS)
    instead of adding a duplicate row. Returns ``None`` when the source
    reported no run.
    """
    if start_time is None:
        return None

    execution = (
        db.query(JobExecution)
        .filter(JobExecution.job_id == job.id, JobExecution.start_time == start_time)
        .first()
    )
    if execution is None:
        execution = JobExecution(job_id=job.id, start_time=start_time)
        db.add(execution)

    execution.status = status
    execution.duration_seconds = duration_seconds
    execution.error_message = error_message
    return execution
