"""File-based job lineage connector (CSV input files).

Lets the Job Lineage UI run from hand-made input files when there is no
access to production schedulers or metadata, e.g. for demos. The files live
in one directory (``settings.lineage_data_dir``)::

    platforms.csv                 one row per platform (see src/catalog/platforms.py)
    <folder>/jobs.csv             one row per job
    <folder>/job_datasets.csv     one row per dataset/table a job reads or writes
    <folder>/table_columns.csv    optional: columns of each dataset/table
    <folder>/column_lineage.csv   optional: source column -> target column per job

``graphs.csv`` / ``graph_datasets.csv`` with ``graph_name`` are accepted in place
of ``jobs.csv`` / ``job_datasets.csv`` with ``job_name`` (the Ab Initio folder).

See ``docs/JOB_LINEAGE_DEMO_DATA.md`` for the columns. Timestamps accept ISO
format (``2026-10-07T01:00``) or an offset from now (``-9h``, ``+15h``,
``-2d``, ``+30m``) so a demo always looks current.
"""

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from src.catalog.platforms import DEFAULT_PLATFORMS, PLATFORMS_FILE
from src.connectors.base_lineage import BaseLineageConnector

JOBS_FILES = ("jobs.csv", "graphs.csv")  # per platform folder
TABLE_COLUMNS = "table_columns.csv"
COLUMN_LINEAGE = "column_lineage.csv"
PORT_COLUMNS = ("port", "dd_name", "step")  # whichever the datasets file uses

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
                "port": next((row[c] for c in PORT_COLUMNS if row.get(c)), None),
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


def _first_existing(base: Path, folder: str, names: Sequence[str]) -> Optional[str]:
    for name in names:
        if (base / folder / name).is_file():
            return f"{folder}/{name}"
    return None


def has_lineage_files(data_dir: str) -> bool:
    """True when ``data_dir`` holds input files (so they should be used)."""
    base = Path(data_dir)
    if (base / PLATFORMS_FILE).is_file():
        return True
    return any(
        _first_existing(base, p.folder, JOBS_FILES) for p in DEFAULT_PLATFORMS
    )


class CsvLineageConnector(BaseLineageConnector):
    """Jobs, datasets, columns and column mappings of one platform, from CSV files.

    Reads ``<data_dir>/<folder>/``: ``jobs.csv`` + ``job_datasets.csv`` (key column
    ``job_name``), or the Ab Initio naming ``graphs.csv`` + ``graph_datasets.csv``
    (``graph_name``); plus the optional ``table_columns.csv`` and ``column_lineage.csv``.
    """

    def __init__(self, data_dir: str, folder: str):
        self.data_dir = Path(data_dir)
        self.folder = folder
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._columns: List[Dict[str, Any]] = []
        self._connected = False

    def connect(self) -> None:
        jobs_file = _first_existing(self.data_dir, self.folder, JOBS_FILES)
        if jobs_file is None:
            raise LineageFileError(
                f"{self.data_dir / self.folder}: no jobs file (expected jobs.csv)"
            )
        uses_graphs = jobs_file.endswith("graphs.csv")
        name_col = "graph_name" if uses_graphs else "job_name"
        datasets_name = "graph_datasets.csv" if uses_graphs else "job_datasets.csv"
        datasets_file = f"{self.folder}/{datasets_name}"
        required = (name_col, "scheduler_system", "schedule_name", "last_run_status")

        self._jobs = _load(self.data_dir, jobs_file, datasets_file, name_col, required)
        _load_column_lineage(self.data_dir / self.folder / COLUMN_LINEAGE, self._jobs, name_col)
        self._columns = _load_table_columns(self.data_dir / self.folder / TABLE_COLUMNS)
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def is_connected(self) -> bool:
        return self._connected

    def _get(self, job_name: str) -> Dict[str, Any]:
        if job_name not in self._jobs:
            raise KeyError(f"Unknown job: {job_name}")
        return self._jobs[job_name]

    def get_jobs(self) -> List[str]:
        return list(self._jobs)

    def get_job_details(self, job_name: str) -> Dict[str, Any]:
        job = self._get(job_name)
        return {
            "name": job_name,
            "owner": job.get("owner") or None,
            "description": job.get("description") or None,
            "job_class": job.get("job_class") or None,
            "last_run_status": job["last_run_status"],
            "last_run": job["last_run"],
            "next_run": job["next_run"],
            "duration_seconds": job["duration_seconds"],
            # Mainframe files say return_code, the others error_message.
            "error_message": job.get("error_message") or job.get("return_code") or None,
            "expected_completion": job["expected_completion"],
            "scheduler_system": job.get("scheduler_system") or None,
            "schedule_name": job.get("schedule_name") or None,
            "frequency": job.get("frequency") or None,
        }

    def get_job_datasets(self, job_name: str) -> List[Dict[str, Any]]:
        return self._get(job_name)["datasets"]

    def get_table_columns(self) -> List[Dict[str, Any]]:
        return self._columns

    def get_job_column_lineage(self, job_name: str) -> List[Dict[str, Any]]:
        return self._get(job_name)["column_mappings"]
