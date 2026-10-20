"""Job list, detail and dataset endpoints for any lineage platform.

``/platforms/{platform}/jobs`` serves every platform in ``platforms.csv``
(Mainframe, Ab Initio, Informatica, Airflow, DataStage, ...). The older
``/mainframe/jobs`` routes use the same helpers for the MAINFRAME platform.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from src.catalog.database import get_db
from src.catalog.models import Job, JobExecution, JobFile
from src.catalog.platforms import get_platform

router = APIRouter()

RUN_STATUSES = ("SUCCESS", "FAILED", "RUNNING")


def _latest_run(job: Job) -> Optional[JobExecution]:
    """The job's current run; a run without a start time counts as the newest."""
    return max(
        job.executions,
        key=lambda e: (e.start_time is None, e.start_time or datetime.min),
        default=None,
    )


def job_to_dict(job: Job) -> dict:
    run = _latest_run(job)
    return {
        "id": job.id,
        "job_name": job.name,
        "platform": job.source_system,
        "owner": job.owner,
        "status": job.status.value,
        "description": job.description,
        "job_class": job.job_class,
        "scheduler_system": job.scheduler_system,
        "schedule_name": job.schedule_name,
        "frequency": job.frequency,
        "last_run": job.last_run.isoformat() if job.last_run else None,
        "last_run_status": run.status if run else None,
        "last_run_error": run.error_message if run else None,
        "next_run": job.next_run.isoformat() if job.next_run else None,
        "last_synced": job.last_synced.isoformat() if job.last_synced else None,
        "file_count": len(job.files),
    }


def get_job_on_platform(db: Session, platform: str, job_id: int) -> Job:
    """The job with this catalog id, or 404 if it belongs to another platform."""
    job = db.get(Job, job_id)
    if not job or job.source_system != platform:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


def job_files(db: Session, job: Job) -> List[dict]:
    files = db.query(JobFile).filter(JobFile.job_id == job.id).order_by(JobFile.dd_name).all()
    return [
        {
            "id": f.id,
            "dd_name": f.dd_name,
            "dataset_name": f.dataset_name,
            "disposition": f.disposition,
            "direction": f.direction,
            "dataset_type": f.dataset_type,
            "volume_serial": f.volume_serial,
        }
        for f in files
    ]


def _check_platform(platform: str) -> None:
    try:
        get_platform(platform)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown platform: {platform}")


@router.get("/platforms/{platform}/jobs", response_model=List[dict])
async def list_platform_jobs(
    platform: str,
    db: Session = Depends(get_db),
    run_status: Optional[str] = Query(None, description="SUCCESS, FAILED or RUNNING"),
    skip: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
):
    """List one platform's jobs by name, with their latest run status."""
    _check_platform(platform)
    if run_status and run_status.upper() not in RUN_STATUSES:
        raise HTTPException(status_code=400, detail="run_status must be SUCCESS, FAILED or RUNNING")

    query = (
        select(Job)
        .where(Job.source_system == platform)
        .options(selectinload(Job.files), selectinload(Job.executions))
        .order_by(Job.name)
    )
    jobs = [job_to_dict(j) for j in db.execute(query).scalars().all()]
    if run_status:
        jobs = [j for j in jobs if j["last_run_status"] == run_status.upper()]
    return jobs[skip : skip + limit]


@router.get("/platforms/{platform}/jobs/{job_id}", response_model=dict)
async def get_platform_job(platform: str, job_id: int, db: Session = Depends(get_db)):
    """One job of a platform, by catalog id."""
    return job_to_dict(get_job_on_platform(db, platform, job_id))


@router.get("/platforms/{platform}/jobs/{job_id}/files", response_model=List[dict])
async def get_platform_job_files(platform: str, job_id: int, db: Session = Depends(get_db)):
    """The datasets/tables/files a job reads and writes."""
    return job_files(db, get_job_on_platform(db, platform, job_id))
