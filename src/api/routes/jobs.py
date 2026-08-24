"""Job and schedule endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from src.catalog.database import get_db
from src.catalog.models import Job, JobExecution, AssetStatus

router = APIRouter()


@router.get("/jobs", response_model=List[dict])
async def list_jobs(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List all jobs/schedules.

    - **status**: Filter by asset status
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    query = select(Job)

    if status:
        try:
            asset_status = AssetStatus(status)
            query = query.where(Job.status == asset_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    query = query.offset(skip).limit(limit)
    jobs = db.execute(query).scalars().all()

    return [
        {
            "id": j.id,
            "name": j.name,
            "owner": j.owner,
            "status": j.status.value,
            "schedule": j.schedule,
            "frequency": j.frequency,
            "created_at": j.created_at.isoformat() if j.created_at else None,
            "last_run": j.last_run.isoformat() if j.last_run else None,
            "next_run": j.next_run.isoformat() if j.next_run else None,
            "execution_count": len(j.executions),
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}", response_model=dict)
async def get_job(job_id: int, db: Session = Depends(get_db)):
    """Get job details by ID."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {
        "id": job.id,
        "name": job.name,
        "owner": job.owner,
        "status": job.status.value,
        "description": job.description,
        "schedule": job.schedule,
        "frequency": job.frequency,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "last_run": job.last_run.isoformat() if job.last_run else None,
        "next_run": job.next_run.isoformat() if job.next_run else None,
        "execution_timeout_seconds": job.execution_timeout_seconds,
        "execution_count": len(job.executions),
    }


@router.get("/jobs/{job_id}/executions", response_model=List[dict])
async def get_job_executions(
    job_id: int,
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """Get execution history for a job."""
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    executions = (
        db.query(JobExecution)
        .filter(JobExecution.job_id == job_id)
        .order_by(JobExecution.start_time.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return [
        {
            "id": e.id,
            "job_id": e.job_id,
            "start_time": e.start_time.isoformat(),
            "end_time": e.end_time.isoformat() if e.end_time else None,
            "status": e.status,
            "duration_seconds": e.duration_seconds,
            "rows_processed": e.rows_processed,
            "error_message": e.error_message,
        }
        for e in executions
    ]


@router.post("/jobs", response_model=dict, status_code=201)
async def create_job(
    name: str,
    owner: Optional[str] = None,
    schedule: Optional[str] = None,
    frequency: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new job record."""
    existing = db.query(Job).filter(Job.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Job already exists")

    job = Job(
        name=name,
        owner=owner,
        schedule=schedule,
        frequency=frequency,
        description=description,
        status=AssetStatus.ACTIVE,
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "id": job.id,
        "name": job.name,
        "owner": job.owner,
        "status": job.status.value,
        "created_at": job.created_at.isoformat(),
    }
