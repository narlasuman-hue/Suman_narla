"""Tests for Ab Initio sync and cross-platform job lineage."""

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as job_lineage_routes
from src.catalog.models import Job, JobExecution
from src.catalog.services.abinitio_sync import create_abinitio_sync_service
from src.catalog.services.job_lineage import JobLineageService, dataset_node_id, job_node_id
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.connectors.abinitio import MockAbInitioConnector
from src.connectors.mainframe import MockMainframeConnector


@pytest.fixture
def synced_db(db):
    """Catalog session with both mock platforms synced."""
    with MockMainframeConnector() as mainframe:
        create_mainframe_sync_service(db, mainframe).sync_all_jobs()
    with MockAbInitioConnector() as abinitio:
        create_abinitio_sync_service(db, abinitio).sync_all_graphs()
    return db


def _job_id(db, name: str) -> str:
    return job_node_id(db.query(Job).filter(Job.name == name).one().id)


def _names(nodes) -> set:
    return {n["name"] for n in nodes}


# ---------- Ab Initio connector & sync ----------


def test_abinitio_mock_connector_lists_graphs():
    with MockAbInitioConnector() as connector:
        graphs = connector.get_graphs()
        assert any(g["graph_name"] == "ing_td_gl_postings.mp" for g in graphs)
        datasets = connector.get_graph_datasets("ing_td_gl_postings.mp")
        assert {"INPUT", "OUTPUT"} <= {d["direction"] for d in datasets}


def test_abinitio_mock_connector_unknown_graph_raises():
    with pytest.raises(KeyError):
        MockAbInitioConnector().get_graph_details("nosuch.mp")


def test_abinitio_sync_creates_jobs_and_runs(db):
    with MockAbInitioConnector() as connector:
        stats = create_abinitio_sync_service(db, connector).sync_all_graphs()

    assert stats["errors"] == []
    jobs = db.query(Job).filter(Job.source_system == "HADOOP_ABINITIO").all()
    assert stats["jobs_created"] == len(jobs) == 6

    failed = db.query(Job).filter(Job.name == "bld_customer_360.mp").one()
    run = db.query(JobExecution).filter(JobExecution.job_id == failed.id).one()
    assert run.status == "FAILED"
    assert "reject" in run.error_message


def test_abinitio_sync_is_idempotent(db):
    connector = MockAbInitioConnector()
    service = create_abinitio_sync_service(db, connector)
    service.sync_all_graphs()
    stats = service.sync_all_graphs()

    assert stats["jobs_created"] == 0
    assert db.query(Job).filter(Job.source_system == "HADOOP_ABINITIO").count() == 6
    # Same run re-reported -> no duplicate execution rows
    assert db.query(JobExecution).count() == 6


def test_mainframe_sync_records_failed_run(db):
    with MockMainframeConnector() as connector:
        create_mainframe_sync_service(db, connector).sync_all_jobs()

    job = db.query(Job).filter(Job.name == "INVRECON").one()
    run = db.query(JobExecution).filter(JobExecution.job_id == job.id).one()
    assert run.status == "FAILED"
    assert run.error_message == "CC 0012"


# ---------- lineage graph ----------


def test_dataset_node_id_normalization():
    assert dataset_node_id(" fin_raw.gl_postings ") == "dataset:FIN_RAW.GL_POSTINGS"
    assert dataset_node_id("/data/Raw/x") == "dataset:/data/Raw/x"


def test_graph_links_mainframe_teradata_and_hadoop(synced_db):
    graph = JobLineageService(synced_db).get_graph()
    edges = {(e["source"], e["target"]) for e in graph["edges"]}

    td_table = dataset_node_id("FINANCE_DB.GL_POSTINGS")
    # mainframe FastLoad job writes the Teradata table, Ab Initio graph reads it
    assert (_job_id(synced_db, "TDGLLOAD"), td_table) in edges
    assert (td_table, _job_id(synced_db, "ing_td_gl_postings.mp")) in edges

    summary = graph["summary"]
    assert summary["jobs_by_platform"] == {"MAINFRAME": 5, "HADOOP_ABINITIO": 6}
    assert summary["teradata_load_jobs"] == 2
    assert set(summary["failed_jobs"]) == {"INVRECON", "bld_customer_360.mp"}
    assert summary["running_jobs"] == ["ing_mf_billing_stmts.mp"]

    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes[_job_id(synced_db, "TDGLLOAD")]["job_type"] == "TERADATA_LOAD"
    assert nodes[td_table]["platform"] == "TERADATA"


def test_failed_job_marks_downstream_impacted(synced_db):
    graph = JobLineageService(synced_db).get_graph()
    impacted = {n["name"] for n in graph["nodes"] if n["impacted"]}

    # INVRECON (mainframe) failure flows through Teradata into Hadoop
    assert {"TDINVMLD", "INV_DB.INVENTORY_RECON", "ing_td_inventory_recon.mp",
            "bld_supply_chain_kpi.mp"} <= impacted
    # unrelated finance chain is not impacted
    assert "TDGLLOAD" not in impacted
    assert "INVRECON" not in impacted


def test_platform_filter(synced_db):
    graph = JobLineageService(synced_db).get_graph(platform="HADOOP_ABINITIO")
    jobs = [n for n in graph["nodes"] if n["type"] == "job"]
    assert jobs and all(j["platform"] == "HADOOP_ABINITIO" for j in jobs)


def test_focus_upstream_with_depth(synced_db):
    service = JobLineageService(synced_db)
    focus = _job_id(synced_db, "ing_td_gl_postings.mp")

    full = service.get_graph(focus=focus, direction="upstream")
    assert {"TDGLLOAD", "PAYRDLY1"} <= _names(full["nodes"])
    assert "bld_fin_gl_summary.mp" not in _names(full["nodes"])

    one_level = service.get_graph(focus=focus, direction="upstream", depth=1)
    assert "TDGLLOAD" in _names(one_level["nodes"])
    assert "PAYRDLY1" not in _names(one_level["nodes"])


def test_focus_unknown_node_raises(synced_db):
    with pytest.raises(KeyError):
        JobLineageService(synced_db).get_graph(focus="job:999999")


def test_impact_of_mainframe_failure(synced_db):
    result = JobLineageService(synced_db).get_impact(_job_id(synced_db, "INVRECON"))

    impacted = [j["name"] for j in result["impacted_jobs"]]
    assert impacted[0] == "TDINVMLD"  # nearest first
    assert "bld_supply_chain_kpi.mp" in impacted
    assert result["impacted_platforms"] == ["HADOOP_ABINITIO", "MAINFRAME"]
    distance = {j["name"]: j["distance"] for j in result["impacted_jobs"]}
    assert distance["TDINVMLD"] == 1
    assert distance["ing_td_inventory_recon.mp"] == 2


def test_impact_reports_upstream_issues(synced_db):
    result = JobLineageService(synced_db).get_impact(_job_id(synced_db, "bld_supply_chain_kpi.mp"))
    assert "INVRECON" in [j["name"] for j in result["upstream_issues"]]


# ---------- routes (called directly; see note in test_mainframe.py) ----------


@pytest.mark.asyncio
async def test_sync_and_graph_routes(db):
    stats = await job_lineage_routes.sync_job_lineage(db)
    assert stats["mainframe"]["jobs_created"] == 5
    assert stats["abinitio"]["jobs_created"] == 6

    graph = await job_lineage_routes.get_job_lineage_graph(
        db=db, platform=None, focus=None, direction="both", depth=None
    )
    assert graph["nodes"] and graph["edges"]


@pytest.mark.asyncio
async def test_graph_route_errors(db):
    with pytest.raises(HTTPException) as exc_info:
        await job_lineage_routes.get_job_lineage_graph(
            db=db, platform="NOPE", focus=None, direction="both", depth=None
        )
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await job_lineage_routes.get_job_lineage_impact(node="job:999999", db=db)
    assert exc_info.value.status_code == 404
