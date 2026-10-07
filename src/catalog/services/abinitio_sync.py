"""Ab Initio (Hadoop) graph synchronization service.

Pulls graphs, the datasets they read/write, schedule info, and the latest
run from a ``BaseAbInitioConnector`` and upserts them into the shared
``Job`` / ``JobFile`` catalog tables with ``source_system="HADOOP_ABINITIO"``.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from sqlalchemy.orm import Session

from src.catalog.models import AssetStatus, Job, JobFile
from src.catalog.services.job_runs import record_last_run
from src.connectors.abinitio import BaseAbInitioConnector

logger = logging.getLogger(__name__)

SOURCE_SYSTEM = "HADOOP_ABINITIO"


class AbInitioSyncService:
    """Synchronizes Ab Initio graph metadata into the catalog."""

    def __init__(self, db: Session, connector: BaseAbInitioConnector):
        self.db = db
        self.connector = connector

    def sync_all_graphs(self) -> Dict[str, Any]:
        """Sync every graph the connector knows about."""
        stats = {"jobs_created": 0, "jobs_updated": 0, "files_synced": 0, "errors": []}

        for summary in self.connector.get_graphs():
            graph_name = summary["graph_name"]
            try:
                self._sync_graph(graph_name, stats)
            except Exception as e:
                logger.error(f"Failed to sync Ab Initio graph {graph_name}: {e}")
                stats["errors"].append(f"{graph_name}: {e}")

        self.db.commit()
        return stats

    def _sync_graph(self, graph_name: str, stats: Dict[str, Any]) -> Job:
        details = self.connector.get_graph_details(graph_name)
        schedule = self.connector.get_graph_schedule(graph_name)
        datasets = self.connector.get_graph_datasets(graph_name)

        job = (
            self.db.query(Job)
            .filter(Job.name == graph_name, Job.source_system == SOURCE_SYSTEM)
            .first()
        )
        is_new = job is None
        if is_new:
            job = Job(name=graph_name, source_system=SOURCE_SYSTEM)
            self.db.add(job)

        job.owner = details.get("owner")
        job.description = details.get("description")
        job.status = AssetStatus.ACTIVE
        job.last_run = details.get("last_run")
        job.next_run = details.get("next_run")
        job.scheduler_system = schedule.get("scheduler_system")
        job.schedule_name = schedule.get("schedule_name")
        job.frequency = schedule.get("frequency")
        job.last_synced = datetime.utcnow()

        self.db.flush()  # ensure job.id is available for dataset rows

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
                )
            )
        stats["files_synced"] += len(datasets)

        record_last_run(
            self.db,
            job,
            start_time=details.get("last_run"),
            status=details.get("last_run_status") or "UNKNOWN",
            duration_seconds=details.get("duration_seconds"),
            error_message=details.get("error_message"),
        )

        if is_new:
            stats["jobs_created"] += 1
        else:
            stats["jobs_updated"] += 1

        return job


def create_abinitio_sync_service(
    db: Session, connector: BaseAbInitioConnector
) -> AbInitioSyncService:
    """Factory for AbInitioSyncService."""
    return AbInitioSyncService(db, connector)
