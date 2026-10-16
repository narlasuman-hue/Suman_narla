"""Generic lineage connector interface, for any platform.

A connector describes one platform's jobs: their run state and schedule, the
datasets/tables each job reads and writes, and optionally table columns and
column-level mappings. ``CsvLineageConnector`` reads them from CSV files; a
production connector (scheduler API, metadata export, database catalog)
implements the same methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseLineageConnector(ABC):
    """Source of one platform's lineage metadata."""

    @abstractmethod
    def connect(self) -> None:
        """Open the source (read files, start a session...)."""

    @abstractmethod
    def disconnect(self) -> None:
        """Release the source."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the source is usable."""

    @abstractmethod
    def get_jobs(self) -> List[str]:
        """Names of every job on the platform."""

    @abstractmethod
    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        """Job details and latest run.

        Keys: ``owner``, ``description``, ``job_class``, ``scheduler_system``,
        ``schedule_name``, ``frequency``, ``last_run`` / ``next_run`` (datetimes),
        ``last_run_status`` (SUCCESS / FAILED / RUNNING), ``duration_seconds``,
        ``error_message``, ``expected_completion`` (SLA datetime). Any may be None.
        """

    @abstractmethod
    def get_job_datasets(self, job_name: str) -> List[Dict[str, Any]]:
        """Datasets the job reads or writes.

        Keys: ``dataset_name``, ``direction`` (INPUT / OUTPUT / INOUT),
        ``dataset_type``, and optionally ``port`` and ``disposition``.
        """

    def get_table_columns(self) -> List[Dict[str, Any]]:
        """Optional: ``dataset_name``, ``column_name``, ``data_type``, ``description``."""
        return []

    def get_job_column_lineage(self, job_name: str) -> List[Dict[str, Any]]:
        """Optional: ``source_dataset``, ``source_column``, ``target_dataset``,
        ``target_column``, ``transformation``."""
        return []

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
