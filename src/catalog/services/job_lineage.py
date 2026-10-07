"""Cross-platform job lineage for mainframe/Teradata jobs and Hadoop Ab Initio graphs.

Builds a directed graph from the catalog's ``Job`` / ``JobFile`` rows:

* job nodes: mainframe JCL jobs (including Teradata BTEQ/FastLoad/MultiLoad
  load jobs) and Ab Initio graphs running on Hadoop;
* dataset nodes: mainframe datasets, Teradata tables, HDFS paths and Hive
  tables;
* edges: ``dataset -> job`` for inputs and ``job -> dataset`` for outputs.

Jobs on different platforms link up through datasets with the same name,
e.g. a mainframe FastLoad job writes ``FINANCE_DB.GL_POSTINGS`` and an Ab
Initio graph reads it. For SRE triage, every node downstream of a job whose
latest run failed is flagged as impacted (the failure's blast radius).
"""

from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session, selectinload

from src.catalog.models import Job
from src.catalog.services.job_runs import RUN_FAILED, RUN_RUNNING

PLATFORM_LABELS = {
    "MAINFRAME": "Mainframe / Teradata",
    "HADOOP_ABINITIO": "Hadoop / Ab Initio",
}
LINEAGE_PLATFORMS = tuple(PLATFORM_LABELS)
DIRECTIONS = ("upstream", "downstream", "both")

# Where a dataset lives, by dataset_type. Anything else (PS, VSAM, GDG, PDS...)
# is a mainframe dataset.
_DATASET_PLATFORM = {"TERADATA": "TERADATA", "HIVE": "HADOOP", "HDFS": "HADOOP"}

Graph = Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]


def dataset_node_id(dataset_name: str) -> str:
    """Stable node id for a dataset, shared by every job that touches it.

    HDFS paths are case-sensitive; mainframe DSNs, Teradata and Hive names
    are not, so those are upper-cased to match across systems.
    """
    name = dataset_name.strip()
    if not (name.startswith("/") or "://" in name):
        name = name.upper()
    return f"dataset:{name}"


def job_node_id(job_id: int) -> str:
    return f"job:{job_id}"


def _iso(value) -> Optional[str]:
    return value.isoformat() if value else None


def _job_type(job: Job) -> str:
    if job.source_system == "HADOOP_ABINITIO":
        return "AB_INITIO_GRAPH"
    writes_teradata = any(
        (f.dataset_type or "").upper() == "TERADATA"
        and (f.direction or "").upper() in ("OUTPUT", "INOUT")
        for f in job.files
    )
    return "TERADATA_LOAD" if writes_teradata else "JCL"


class JobLineageService:
    """Builds and queries the job/dataset lineage graph."""

    def __init__(self, db: Session):
        self.db = db

    # ---------- graph construction ----------

    def _load(self, platform: Optional[str] = None) -> Graph:
        platforms = (platform,) if platform else LINEAGE_PLATFORMS
        jobs = (
            self.db.query(Job)
            .options(selectinload(Job.files), selectinload(Job.executions))
            .filter(Job.source_system.in_(platforms))
            .order_by(Job.name)
            .all()
        )

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: Dict[str, Dict[str, Any]] = {}

        for job in jobs:
            jid = job_node_id(job.id)
            latest = max(job.executions, key=lambda e: e.start_time, default=None)
            nodes[jid] = {
                "id": jid,
                "type": "job",
                "catalog_id": job.id,
                "name": job.name,
                "platform": job.source_system,
                "platform_label": PLATFORM_LABELS[job.source_system],
                "job_type": _job_type(job),
                "owner": job.owner,
                "description": job.description,
                "scheduler_system": job.scheduler_system,
                "schedule_name": job.schedule_name,
                "frequency": job.frequency,
                "last_run": _iso(job.last_run),
                "next_run": _iso(job.next_run),
                "run_status": latest.status if latest else "UNKNOWN",
                "run_duration_seconds": latest.duration_seconds if latest else None,
                "run_error": latest.error_message if latest else None,
            }

            for f in job.files:
                did = dataset_node_id(f.dataset_name)
                dataset_type = (f.dataset_type or "").upper() or None
                nodes.setdefault(
                    did,
                    {
                        "id": did,
                        "type": "dataset",
                        "name": f.dataset_name.strip(),
                        "dataset_type": dataset_type,
                        "platform": _DATASET_PLATFORM.get(dataset_type or "", "MAINFRAME"),
                    },
                )
                direction = (f.direction or "").upper()
                if direction in ("INPUT", "INOUT"):
                    self._add_edge(edges, did, jid, f.dd_name)
                if direction in ("OUTPUT", "INOUT"):
                    self._add_edge(edges, jid, did, f.dd_name)

        self._mark_impact(nodes, list(edges.values()))
        return nodes, list(edges.values())

    @staticmethod
    def _add_edge(edges: Dict[str, Dict[str, Any]], source: str, target: str, port) -> None:
        edge_id = f"{source}->{target}"
        if edge_id not in edges:
            edges[edge_id] = {"id": edge_id, "source": source, "target": target, "port": port}

    @staticmethod
    def _adjacency(edges: Iterable[Dict[str, Any]], reverse: bool = False) -> Dict[str, List[str]]:
        adj: Dict[str, List[str]] = {}
        for e in edges:
            a, b = (e["target"], e["source"]) if reverse else (e["source"], e["target"])
            adj.setdefault(a, []).append(b)
        return adj

    @staticmethod
    def _reachable(
        start: str, adj: Dict[str, List[str]], max_hops: Optional[int] = None
    ) -> Dict[str, int]:
        """BFS from ``start``; returns ``{node_id: hops}`` excluding ``start``."""
        dist = {start: 0}
        queue = deque([start])
        while queue:
            node = queue.popleft()
            if max_hops is not None and dist[node] >= max_hops:
                continue
            for nxt in adj.get(node, []):
                if nxt not in dist:
                    dist[nxt] = dist[node] + 1
                    queue.append(nxt)
        del dist[start]
        return dist

    def _mark_impact(self, nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        adj = self._adjacency(edges)
        for node in nodes.values():
            node["impacted"] = False
            node["impacted_by"] = []
        for failed in [n for n in nodes.values() if n.get("run_status") == RUN_FAILED]:
            for nid in self._reachable(failed["id"], adj):
                nodes[nid]["impacted"] = True
                nodes[nid]["impacted_by"].append(failed["name"])

    # ---------- queries ----------

    def get_graph(
        self,
        platform: Optional[str] = None,
        focus: Optional[str] = None,
        direction: str = "both",
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return the lineage graph, optionally narrowed around a focus node.

        ``depth`` counts job levels (a job -> dataset -> job step is one level).
        Raises ``KeyError`` if ``focus`` is not in the graph.
        """
        if platform is not None and platform not in PLATFORM_LABELS:
            raise ValueError(f"Unknown platform: {platform}")
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")

        nodes, edges = self._load(platform)
        summary = self._summarize(nodes)

        if focus is not None:
            if focus not in nodes:
                raise KeyError(focus)
            max_hops = depth * 2 if depth else None
            keep = {focus}
            if direction in ("upstream", "both"):
                upstream = self._adjacency(edges, reverse=True)
                keep |= self._reachable(focus, upstream, max_hops).keys()
            if direction in ("downstream", "both"):
                keep |= self._reachable(focus, self._adjacency(edges), max_hops).keys()
            nodes = {k: v for k, v in nodes.items() if k in keep}
            edges = [e for e in edges if e["source"] in keep and e["target"] in keep]

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "summary": summary,
            "focus": focus,
        }

    def get_impact(self, node_id: str) -> Dict[str, Any]:
        """Blast radius of ``node_id`` plus upstream jobs that are failing or still running.

        Always evaluated across all platforms, since an outage on one platform
        typically lands on another. Raises ``KeyError`` for an unknown node.
        """
        nodes, edges = self._load()
        if node_id not in nodes:
            raise KeyError(node_id)

        downstream = self._reachable(node_id, self._adjacency(edges))
        upstream = self._reachable(node_id, self._adjacency(edges, reverse=True))

        def jobs_at(dist: Dict[str, int]) -> List[Dict[str, Any]]:
            found = [
                {**nodes[nid], "distance": hops // 2 + hops % 2}
                for nid, hops in dist.items()
                if nodes[nid]["type"] == "job"
            ]
            return sorted(found, key=lambda n: (n["distance"], n["name"]))

        upstream_issues = [
            j for j in jobs_at(upstream) if j["run_status"] in (RUN_FAILED, RUN_RUNNING)
        ]

        return {
            "node": nodes[node_id],
            "impacted_jobs": jobs_at(downstream),
            "impacted_datasets": sorted(
                (nodes[nid] for nid in downstream if nodes[nid]["type"] == "dataset"),
                key=lambda n: n["name"],
            ),
            "impacted_platforms": sorted(
                {nodes[nid]["platform"] for nid in downstream if nodes[nid]["type"] == "job"}
            ),
            "upstream_issues": upstream_issues,
        }

    @staticmethod
    def _summarize(nodes: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        jobs = [n for n in nodes.values() if n["type"] == "job"]
        return {
            "jobs_by_platform": {
                p: sum(1 for j in jobs if j["platform"] == p) for p in LINEAGE_PLATFORMS
            },
            "teradata_load_jobs": sum(1 for j in jobs if j["job_type"] == "TERADATA_LOAD"),
            "datasets": sum(1 for n in nodes.values() if n["type"] == "dataset"),
            "failed_jobs": [j["name"] for j in jobs if j["run_status"] == RUN_FAILED],
            "running_jobs": [j["name"] for j in jobs if j["run_status"] == RUN_RUNNING],
            "impacted_jobs": sum(1 for j in jobs if j["impacted"]),
        }
