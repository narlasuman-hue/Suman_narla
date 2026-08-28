"""Mainframe job, file, and schedule endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.models import AssetStatus, Job, JobFile
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.connectors.mainframe import MockMainframeConnector

router = APIRouter()


def _job_to_dict(job: Job) -> dict:
    return {
        "id": job.id,
        "job_name": job.name,
        "owner": job.owner,
        "status": job.status.value,
        "description": job.description,
        "job_class": job.job_class,
        "scheduler_system": job.scheduler_system,
        "schedule_name": job.schedule_name,
        "frequency": job.frequency,
        "last_run": job.last_run.isoformat() if job.last_run else None,
        "next_run": job.next_run.isoformat() if job.next_run else None,
        "last_synced": job.last_synced.isoformat() if job.last_synced else None,
        "file_count": len(job.files),
    }


def _get_mainframe_job(db: Session, job_id: int) -> Job:
    job = db.get(Job, job_id)
    if not job or job.source_system != "MAINFRAME":
        raise HTTPException(status_code=404, detail="Mainframe job not found")
    return job


@router.get("/mainframe/jobs", response_model=List[dict])
async def list_mainframe_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    schedule_name: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List mainframe jobs.

    - **status**: Filter by asset status
    - **schedule_name**: Filter by scheduler schedule/application name
    """
    query = select(Job).where(Job.source_system == "MAINFRAME")

    if status:
        try:
            query = query.where(Job.status == AssetStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    if schedule_name:
        query = query.where(Job.schedule_name == schedule_name)

    query = query.offset(skip).limit(limit)
    jobs = db.execute(query).scalars().all()

    return [_job_to_dict(j) for j in jobs]


@router.get("/mainframe/jobs/{job_id}", response_model=dict)
async def get_mainframe_job(job_id: int, db: Session = Depends(get_db)):
    """Get mainframe job details by catalog ID."""
    job = _get_mainframe_job(db, job_id)
    return _job_to_dict(job)


@router.get("/mainframe/jobs/{job_id}/files", response_model=List[dict])
async def get_mainframe_job_files(job_id: int, db: Session = Depends(get_db)):
    """List the files/datasets (DD statements) used by a mainframe job."""
    job = _get_mainframe_job(db, job_id)

    files = (
        db.query(JobFile)
        .filter(JobFile.job_id == job.id)
        .order_by(JobFile.dd_name)
        .all()
    )

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


@router.get("/mainframe/jobs/{job_id}/schedule", response_model=dict)
async def get_mainframe_job_schedule(job_id: int, db: Session = Depends(get_db)):
    """Get the scheduler schedule info for a mainframe job."""
    job = _get_mainframe_job(db, job_id)

    return {
        "job_id": job.id,
        "job_name": job.name,
        "scheduler_system": job.scheduler_system,
        "schedule_name": job.schedule_name,
        "frequency": job.frequency,
        "last_run": job.last_run.isoformat() if job.last_run else None,
        "next_run": job.next_run.isoformat() if job.next_run else None,
    }


@router.post("/mainframe/sync", response_model=dict)
async def sync_mainframe_jobs(db: Session = Depends(get_db)):
    """
    Sync mainframe jobs, files, and schedules into the catalog.

    Uses the mock mainframe connector by default; swap in a real
    ``BaseMainframeConnector`` implementation (z/OSMF, FTP/JCL, or a
    scheduler export reader) to sync from an actual mainframe.
    """
    connector = MockMainframeConnector()
    connector.connect()
    try:
        sync_service = create_mainframe_sync_service(db, connector)
        stats = sync_service.sync_all_jobs()
    finally:
        connector.disconnect()

    return stats
