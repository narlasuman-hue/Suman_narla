"""Lineage platforms: which job/scheduler worlds the Job Lineage UI shows.

A platform is one independent world of jobs and the tables they load, e.g.
"Mainframe → Teradata" or "Airflow → Snowflake". Platforms are configured,
not coded: ``platforms.csv`` in the lineage data folder has one row each::

    platform_id,folder,name,description,job_label,table_label,table_types,color
    MAINFRAME,mainframe,Mainframe → Teradata,Mainframe jobs loading Teradata tables,
        Mainframe job,Teradata table,TERADATA,#c2410c

* ``platform_id``: stored on every job (``Job.source_system``) and used by the API.
* ``folder``: sub-folder holding the platform's CSV files; also its URL key.
* ``table_types``: ``dataset_type`` values (``;``-separated) that are this
  platform's *tables*: what its jobs load. Every other dataset is a source
  file or input. A job that writes a table is a "load" job.
* ``color``: hex color for the platform's load jobs and tables in the UI.

Without a ``platforms.csv`` the two original platforms are used.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

PLATFORMS_FILE = "platforms.csv"
REQUIRED_COLUMNS = ("platform_id", "folder", "name", "table_types")

_ID = re.compile(r"^[A-Z][A-Z0-9_]{0,49}$")
_FOLDER = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


class PlatformConfigError(ValueError):
    """``platforms.csv`` is missing columns or has an invalid row."""


@dataclass(frozen=True)
class Platform:
    id: str
    folder: str
    name: str
    description: str = ""
    job_label: str = "Job"
    table_label: str = "Table"
    table_types: FrozenSet[str] = field(default_factory=frozenset)
    color: str = "#4338ca"

    def is_table(self, dataset_type: Optional[str]) -> bool:
        return (dataset_type or "").upper() in self.table_types

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id,
            "key": self.folder,
            "name": self.name,
            "description": self.description,
            "job_label": self.job_label,
            "table_label": self.table_label,
            "table_types": sorted(self.table_types),
            "color": self.color,
        }


DEFAULT_PLATFORMS: List[Platform] = [
    Platform(
        id="MAINFRAME",
        folder="mainframe",
        name="Mainframe → Teradata",
        description="Mainframe jobs loading Teradata tables",
        job_label="Mainframe job",
        table_label="Teradata table",
        table_types=frozenset({"TERADATA"}),
        color="#c2410c",
    ),
    Platform(
        id="HADOOP_ABINITIO",
        folder="abinitio",
        name="Ab Initio → Hadoop",
        description="Ab Initio graphs loading Hadoop tables",
        job_label="Ab Initio graph",
        table_label="Hadoop table",
        table_types=frozenset({"HIVE", "HDFS"}),
        color="#0f766e",
    ),
]


def read_platforms_file(path: Path) -> List[Platform]:
    """Parse and validate a ``platforms.csv``."""
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames or []]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise PlatformConfigError(f"{path}: missing column(s) {', '.join(missing)}")

        platforms: List[Platform] = []
        for line, raw in enumerate(reader, start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            if not any(row.values()):
                continue

            def fail(message: str) -> PlatformConfigError:
                return PlatformConfigError(f"{path} line {line}: {message}")

            pid, folder = row["platform_id"].upper(), row["folder"].lower()
            if not _ID.match(pid):
                raise fail(f"platform_id '{row['platform_id']}' must be letters, digits or _")
            if not _FOLDER.match(folder):
                raise fail(f"folder '{row['folder']}' must be lower-case letters, digits, - or _")
            if any(p.id == pid for p in platforms):
                raise fail(f"duplicate platform_id '{pid}'")
            if any(p.folder == folder for p in platforms):
                raise fail(f"duplicate folder '{folder}'")
            if not row["name"]:
                raise fail("name is empty")
            table_types = frozenset(
                t.strip().upper() for t in row["table_types"].split(";") if t.strip()
            )
            if not table_types:
                raise fail("table_types is empty (e.g. TERADATA, or HIVE;HDFS)")
            color = row.get("color") or "#4338ca"
            if not _COLOR.match(color):
                raise fail(f"color '{color}' must be a hex color like #c2410c")

            platforms.append(
                Platform(
                    id=pid,
                    folder=folder,
                    name=row["name"],
                    description=row.get("description", ""),
                    job_label=row.get("job_label") or "Job",
                    table_label=row.get("table_label") or "Table",
                    table_types=table_types,
                    color=color,
                )
            )
    if not platforms:
        raise PlatformConfigError(f"{path}: no platforms defined")
    return platforms


def load_platforms(data_dir: Optional[str] = None) -> List[Platform]:
    """Platforms from ``<data_dir>/platforms.csv``, or the two defaults without one."""
    if data_dir is None:
        from src.config import settings  # late import: keep this module import-light

        data_dir = settings.lineage_data_dir
    path = Path(data_dir) / PLATFORMS_FILE
    return read_platforms_file(path) if path.is_file() else list(DEFAULT_PLATFORMS)


def get_platform(platform_id: str, data_dir: Optional[str] = None) -> Platform:
    """The configured platform with this id; ``ValueError`` if there is none."""
    for platform in load_platforms(data_dir):
        if platform.id == platform_id:
            return platform
    raise ValueError(f"Unknown platform: {platform_id}")
