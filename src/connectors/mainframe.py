"""Mainframe job connector.

Exposes job details, the files/datasets a job uses, and the scheduler
schedule name behind the same connector shape used elsewhere in this
project (``connect`` / ``disconnect`` / ``is_connected``), so a real
integration can be dropped in without touching the sync service, API
routes, or frontend.

``MockMainframeConnector`` returns realistic sample data shaped like a
z/OSMF job-info response (see IBM z/OSMF Jobs REST API:
``GET /zosmf/restjobs/jobs``) plus DD/dataset and scheduler details. A
production connector (z/OSMF REST calls, an FTP/JCL pull, or a scheduler
export reader for CA-7/Control-M/OPC-TWS) implements
``BaseMainframeConnector`` the same way and can be swapped in via
``src/config.py`` without changing any other layer.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class BaseMainframeConnector(ABC):
    """Abstract interface for retrieving mainframe job metadata."""

    @abstractmethod
    def connect(self) -> None:
        """Establish the connection (or session) to the mainframe."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the connection."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Whether the connector currently has a usable connection."""

    @abstractmethod
    def get_jobs(self) -> List[Dict[str, Any]]:
        """List known mainframe jobs with summary info."""

    @abstractmethod
    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        """Get full details for a single job by JCL job name."""

    @abstractmethod
    def get_job_files(self, job_name: str) -> List[Dict[str, Any]]:
        """List the files/datasets (DD statements) a job reads or writes."""

    @abstractmethod
    def get_job_schedule(self, job_name: str) -> Dict[str, Any]:
        """Get the scheduler-side schedule info for a job."""

    def get_table_columns(self) -> List[Dict[str, Any]]:
        """Optional: columns of the tables/datasets this platform uses.

        Each item: ``dataset_name``, ``column_name`` and optionally
        ``data_type`` / ``description``. Default: none.
        """
        return []

    def get_job_column_lineage(self, job_name: str) -> List[Dict[str, Any]]:
        """Optional: column mappings the job applies.

        Each item: ``source_dataset``, ``source_column``, ``target_dataset``,
        ``target_column`` and optionally ``transformation``. Default: none.
        """
        return []

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()


class MockMainframeConnector(BaseMainframeConnector):
    """Sample-data mainframe connector for development and demos.

    Returns fixed, realistic-looking job/dataset/schedule data instead of
    talking to a real mainframe. Useful for building and testing the API
    and UI before a real z/OSMF or scheduler integration is wired up.
    """

    def __init__(self):
        self._connected = False
        self._jobs = self._build_jobs()

    def connect(self) -> None:
        self._connected = True
        logger.info("Connected to mock mainframe data source")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("Disconnected from mock mainframe data source")

    def is_connected(self) -> bool:
        return self._connected

    def get_jobs(self) -> List[Dict[str, Any]]:
        return [
            {
                "job_name": j["job_name"],
                "job_id": j["job_id"],
                "owner": j["owner"],
                "job_class": j["job_class"],
                "status": j["status"],
                "scheduler_system": j["schedule"]["scheduler_system"],
                "schedule_name": j["schedule"]["schedule_name"],
            }
            for j in self._jobs.values()
        ]

    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        job = self._jobs.get(job_name)
        if not job:
            raise KeyError(f"Unknown mainframe job: {job_name}")
        return {k: v for k, v in job.items() if k not in ("files",)}

    def get_job_files(self, job_name: str) -> List[Dict[str, Any]]:
        job = self._jobs.get(job_name)
        if not job:
            raise KeyError(f"Unknown mainframe job: {job_name}")
        return job["files"]

    def get_job_schedule(self, job_name: str) -> Dict[str, Any]:
        job = self._jobs.get(job_name)
        if not job:
            raise KeyError(f"Unknown mainframe job: {job_name}")
        return job["schedule"]

    @staticmethod
    def _build_jobs() -> Dict[str, Dict[str, Any]]:
        # Truncate to the hour so repeated syncs of the mock report the same
        # run timestamps (and don't record a "new" run on every sync).
        now = datetime.utcnow().replace(minute=0, second=0, microsecond=0)
        return {
            "PAYRDLY1": {
                "job_name": "PAYRDLY1",
                "job_id": "JOB12345",
                "owner": "PAYROLL_TEAM",
                "job_class": "A",
                "description": "Daily payroll extract and GL posting",
                "status": "ACTIVE",
                "last_run": now - timedelta(hours=10),
                "next_run": now + timedelta(hours=14),
                "return_code": "CC 0000",
                "schedule": {
                    "scheduler_system": "CA-7",
                    "schedule_name": "PAYROLL-DAILY",
                    "frequency": "DAILY",
                    "run_time": "01:00",
                    "calendar": "BANKDAY",
                },
                "files": [
                    {
                        "dd_name": "EMPIN",
                        "dataset_name": "PROD.PAYROLL.EMPLOYEE.MASTER",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "VSAM",
                        "volume_serial": "PRD001",
                    },
                    {
                        "dd_name": "TIMEIN",
                        "dataset_name": "PROD.PAYROLL.TIMECARDS.DAILY",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD002",
                    },
                    {
                        "dd_name": "GLOUT",
                        "dataset_name": "PROD.PAYROLL.GL.EXTRACT",
                        "disposition": "NEW,CATLG,DELETE",
                        "direction": "OUTPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD003",
                    },
                ],
            },
            "BILLMTH2": {
                "job_name": "BILLMTH2",
                "job_id": "JOB12678",
                "owner": "BILLING_TEAM",
                "job_class": "B",
                "description": "Month-end billing statement generation",
                "status": "ACTIVE",
                "last_run": now - timedelta(days=3),
                "next_run": now + timedelta(days=27),
                "return_code": "CC 0000",
                "schedule": {
                    "scheduler_system": "Control-M",
                    "schedule_name": "BILLING-MONTHEND",
                    "frequency": "MONTHLY",
                    "run_time": "23:30",
                    "calendar": "MONTHEND",
                },
                "files": [
                    {
                        "dd_name": "ACCTIN",
                        "dataset_name": "PROD.BILLING.ACCOUNT.MASTER",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "VSAM",
                        "volume_serial": "PRD010",
                    },
                    {
                        "dd_name": "RATEIN",
                        "dataset_name": "PROD.BILLING.RATE.TABLE",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD011",
                    },
                    {
                        "dd_name": "STMTOUT",
                        "dataset_name": "PROD.BILLING.STATEMENTS.GDG",
                        "disposition": "NEW,CATLG,DELETE",
                        "direction": "OUTPUT",
                        "dataset_type": "GDG",
                        "volume_serial": "PRD012",
                    },
                ],
            },
            "INVRECON": {
                "job_name": "INVRECON",
                "job_id": "JOB13011",
                "owner": "INVENTORY_TEAM",
                "job_class": "C",
                "description": "Nightly inventory reconciliation batch",
                "status": "FAILED",
                "last_run": now - timedelta(hours=8),
                "next_run": now + timedelta(hours=16),
                "return_code": "CC 0012",
                "schedule": {
                    "scheduler_system": "OPC/TWS",
                    "schedule_name": "INV-NIGHTLY",
                    "frequency": "DAILY",
                    "run_time": "02:15",
                    "calendar": "DAILY",
                },
                "files": [
                    {
                        "dd_name": "WHSEIN",
                        "dataset_name": "PROD.INVENTORY.WAREHOUSE.MASTER",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "VSAM",
                        "volume_serial": "PRD020",
                    },
                    {
                        "dd_name": "POSIN",
                        "dataset_name": "PROD.INVENTORY.POS.FEED",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD021",
                    },
                    {
                        "dd_name": "RECONOUT",
                        "dataset_name": "PROD.INVENTORY.RECON.REPORT",
                        "disposition": "NEW,CATLG,DELETE",
                        "direction": "OUTPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD022",
                    },
                    {
                        "dd_name": "SYSOUT",
                        "dataset_name": "PROD.INVENTORY.RECON.SYSOUT",
                        "disposition": "MOD",
                        "direction": "OUTPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD023",
                    },
                ],
            },
            # Teradata load jobs: JCL that runs BTEQ / FastLoad / MultiLoad to move
            # mainframe datasets into Teradata tables. Files with
            # dataset_type="TERADATA" are the Teradata tables the job writes.
            "TDGLLOAD": {
                "job_name": "TDGLLOAD",
                "job_id": "JOB13102",
                "owner": "FINANCE_DW_TEAM",
                "job_class": "T",
                "description": (
                    "FastLoad payroll GL extract into Teradata, then BTEQ merge to GL_POSTINGS"
                ),
                "status": "ACTIVE",
                "last_run": now - timedelta(hours=9),
                "next_run": now + timedelta(hours=15),
                "return_code": "CC 0000",
                "schedule": {
                    "scheduler_system": "CA-7",
                    "schedule_name": "PAYROLL-DAILY",
                    "frequency": "DAILY",
                    "run_time": "02:00",
                    "calendar": "BANKDAY",
                },
                "files": [
                    {
                        "dd_name": "GLIN",
                        "dataset_name": "PROD.PAYROLL.GL.EXTRACT",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD003",
                    },
                    {
                        "dd_name": "TDSTG",
                        "dataset_name": "FIN_STG.GL_EXTRACT_STG",
                        "direction": "OUTPUT",
                        "dataset_type": "TERADATA",
                    },
                    {
                        "dd_name": "TDTGT",
                        "dataset_name": "FINANCE_DB.GL_POSTINGS",
                        "direction": "OUTPUT",
                        "dataset_type": "TERADATA",
                    },
                ],
            },
            "TDINVMLD": {
                "job_name": "TDINVMLD",
                "job_id": "JOB13140",
                "owner": "INVENTORY_TEAM",
                "job_class": "T",
                "description": "MultiLoad inventory reconciliation report into Teradata",
                "status": "ACTIVE",
                "last_run": now - timedelta(days=1, hours=7),
                "next_run": now + timedelta(hours=17),
                "return_code": "CC 0000",
                "schedule": {
                    "scheduler_system": "OPC/TWS",
                    "schedule_name": "INV-NIGHTLY",
                    "frequency": "DAILY",
                    "run_time": "03:00",
                    "calendar": "DAILY",
                },
                "files": [
                    {
                        "dd_name": "RECONIN",
                        "dataset_name": "PROD.INVENTORY.RECON.REPORT",
                        "disposition": "SHR",
                        "direction": "INPUT",
                        "dataset_type": "PS",
                        "volume_serial": "PRD022",
                    },
                    {
                        "dd_name": "TDTGT",
                        "dataset_name": "INV_DB.INVENTORY_RECON",
                        "direction": "OUTPUT",
                        "dataset_type": "TERADATA",
                    },
                ],
            },
        }
