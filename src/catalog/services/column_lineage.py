"""Column-level lineage and column search for one platform.

Columns come from two places, merged:

* ``DatasetColumn``: the column list of each table/dataset;
* ``ColumnLineage``: per-job mappings ``source table.column -> target table.column``
  (any column named in a mapping exists even if it is not in the column list).

A column's node id is ``<dataset node id>::<COLUMN>``, e.g.
``dataset:CARDS_DB.CARD_TRANSACTIONS::CUSTOMER_ID``. Column names match
case-insensitively. Table facts (database, load jobs, failure impact, SLA)
come from the platform's job lineage graph so both views always agree.
"""

from collections import deque
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from src.catalog.models import ColumnLineage, DatasetColumn, Job
from src.catalog.services.job_lineage import (
    DIRECTIONS,
    JobLineageService,
    database_of,
    dataset_node_id,
    job_node_id,
)

COLUMN_SEPARATOR = "::"


def column_node_id(dataset_name: str, column_name: str) -> str:
    return f"{dataset_node_id(dataset_name)}{COLUMN_SEPARATOR}{column_name.strip().upper()}"


def _job_ref(job: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": job["id"],
        "name": job["name"],
        "run_status": job["run_status"],
        "last_run": job["last_run"],
        "sla_status": job["sla"]["status"] if job.get("sla") else None,
    }


class ColumnLineageService:
    """Column search and column-level lineage built on the job lineage graph."""

    def __init__(self, db: Session):
        self.db = db
        self.job_lineage = JobLineageService(db)

    def _load(self, platform: str) -> Tuple[Dict, List, Dict, List]:
        nodes, edges = self.job_lineage._load(platform)
        columns: Dict[str, Dict[str, Any]] = {}

        def add(dataset: str, column: str, data_type=None, description=None, position=None):
            cid = column_node_id(dataset, column)
            existing = columns.get(cid)
            if existing:
                existing["data_type"] = existing["data_type"] or data_type
                existing["description"] = existing["description"] or description
                return cid
            did = dataset_node_id(dataset)
            table = nodes.get(did, {})
            columns[cid] = {
                "id": cid,
                "type": "column",
                "column": column.strip(),
                "dataset_id": did,
                "dataset_name": table.get("name", dataset.strip()),
                "dataset_type": table.get("dataset_type"),
                "platform": table.get("platform"),
                "database": table.get("database") or database_of(dataset, None),
                "data_type": data_type,
                "description": description,
                "position": position,
                "impacted": table.get("impacted", False),
                "impacted_by": table.get("impacted_by", []),
            }
            return cid

        listed = (
            self.db.query(DatasetColumn)
            .filter(DatasetColumn.source_system == platform)
            .order_by(DatasetColumn.position)
        )
        for c in listed:
            add(c.dataset_name, c.column_name, c.data_type, c.description, c.position)

        mappings = (
            self.db.query(ColumnLineage)
            .join(Job)
            .filter(Job.source_system == platform)
            .order_by(ColumnLineage.id)
        )
        column_edges = []
        for m in mappings:
            source = add(m.source_dataset, m.source_column)
            target = add(m.target_dataset, m.target_column)
            job = nodes[job_node_id(m.job_id)]
            column_edges.append(
                {
                    "id": f"{source}->{target}@{job['id']}",
                    "source": source,
                    "target": target,
                    "job_id": job["id"],
                    "job_name": job["name"],
                    "run_status": job["run_status"],
                    "transformation": m.transformation,
                }
            )
        return nodes, edges, columns, column_edges

    @staticmethod
    def _table_jobs(nodes, edges, dataset_id: str) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "loaded_by": [_job_ref(nodes[e["source"]]) for e in edges if e["target"] == dataset_id],
            "read_by": [_job_ref(nodes[e["target"]]) for e in edges if e["source"] == dataset_id],
        }

    def search_columns(
        self, platform: str, query: str, exact: bool = False, limit: int = 200
    ) -> List[Dict[str, Any]]:
        """Every table that has a column matching ``query``, with its load jobs.

        ``exact`` matches the whole column name; otherwise any part of it.
        Results: exact name matches first, then by column and table name.
        """
        nodes, edges, columns, column_edges = self._load(platform)
        needle = query.strip().lower()
        if not needle:
            return []
        matches = [
            c for c in columns.values()
            if (c["column"].lower() == needle if exact else needle in c["column"].lower())
        ]
        matches.sort(
            key=lambda c: (c["column"].lower() != needle, c["column"].lower(), c["dataset_name"])
        )
        results = []
        for c in matches[:limit]:
            results.append(
                {
                    **c,
                    **self._table_jobs(nodes, edges, c["dataset_id"]),
                    "upstream_columns": sum(1 for e in column_edges if e["target"] == c["id"]),
                    "downstream_columns": sum(1 for e in column_edges if e["source"] == c["id"]),
                }
            )
        return results

    def list_table_columns(self, platform: str, dataset_id: str) -> List[Dict[str, Any]]:
        """Columns of one table/dataset, in file order, then mapped-only columns by name."""
        _, _, columns, column_edges = self._load(platform)
        found = [c for c in columns.values() if c["dataset_id"] == dataset_id]
        found.sort(key=lambda c: (c["position"] is None, c["position"] or 0, c["column"]))
        return [
            {
                **c,
                "upstream_columns": sum(1 for e in column_edges if e["target"] == c["id"]),
                "downstream_columns": sum(1 for e in column_edges if e["source"] == c["id"]),
            }
            for c in found
        ]

    def get_column_lineage(
        self,
        platform: str,
        column_id: str,
        direction: str = "both",
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Columns feeding into and fed by ``column_id``, through job mappings.

        ``depth`` counts jobs (one mapping is one level). Raises ``ValueError``
        for a bad direction and ``KeyError`` for an unknown column.
        """
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        nodes, edges, columns, column_edges = self._load(platform)
        if column_id not in columns:
            raise KeyError(column_id)

        def walk(forward: bool) -> Dict[str, int]:
            dist = {column_id: 0}
            queue = deque([column_id])
            while queue:
                current = queue.popleft()
                if depth is not None and dist[current] >= depth:
                    continue
                for e in column_edges:
                    a, b = (e["source"], e["target"]) if forward else (e["target"], e["source"])
                    if a == current and b not in dist:
                        dist[b] = dist[current] + 1
                        queue.append(b)
            return dist

        keep = {column_id}
        if direction in ("upstream", "both"):
            keep |= walk(forward=False).keys()
        if direction in ("downstream", "both"):
            keep |= walk(forward=True).keys()

        focus = columns[column_id]
        return {
            "focus": {**focus, **self._table_jobs(nodes, edges, focus["dataset_id"])},
            "nodes": [columns[cid] for cid in columns if cid in keep],
            "edges": [e for e in column_edges if e["source"] in keep and e["target"] in keep],
        }
