"""File-based job lineage connectors (CSV input files).

Lets the Job Lineage UI run from hand-made input files when there is no
access to the production mainframe scheduler or Ab Initio metadata, e.g.
for demos. The files live in one directory (``settings.lineage_data_dir``)::

    mainframe/jobs.csv            one row per mainframe job
    mainframe/job_datasets.csv    one row per dataset/table a job reads or writes
    mainframe/table_columns.csv   optional: columns of each dataset/table
    mainframe/column_lineage.csv  optional: source column -> target column per job
    abinitio/graphs.csv           one row per Ab Initio graph
    abinitio/graph_datasets.csv   one row per dataset/table a graph reads or writes
    abinitio/table_columns.csv    optional: columns of each dataset/table
    abinitio/column_lineage.csv   optional: source column -> target column per graph

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
TABLE_COLUMNS = "table_columns.csv"  # under mainframe/ or abinitio/
COLUMN_LINEAGE = "column_lineage.csv"  # under mainframe/ or abinitio/

RUN_STATUSES = ("SUCCESS", "FAILED", "RUNNING")
DIRECTIONS = ("INPUT", "OUTPUT", "INOUT")

_OFFSET = re.compile(r"^([+-])(\d+)([mhd])$")
_CLOCK = re.compile(r"^(\d{1,2}):(\d{2})$")
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


def parse_deadline(value: str, now: Optional[datetime] = None) -> Optional[datetime]:
    """Parse an SLA expected completion: ``HH:MM`` (today, UTC), an offset or ISO."""
    match = _CLOCK.match((value or "").strip())
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour > 23 or minute > 59:
            raise ValueError(f"invalid time '{value}' (HH:MM must be 00:00-23:59)")
        base = now or datetime.utcnow()
        return base.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return parse_time(value, now)


def _dataset_key(name: str) -> str:
    """Same matching rule as the lineage graph: HDFS paths exact, others case-insensitive."""
    name = name.strip()
    return name if name.startswith("/") or "://" in name else name.upper()


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
            expected_completion = parse_deadline(row.get("expected_completion", ""), now)
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
            "expected_completion": expected_completion,
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


def _load_table_columns(path: Path) -> List[Dict[str, Any]]:
    """Optional ``table_columns.csv``; missing file -> no columns."""
    if not path.is_file():
        return []
    columns, seen = [], set()
    for line, row in enumerate(_read_csv(path, ("dataset_name", "column_name")), start=2):
        if not row["dataset_name"] or not row["column_name"]:
            raise LineageFileError(f"{path} line {line}: dataset_name and column_name are required")
        key = (_dataset_key(row["dataset_name"]), row["column_name"].upper())
        if key in seen:
            raise LineageFileError(
                f"{path} line {line}: duplicate column "
                f"'{row['dataset_name']}.{row['column_name']}'"
            )
        seen.add(key)
        columns.append(
            {
                "dataset_name": row["dataset_name"],
                "column_name": row["column_name"],
                "data_type": row.get("data_type") or None,
                "description": row.get("description") or None,
            }
        )
    return columns


def _load_column_lineage(
    path: Path, jobs: Dict[str, Dict[str, Any]], name_col: str
) -> None:
    """Optional ``column_lineage.csv``: attach mappings to ``jobs[name]["column_mappings"]``.

    The source table must be one the job reads and the target one it writes
    (per the datasets file), so column lineage always agrees with table lineage.
    """
    for job in jobs.values():
        job["column_mappings"] = []
    if not path.is_file():
        return
    required = (name_col, "source_dataset", "source_column", "target_dataset", "target_column")
    for line, row in enumerate(_read_csv(path, required), start=2):
        job = jobs.get(row[name_col])
        if job is None:
            raise LineageFileError(f"{path} line {line}: {name_col} '{row[name_col]}' is unknown")
        missing = [c for c in required[1:] if not row[c]]
        if missing:
            raise LineageFileError(f"{path} line {line}: empty {', '.join(missing)}")
        reads = {_dataset_key(d["dataset_name"]) for d in job["datasets"]
                 if d["direction"] in ("INPUT", "INOUT")}
        writes = {_dataset_key(d["dataset_name"]) for d in job["datasets"]
                  if d["direction"] in ("OUTPUT", "INOUT")}
        if _dataset_key(row["source_dataset"]) not in reads:
            raise LineageFileError(
                f"{path} line {line}: {row[name_col]} does not read "
                f"'{row['source_dataset']}' (add it as INPUT in the datasets file)"
            )
        if _dataset_key(row["target_dataset"]) not in writes:
            raise LineageFileError(
                f"{path} line {line}: {row[name_col]} does not write "
                f"'{row['target_dataset']}' (add it as OUTPUT in the datasets file)"
            )
        job["column_mappings"].append(
            {
                "source_dataset": row["source_dataset"],
                "source_column": row["source_column"],
                "target_dataset": row["target_dataset"],
                "target_column": row["target_column"],
                "transformation": row.get("transformation") or None,
            }
        )


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
        self._columns: List[Dict[str, Any]] = []
        self._connected = False

    def connect(self) -> None:
        self._jobs = _load(
            self.data_dir, MAINFRAME_JOBS, MAINFRAME_DATASETS, "job_name",
            self.JOB_COLUMNS, "dd_name",
        )
        _load_column_lineage(self.data_dir / "mainframe" / COLUMN_LINEAGE, self._jobs, "job_name")
        self._columns = _load_table_columns(self.data_dir / "mainframe" / TABLE_COLUMNS)
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
            "expected_completion": job["expected_completion"],
        }

    def get_table_columns(self) -> List[Dict[str, Any]]:
        return self._columns

    def get_job_column_lineage(self, job_name: str) -> List[Dict[str, Any]]:
        return self._get(job_name)["column_mappings"]

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
        self._columns: List[Dict[str, Any]] = []
        self._connected = False

    def connect(self) -> None:
        self._graphs = _load(
            self.data_dir, ABINITIO_GRAPHS, ABINITIO_DATASETS, "graph_name",
            self.JOB_COLUMNS, "port",
        )
        _load_column_lineage(
            self.data_dir / "abinitio" / COLUMN_LINEAGE, self._graphs, "graph_name"
        )
        self._columns = _load_table_columns(self.data_dir / "abinitio" / TABLE_COLUMNS)
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
            "expected_completion": graph["expected_completion"],
        }

    def get_table_columns(self) -> List[Dict[str, Any]]:
        return self._columns

    def get_graph_column_lineage(self, graph_name: str) -> List[Dict[str, Any]]:
        return self._get(graph_name)["column_mappings"]

    def get_graph_datasets(self, graph_name: str) -> List[Dict[str, Any]]:
        return self._get(graph_name)["datasets"]

    def get_graph_schedule(self, graph_name: str) -> Dict[str, Any]:
        graph = self._get(graph_name)
        return {
            "scheduler_system": graph.get("scheduler_system") or None,
            "schedule_name": graph.get("schedule_name") or None,
            "frequency": graph.get("frequency") or None,
        }
