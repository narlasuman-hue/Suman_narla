"""Generic lineage sync: one platform's jobs from a ``BaseLineageConnector`` into the catalog.

Upserts ``Job`` rows (``source_system`` = platform id) with their datasets,
latest run, SLA, column mappings, and the platform's table columns. Works
for any configured platform; see ``src/catalog/platforms.py``.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.catalog.models import AssetStatus, Job, JobFile
from src.catalog.services.job_metadata import (
    replace_column_mappings,
    replace_table_columns,
    upsert_sla,
)
from src.catalog.services.job_runs import RUN_FAILED, record_last_run
from src.connectors.base_lineage import BaseLineageConnector

logger = logging.getLogger(__name__)


class LineageSyncService:
    """Synchronizes one platform's lineage metadata into the catalog."""

    def __init__(self, db: Session, platform_id: str, connector: BaseLineageConnector):
        self.db = db
        self.platform_id = platform_id
        self.connector = connector

    def sync_all(self) -> Dict[str, Any]:
        stats: Dict[str, Any] = {
            "jobs_created": 0,
            "jobs_updated": 0,
            "files_synced": 0,
            "column_mappings_synced": 0,
            "errors": [],
        }
        for job_name in self.connector.get_jobs():
            try:
                self._sync_job(job_name, stats)
            except Exception as e:
                logger.error(f"Failed to sync {self.platform_id} job {job_name}: {e}")
                stats["errors"].append(f"{job_name}: {e}")

        stats["columns_synced"] = replace_table_columns(
            self.db, self.platform_id, self.connector.get_table_columns()
        )
        self.db.commit()
        return stats

    def _sync_job(self, job_name: str, stats: Dict[str, Any]) -> Job:
        details = self.connector.get_job_details(job_name)
        datasets = self.connector.get_job_datasets(job_name)

        job = (
            self.db.query(Job)
            .filter(Job.name == job_name, Job.source_system == self.platform_id)
            .first()
        )
        is_new = job is None
        if is_new:
            job = Job(name=job_name, source_system=self.platform_id)
            self.db.add(job)

        job.owner = details.get("owner")
        job.description = details.get("description")
        job.job_class = details.get("job_class")
        job.status = AssetStatus.ACTIVE  # the job definition; failures are per run
        job.last_run = details.get("last_run")
        job.next_run = details.get("next_run")
        job.scheduler_system = details.get("scheduler_system")
        job.schedule_name = details.get("schedule_name")
        job.frequency = details.get("frequency")
        job.last_synced = datetime.utcnow()
        self.db.flush()  # job.id is needed for the rows below

        # Replace the dataset list with the latest snapshot
        self.db.query(JobFile).filter(JobFile.job_id == job.id).delete()
        for ds in datasets:
            self.db.add(
                JobFile(
                    job_id=job.id,
                    dd_name=ds.get("port"),
                    dataset_name=ds["dataset_name"],
                    direction=ds.get("direction"),
                    dataset_type=ds.get("dataset_type"),
                    disposition=ds.get("disposition"),
                )
            )
        stats["files_synced"] += len(datasets)

        upsert_sla(self.db, job, details.get("expected_completion"))
        stats["column_mappings_synced"] += replace_column_mappings(
            self.db, job, self.connector.get_job_column_lineage(job_name)
        )

        status = details.get("last_run_status") or "UNKNOWN"
        record_last_run(
            self.db,
            job,
            start_time=details.get("last_run"),
            status=status,
            duration_seconds=details.get("duration_seconds"),
            error_message=details.get("error_message") if status == RUN_FAILED else None,
        )

        stats["jobs_updated" if not is_new else "jobs_created"] += 1
        return job
