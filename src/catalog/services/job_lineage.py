"""Job lineage for two independent platforms.

* ``MAINFRAME``: mainframe JCL jobs, which load Teradata tables
  (BTEQ / FastLoad / MultiLoad) from mainframe datasets;
* ``HADOOP_ABINITIO``: Ab Initio graphs, which load Hadoop (Hive / HDFS) tables.

Lineage is always built for one platform at a time from the catalog's
``Job`` / ``JobFile`` rows:

* job nodes: the platform's jobs;
* dataset nodes: the datasets/tables those jobs read and write;
* edges: ``dataset -> job`` for inputs and ``job -> dataset`` for outputs.

For SRE triage, every node downstream of a job whose latest run failed is
flagged as impacted (the failure's blast radius).
"""

from collections import deque
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.orm import Session, selectinload

from src.catalog.models import Job
from src.catalog.services.job_runs import RUN_FAILED, RUN_RUNNING
from src.catalog.services.sla import COMPLETED_LATE, LATE, MET, SEVERITY, evaluate_sla

PLATFORM_LABELS = {
    "MAINFRAME": "Mainframe / Teradata",
    "HADOOP_ABINITIO": "Hadoop / Ab Initio",
}
DIRECTIONS = ("upstream", "downstream", "both")

# The tables each platform loads: Teradata tables for mainframe jobs,
# Hive/HDFS tables for Ab Initio graphs.
TABLE_PLATFORM = {"MAINFRAME": "TERADATA", "HADOOP_ABINITIO": "HADOOP"}

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


def database_of(dataset_name: str, dataset_type: Optional[str]) -> str:
    """The database a dataset belongs to, for database-level lineage.

    * Teradata / Hive ``DB.TABLE`` -> ``DB``
    * HDFS ``/data/raw/cards/auth`` -> zone ``/data/raw``
    * Mainframe DSN ``PROD.PAYROLL.GL.EXTRACT`` -> qualifiers ``PROD.PAYROLL``
    """
    name = dataset_name.strip()
    if name.startswith("/"):
        parts = [p for p in name.split("/") if p]
        return "/" + "/".join(parts[:2])
    kind = (dataset_type or "").upper()
    if kind in ("TERADATA", "HIVE"):
        database = name.split(".")[0]
        # Teradata names are conventionally upper case, Hive lower case.
        return database.upper() if kind == "TERADATA" else database.lower()
    qualifiers = name.upper().split(".")
    return ".".join(qualifiers[:2])


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

    def _load(self, platform: str, now: Optional[datetime] = None) -> Graph:
        if platform not in PLATFORM_LABELS:
            raise ValueError(f"Unknown platform: {platform}")
        jobs = (
            self.db.query(Job)
            .options(
                selectinload(Job.files), selectinload(Job.executions), selectinload(Job.sla)
            )
            .filter(Job.source_system == platform)
            .order_by(Job.name)
            .all()
        )

        nodes: Dict[str, Dict[str, Any]] = {}
        edges: Dict[str, Dict[str, Any]] = {}
        slas = {}  # job node id -> (expected completion, last run start)

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
                "sla": None,
            }
            if job.sla is not None:
                slas[jid] = (job.sla.expected_completion, job.last_run)

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
                        "database": database_of(f.dataset_name, dataset_type),
                    },
                )
                direction = (f.direction or "").upper()
                if direction in ("INPUT", "INOUT"):
                    self._add_edge(edges, did, jid, f.dd_name)
                if direction in ("OUTPUT", "INOUT"):
                    self._add_edge(edges, jid, did, f.dd_name)

        self._mark_impact(nodes, list(edges.values()))
        # SLA status depends on impact (a blocked job is at risk), so evaluate after it.
        for jid, (expected, last_run) in slas.items():
            nodes[jid]["sla"] = evaluate_sla(nodes[jid], expected, last_run, now)
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
        platform: str,
        focus: Optional[str] = None,
        direction: str = "both",
        depth: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Return one platform's lineage graph, optionally narrowed around a focus node.

        ``depth`` counts job levels (a job -> dataset -> job step is one level).
        Raises ``ValueError`` for an unknown platform/direction and ``KeyError``
        if ``focus`` is not in the platform's graph.
        """
        if direction not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")

        nodes, edges = self._load(platform)
        summary = self._summarize(nodes, edges)

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
            "platform": platform,
            "focus": focus,
        }

    def search_tables(
        self, platform: str, query: str = "", limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Find the platform's tables whose name contains ``query`` (case-insensitive).

        Each result lists the jobs that load the table and the jobs that read it.
        An empty query returns all tables, alphabetically, up to ``limit``.
        """
        nodes, edges = self._load(platform)
        needle = query.strip().lower()
        tables = [
            n
            for n in nodes.values()
            if n["type"] == "dataset"
            and n["platform"] == TABLE_PLATFORM[platform]
            and needle in n["name"].lower()
        ]
        # Exact and prefix matches first, then alphabetical.
        tables.sort(
            key=lambda n: (
                n["name"].lower() != needle,
                not n["name"].lower().startswith(needle),
                n["name"].lower(),
            )
        )

        def job_ref(job_id: str) -> Dict[str, Any]:
            job = nodes[job_id]
            return {
                "id": job["id"],
                "name": job["name"],
                "run_status": job["run_status"],
                "last_run": job["last_run"],
            }

        return [
            {
                **table,
                "loaded_by": [job_ref(e["source"]) for e in edges if e["target"] == table["id"]],
                "read_by": [job_ref(e["target"]) for e in edges if e["source"] == table["id"]],
            }
            for table in tables[:limit]
        ]

    def get_impact(self, platform: str, node_id: str) -> Dict[str, Any]:
        """Blast radius of ``node_id`` plus upstream jobs that are failing or still running.

        Raises ``ValueError`` for an unknown platform and ``KeyError`` for a node
        that is not in that platform's graph.
        """
        nodes, edges = self._load(platform)
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
            "upstream_issues": upstream_issues,
        }

    def get_sla(self, platform: str, now: Optional[datetime] = None) -> Dict[str, Any]:
        """SLA status of every job that has an expected completion time, worst first.

        Each row includes ``blocked_by``: failed or still-running jobs upstream of
        it, which is usually why a job is late or at risk.
        """
        nodes, edges = self._load(platform, now)
        reverse = self._adjacency(edges, reverse=True)
        jobs = [n for n in nodes.values() if n["type"] == "job"]

        rows = []
        for job in (j for j in jobs if j["sla"]):
            if job["sla"]["status"] in (MET, COMPLETED_LATE):
                rows.append({**job, "blocked_by": []})  # already completed
                continue
            upstream = self._reachable(job["id"], reverse)
            blocked_by = sorted(
                (
                    {"id": nid, "name": nodes[nid]["name"], "run_status": nodes[nid]["run_status"]}
                    for nid in upstream
                    if nodes[nid]["type"] == "job"
                    and nodes[nid]["run_status"] in (RUN_FAILED, RUN_RUNNING)
                ),
                key=lambda b: (upstream[b["id"]], b["name"]),
            )
            rows.append({**job, "blocked_by": blocked_by})

        rows.sort(
            key=lambda r: (SEVERITY[r["sla"]["status"]], -r["sla"]["late_by_minutes"], r["name"])
        )
        counts = {status: 0 for status in SEVERITY}
        for r in rows:
            counts[r["sla"]["status"]] += 1
        return {
            "platform": platform,
            "jobs": rows,
            "counts": counts,
            "jobs_without_sla": len(jobs) - len(rows),
        }

    @staticmethod
    def _summarize(
        nodes: Dict[str, Dict[str, Any]], edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        jobs = [n for n in nodes.values() if n["type"] == "job"]
        written = {e["target"] for e in edges}
        return {
            "jobs": len(jobs),
            # Teradata tables (mainframe) or Hive/HDFS tables (Ab Initio) a job loads
            "tables_loaded": sum(
                1
                for nid, n in nodes.items()
                if n["type"] == "dataset" and n["platform"] != "MAINFRAME" and nid in written
            ),
            "datasets": sum(1 for n in nodes.values() if n["type"] == "dataset"),
            "failed_jobs": [j["name"] for j in jobs if j["run_status"] == RUN_FAILED],
            "sla_late": sum(
                1 for j in jobs if j["sla"] and j["sla"]["status"] in (LATE, COMPLETED_LATE)
            ),
            "sla_at_risk": sum(1 for j in jobs if j["sla"] and j["sla"]["status"] == "AT_RISK"),
            "running_jobs": [j["name"] for j in jobs if j["run_status"] == RUN_RUNNING],
            "impacted_jobs": sum(1 for j in jobs if j["impacted"]),
        }
