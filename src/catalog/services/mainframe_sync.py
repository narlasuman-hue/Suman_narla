"""Mainframe job synchronization service.

Pulls jobs, their files/datasets, and scheduler schedule info from a
``BaseMainframeConnector`` and upserts them into the shared ``Job`` /
``JobFile`` catalog tables with ``source_system="MAINFRAME"``.
"""

from datetime import datetime
from typing import Any, Dict
import logging

from sqlalchemy.orm import Session

from src.catalog.models import Job, JobFile, AssetStatus
from src.connectors.mainframe import BaseMainframeConnector

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "ACTIVE": AssetStatus.ACTIVE,
    "FAILED": AssetStatus.ACTIVE,  # job definition stays active; failure is per-run
    "INACTIVE": AssetStatus.INACTIVE,
    "DECOMMISSIONED": AssetStatus.DECOMMISSIONED,
}


class MainframeSyncService:
    """Synchronizes mainframe job metadata into the catalog."""

    def __init__(self, db: Session, connector: BaseMainframeConnector):
        self.db = db
        self.connector = connector

    def sync_all_jobs(self) -> Dict[str, Any]:
        """Sync every job the connector knows about."""
        stats = {"jobs_created": 0, "jobs_updated": 0, "files_synced": 0, "errors": []}

        for summary in self.connector.get_jobs():
            job_name = summary["job_name"]
            try:
                self._sync_job(job_name, stats)
            except Exception as e:
                logger.error(f"Failed to sync mainframe job {job_name}: {e}")
                stats["errors"].append(f"{job_name}: {e}")

        self.db.commit()
        return stats

    def _sync_job(self, job_name: str, stats: Dict[str, Any]) -> Job:
        details = self.connector.get_job_details(job_name)
        schedule = self.connector.get_job_schedule(job_name)
        files = self.connector.get_job_files(job_name)

        job = (
            self.db.query(Job)
            .filter(Job.name == job_name, Job.source_system == "MAINFRAME")
            .first()
        )
        is_new = job is None
        if is_new:
            job = Job(name=job_name, source_system="MAINFRAME")
            self.db.add(job)

        job.owner = details.get("owner")
        job.description = details.get("description")
        job.job_class = details.get("job_class")
        job.status = _STATUS_MAP.get(details.get("status"), AssetStatus.ACTIVE)
        job.last_run = details.get("last_run")
        job.next_run = details.get("next_run")
        job.scheduler_system = schedule.get("scheduler_system")
        job.schedule_name = schedule.get("schedule_name")
        job.frequency = schedule.get("frequency")
        job.last_synced = datetime.utcnow()

        self.db.flush()  # ensure job.id is available for file rows

        # Replace the file/dataset list with the latest snapshot
        self.db.query(JobFile).filter(JobFile.job_id == job.id).delete()
        for f in files:
            self.db.add(
                JobFile(
                    job_id=job.id,
                    dd_name=f.get("dd_name"),
                    dataset_name=f["dataset_name"],
                    disposition=f.get("disposition"),
                    direction=f.get("direction"),
                    dataset_type=f.get("dataset_type"),
                    volume_serial=f.get("volume_serial"),
                )
            )
        stats["files_synced"] += len(files)

        if is_new:
            stats["jobs_created"] += 1
        else:
            stats["jobs_updated"] += 1

        return job


def create_mainframe_sync_service(db: Session, connector: BaseMainframeConnector) -> MainframeSyncService:
    """Factory for MainframeSyncService."""
    return MainframeSyncService(db, connector)
