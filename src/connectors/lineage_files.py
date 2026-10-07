"""File-based job lineage connectors (CSV input files).

Lets the Job Lineage UI run from hand-made input files when there is no
access to the production mainframe scheduler or Ab Initio metadata, e.g.
for demos. The files live in one directory (``settings.lineage_data_dir``)::

    mainframe/jobs.csv            one row per mainframe job
    mainframe/job_datasets.csv    one row per dataset/table a job reads or writes
    abinitio/graphs.csv           one row per Ab Initio graph
    abinitio/graph_datasets.csv   one row per dataset/table a graph reads or writes

See ``docs/JOB_LINEAGE_DEMO_DATA.md`` for the columns. Timestamps accept ISO
format (``2026-10-07T01:00``) or an offset from now (``-9h``, ``+15h``,
``-2d``, ``+30m``) so a demo always looks current.
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.connectors.abinitio import BaseAbInitioConnector
from src.connectors.mainframe import BaseMainframeConnector

MAINFRAME_JOBS = "mainframe/jobs.csv"
MAINFRAME_DATASETS = "mainframe/job_datasets.csv"
ABINITIO_GRAPHS = "abinitio/graphs.csv"
ABINITIO_DATASETS = "abinitio/graph_datasets.csv"

RUN_STATUSES = ("SUCCESS", "FAILED", "RUNNING")
DIRECTIONS = ("INPUT", "OUTPUT", "INOUT")

_OFFSET = re.compile(r"^([+-])(\d+)([mhd])$")
_UNITS = {"m": "minutes", "h": "hours", "d": "days"}


class LineageFileError(ValueError):
    """An input file is missing or has invalid content."""


def parse_time(value: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Parse an ISO timestamp or a relative offset such as ``-9h``; blank -> None."""
    value = (value or "").strip()
    if not value:
        return None
    match = _OFFSET.match(value)
    if match:
        sign, amount, unit = match.groups()
        base = now or datetime.utcnow().replace(second=0, microsecond=0)
        delta = timedelta(**{_UNITS[unit]: int(amount)})
        return base + delta if sign == "+" else base - delta
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(f"invalid time '{value}' (use ISO like 2026-10-07T01:00, or -9h / +15h)")


def _read_csv(path: Path, required: Sequence[str]) -> List[Dict[str, str]]:
    if not path.is_file():
        raise LineageFileError(f"{path}: file not found")
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames or []]
        missing = [c for c in required if c not in headers]
        if missing:
            raise LineageFileError(f"{path}: missing column(s) {', '.join(missing)}")
        rows = []
        for row in reader:
            clean = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
            if any(clean.values()):  # skip blank lines
                rows.append(clean)
        return rows


def _choice(path: Path, line: int, column: str, value: str, allowed: Sequence[str]) -> str:
    value = value.upper()
    if value not in allowed:
        raise LineageFileError(
            f"{path} line {line}: {column} '{value}' must be one of {', '.join(allowed)}"
        )
    return value


def _load(
    base: Path,
    jobs_file: str,
    datasets_file: str,
    name_col: str,
    job_columns: Sequence[str],
    port_col: str,
) -> Dict[str, Dict[str, Any]]:
    """Load a jobs file and its datasets file into ``{name: job_dict}``."""
    jobs_path, ds_path = base / jobs_file, base / datasets_file
    now = datetime.utcnow().replace(second=0, microsecond=0)

    jobs: Dict[str, Dict[str, Any]] = {}
    for line, row in enumerate(_read_csv(jobs_path, job_columns), start=2):
        name = row[name_col]
        if not name:
            raise LineageFileError(f"{jobs_path} line {line}: {name_col} is empty")
        if name in jobs:
            raise LineageFileError(f"{jobs_path} line {line}: duplicate {name_col} '{name}'")
        try:
            last_run = parse_time(row.get("last_run", ""), now)
            next_run = parse_time(row.get("next_run", ""), now)
        except ValueError as e:
            raise LineageFileError(f"{jobs_path} line {line}: {e}")
        status = _choice(
            jobs_path, line, "last_run_status", row.get("last_run_status") or "SUCCESS",
            RUN_STATUSES,
        )
        duration = row.get("duration_seconds", "")
        if duration and not duration.isdigit():
            raise LineageFileError(f"{jobs_path} line {line}: duration_seconds must be a number")
        jobs[name] = {
            **row,
            "last_run": last_run,
            "next_run": next_run,
            "last_run_status": status,
            "duration_seconds": int(duration) if duration else None,
            "datasets": [],
        }

    ds_columns = (name_col, "dataset_name", "direction", "dataset_type")
    for line, row in enumerate(_read_csv(ds_path, ds_columns), start=2):
        job = jobs.get(row[name_col])
        if job is None:
            raise LineageFileError(
                f"{ds_path} line {line}: {name_col} '{row[name_col]}' is not in {jobs_file}"
            )
        if not row["dataset_name"]:
            raise LineageFileError(f"{ds_path} line {line}: dataset_name is empty")
        job["datasets"].append(
            {
                "port": row.get(port_col) or None,
                "dataset_name": row["dataset_name"],
                "direction": _choice(ds_path, line, "direction", row["direction"], DIRECTIONS),
                "dataset_type": row["dataset_type"].upper() or None,
                "disposition": row.get("disposition") or None,
            }
        )
    return jobs


def has_lineage_files(data_dir: str) -> bool:
    """True when ``data_dir`` holds the input files (so they should be used)."""
    base = Path(data_dir)
    return (base / MAINFRAME_JOBS).is_file() or (base / ABINITIO_GRAPHS).is_file()


class CsvMainframeConnector(BaseMainframeConnector):
    """Mainframe jobs (including Teradata load jobs) read from CSV files."""

    JOB_COLUMNS = ("job_name", "scheduler_system", "schedule_name", "last_run_status")

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._connected = False

    def connect(self) -> None:
        self._jobs = _load(
            self.data_dir, MAINFRAME_JOBS, MAINFRAME_DATASETS, "job_name",
            self.JOB_COLUMNS, "dd_name",
        )
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _get(self, job_name: str) -> Dict[str, Any]:
        if job_name not in self._jobs:
            raise KeyError(f"Unknown mainframe job: {job_name}")
        return self._jobs[job_name]

    def get_jobs(self) -> List[Dict[str, Any]]:
        return [{"job_name": name} for name in self._jobs]

    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        job = self._get(job_name)
        return {
            "job_name": job_name,
            "owner": job.get("owner") or None,
            "job_class": job.get("job_class") or None,
            "description": job.get("description") or None,
            "status": job["last_run_status"],
            "last_run_status": job["last_run_status"],
            "last_run": job["last_run"],
            "next_run": job["next_run"],
            "return_code": job.get("return_code") or None,
            "duration_seconds": job["duration_seconds"],
        }

    def get_job_files(self, job_name: str) -> List[Dict[str, Any]]:
        return [
            {**{k: v for k, v in ds.items() if k != "port"}, "dd_name": ds["port"]}
            for ds in self._get(job_name)["datasets"]
        ]

    def get_job_schedule(self, job_name: str) -> Dict[str, Any]:
        job = self._get(job_name)
        return {
            "scheduler_system": job.get("scheduler_system") or None,
            "schedule_name": job.get("schedule_name") or None,
            "frequency": job.get("frequency") or None,
        }


class CsvAbInitioConnector(BaseAbInitioConnector):
    """Ab Initio graphs (loading Hadoop tables) read from CSV files."""

    JOB_COLUMNS = ("graph_name", "scheduler_system", "schedule_name", "last_run_status")

    def __init__(self, data_dir: str):
        self.data_dir = Path(data_dir)
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._connected = False

    def connect(self) -> None:
        self._graphs = _load(
            self.data_dir, ABINITIO_GRAPHS, ABINITIO_DATASETS, "graph_name",
            self.JOB_COLUMNS, "port",
        )
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _get(self, graph_name: str) -> Dict[str, Any]:
        if graph_name not in self._graphs:
            raise KeyError(f"Unknown Ab Initio graph: {graph_name}")
        return self._graphs[graph_name]

    def get_graphs(self) -> List[Dict[str, Any]]:
        return [{"graph_name": name} for name in self._graphs]

    def get_graph_details(self, graph_name: str) -> Dict[str, Any]:
        graph = self._get(graph_name)
        return {
            "graph_name": graph_name,
            "project": graph.get("project") or None,
            "owner": graph.get("owner") or None,
            "description": graph.get("description") or None,
            "last_run_status": graph["last_run_status"],
            "last_run": graph["last_run"],
            "next_run": graph["next_run"],
            "duration_seconds": graph["duration_seconds"],
            "error_message": graph.get("error_message") or None,
        }

    def get_graph_datasets(self, graph_name: str) -> List[Dict[str, Any]]:
        return self._get(graph_name)["datasets"]

    def get_graph_schedule(self, graph_name: str) -> Dict[str, Any]:
        graph = self._get(graph_name)
        return {
            "scheduler_system": graph.get("scheduler_system") or None,
            "schedule_name": graph.get("schedule_name") or None,
            "frequency": graph.get("frequency") or None,
        }
