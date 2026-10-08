"""Helpers shared by the mainframe and Ab Initio syncs for SLA and column metadata."""

from datetime import datetime
from typing import Any, Dict, Iterable, Optional

from sqlalchemy.orm import Session

from src.catalog.models import ColumnLineage, DatasetColumn, Job, JobSla


def upsert_sla(db: Session, job: Job, expected_completion: Optional[datetime]) -> None:
    """Set (or clear, when ``None``) the job's expected completion time."""
    if expected_completion is None:
        if job.sla is not None:
            db.delete(job.sla)
            job.sla = None
        return
    if job.sla is None:
        job.sla = JobSla(job_id=job.id, expected_completion=expected_completion)
    else:
        job.sla.expected_completion = expected_completion


def replace_column_mappings(db: Session, job: Job, mappings: Iterable[Dict[str, Any]]) -> int:
    """Replace the job's column-level lineage with the latest snapshot."""
    db.query(ColumnLineage).filter(ColumnLineage.job_id == job.id).delete()
    count = 0
    for m in mappings:
        db.add(
            ColumnLineage(
                job_id=job.id,
                source_dataset=m["source_dataset"],
                source_column=m["source_column"],
                target_dataset=m["target_dataset"],
                target_column=m["target_column"],
                transformation=m.get("transformation") or None,
            )
        )
        count += 1
    return count


def replace_table_columns(
    db: Session, source_system: str, columns: Iterable[Dict[str, Any]]
) -> int:
    """Replace the platform's table/dataset column list with the latest snapshot."""
    db.query(DatasetColumn).filter(DatasetColumn.source_system == source_system).delete()
    count = 0
    for position, c in enumerate(columns):
        db.add(
            DatasetColumn(
                source_system=source_system,
                dataset_name=c["dataset_name"],
                column_name=c["column_name"],
                data_type=c.get("data_type") or None,
                description=c.get("description") or None,
                position=position,
            )
        )
        count += 1
    return count
