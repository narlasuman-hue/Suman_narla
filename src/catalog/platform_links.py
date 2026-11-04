"""Hand-offs between platforms, for the All platforms lineage view.

Each platform's lineage is built from its own jobs. Data often moves between
platforms under a different name: a mainframe extract ``PROD.CARDS.TXN.DAILY``
is sent by NDM and lands on Hadoop as ``/data/landing/cards/auth_feed``.
``platform_links.csv`` in the lineage data folder records each hand-off::

    source_dataset,target_dataset,method,description
    PROD.CARDS.TXN.DAILY,/data/landing/cards/auth_feed,NDM file transfer,Card transactions to Hadoop

In the All platforms view the target is the same dataset as the source, so the
jobs on both sides join up. Datasets with the same name on two platforms join
without a link. Single-platform views ignore this file. Without the file there
are no links.
"""

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

PLATFORM_LINKS_FILE = "platform_links.csv"
REQUIRED_COLUMNS = ("source_dataset", "target_dataset")


class PlatformLinkError(ValueError):
    """``platform_links.csv`` is missing columns or has an invalid row."""


@dataclass(frozen=True)
class PlatformLink:
    source_dataset: str
    target_dataset: str
    method: str = ""
    description: str = ""


def read_platform_links_file(path: Path) -> List[PlatformLink]:
    """Parse and validate a ``platform_links.csv``."""
    # Local import: dataset ids are defined with the lineage graph.
    from src.catalog.services.job_lineage import dataset_node_id

    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = [h.strip() for h in reader.fieldnames or []]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            raise PlatformLinkError(f"{path}: missing column(s) {', '.join(missing)}")

        links: List[PlatformLink] = []
        targets = set()
        for line, raw in enumerate(reader, start=2):
            row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
            if not any(row.values()):
                continue

            def fail(message: str) -> PlatformLinkError:
                return PlatformLinkError(f"{path} line {line}: {message}")

            source, target = row["source_dataset"], row["target_dataset"]
            if not source:
                raise fail("source_dataset is empty")
            if not target:
                raise fail("target_dataset is empty")
            if dataset_node_id(source) == dataset_node_id(target):
                raise fail(f"links a dataset to itself ('{source}')")
            if dataset_node_id(target) in targets:
                raise fail(f"target_dataset '{target}' is already linked")
            targets.add(dataset_node_id(target))
            links.append(
                PlatformLink(
                    source_dataset=source,
                    target_dataset=target,
                    method=row.get("method", ""),
                    description=row.get("description", ""),
                )
            )
    return links


def load_platform_links(data_dir: Optional[str] = None) -> List[PlatformLink]:
    """Links from ``<data_dir>/platform_links.csv``; none without the file."""
    if data_dir is None:
        from src.config import settings  # late import: keep this module import-light

        data_dir = settings.lineage_data_dir
    path = Path(data_dir) / PLATFORM_LINKS_FILE
    return read_platform_links_file(path) if path.is_file() else []
