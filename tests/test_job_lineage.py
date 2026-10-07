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
        assert any(g["graph_name"] == "ing_gl_postings.mp" for g in graphs)
        datasets = connector.get_graph_datasets("ing_gl_postings.mp")
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

MF = "MAINFRAME"
AI = "HADOOP_ABINITIO"


def test_dataset_node_id_normalization():
    assert dataset_node_id(" fin_raw.gl_postings ") == "dataset:FIN_RAW.GL_POSTINGS"
    assert dataset_node_id("/data/Raw/x") == "dataset:/data/Raw/x"


def test_mainframe_graph_loads_teradata_tables(synced_db):
    graph = JobLineageService(synced_db).get_graph(MF)
    edges = {(e["source"], e["target"]) for e in graph["edges"]}

    # PAYRDLY1 writes the GL extract, which TDGLLOAD FastLoads into Teradata
    gl_extract = dataset_node_id("PROD.PAYROLL.GL.EXTRACT")
    td_table = dataset_node_id("FINANCE_DB.GL_POSTINGS")
    assert (_job_id(synced_db, "PAYRDLY1"), gl_extract) in edges
    assert (gl_extract, _job_id(synced_db, "TDGLLOAD")) in edges
    assert (_job_id(synced_db, "TDGLLOAD"), td_table) in edges

    nodes = {n["id"]: n for n in graph["nodes"]}
    assert nodes[_job_id(synced_db, "TDGLLOAD")]["job_type"] == "TERADATA_LOAD"
    assert nodes[td_table]["platform"] == "TERADATA"

    summary = graph["summary"]
    assert summary["jobs"] == 5
    assert summary["tables_loaded"] == 3  # GL_EXTRACT_STG, GL_POSTINGS, INVENTORY_RECON
    assert summary["failed_jobs"] == ["INVRECON"]


def test_abinitio_graph_loads_hadoop_tables(synced_db):
    graph = JobLineageService(synced_db).get_graph(AI)
    edges = {(e["source"], e["target"]) for e in graph["edges"]}
    hive_table = dataset_node_id("fin_raw.gl_postings")
    assert (_job_id(synced_db, "ing_gl_postings.mp"), hive_table) in edges
    assert (hive_table, _job_id(synced_db, "bld_fin_gl_summary.mp")) in edges

    summary = graph["summary"]
    assert summary["jobs"] == 6
    assert set(summary["failed_jobs"]) == {"ing_inventory_recon.mp", "bld_customer_360.mp"}
    assert summary["running_jobs"] == ["ing_billing_stmts.mp"]


def test_platforms_are_separate(synced_db):
    service = JobLineageService(synced_db)
    for platform in (MF, AI):
        jobs = [n for n in service.get_graph(platform)["nodes"] if n["type"] == "job"]
        assert jobs and all(j["platform"] == platform for j in jobs)

    ai_dataset_platforms = {
        n["platform"] for n in service.get_graph(AI)["nodes"] if n["type"] == "dataset"
    }
    assert ai_dataset_platforms == {"HADOOP"}


def test_unknown_platform_raises(synced_db):
    with pytest.raises(ValueError):
        JobLineageService(synced_db).get_graph("NOPE")


def test_failed_job_marks_downstream_impacted(synced_db):
    service = JobLineageService(synced_db)

    mf_impacted = {n["name"] for n in service.get_graph(MF)["nodes"] if n["impacted"]}
    assert {"TDINVMLD", "INV_DB.INVENTORY_RECON"} <= mf_impacted
    assert "TDGLLOAD" not in mf_impacted
    assert "INVRECON" not in mf_impacted

    ai_impacted = {n["name"] for n in service.get_graph(AI)["nodes"] if n["impacted"]}
    assert {"inv_raw.inventory_recon", "bld_supply_chain_kpi.mp"} <= ai_impacted
    assert "bld_fin_gl_summary.mp" not in ai_impacted


def test_focus_upstream_with_depth(synced_db):
    service = JobLineageService(synced_db)
    focus = dataset_node_id("FINANCE_DB.GL_POSTINGS")

    full = service.get_graph(MF, focus=focus, direction="upstream")
    assert {"TDGLLOAD", "PAYRDLY1"} <= _names(full["nodes"])
    assert "INVRECON" not in _names(full["nodes"])

    one_level = service.get_graph(MF, focus=focus, direction="upstream", depth=1)
    assert "TDGLLOAD" in _names(one_level["nodes"])
    assert "PAYRDLY1" not in _names(one_level["nodes"])


def test_focus_node_from_other_platform_raises(synced_db):
    with pytest.raises(KeyError):
        JobLineageService(synced_db).get_graph(AI, focus=_job_id(synced_db, "TDGLLOAD"))


def test_impact_of_mainframe_failure(synced_db):
    result = JobLineageService(synced_db).get_impact(MF, _job_id(synced_db, "INVRECON"))

    assert [j["name"] for j in result["impacted_jobs"]] == ["TDINVMLD"]
    assert result["impacted_jobs"][0]["distance"] == 1
    assert dataset_node_id("INV_DB.INVENTORY_RECON") in {
        d["id"] for d in result["impacted_datasets"]
    }


def test_impact_of_abinitio_failure(synced_db):
    service = JobLineageService(synced_db)
    result = service.get_impact(AI, _job_id(synced_db, "ing_inventory_recon.mp"))
    assert [j["name"] for j in result["impacted_jobs"]] == ["bld_supply_chain_kpi.mp"]

    upstream = service.get_impact(AI, _job_id(synced_db, "bld_supply_chain_kpi.mp"))
    assert "ing_inventory_recon.mp" in [j["name"] for j in upstream["upstream_issues"]]


# ---------- routes (called directly; see note in test_mainframe.py) ----------


@pytest.mark.asyncio
async def test_sync_and_graph_routes(db):
    stats = await job_lineage_routes.sync_job_lineage(db)
    assert stats["mainframe"]["jobs_created"] == 5
    assert stats["abinitio"]["jobs_created"] == 6

    graph = await job_lineage_routes.get_job_lineage_graph(
        db=db, platform=MF, focus=None, direction="both", depth=None
    )
    assert graph["platform"] == MF
    assert graph["nodes"] and graph["edges"]


@pytest.mark.asyncio
async def test_graph_route_errors(db):
    with pytest.raises(HTTPException) as exc_info:
        await job_lineage_routes.get_job_lineage_graph(
            db=db, platform="NOPE", focus=None, direction="both", depth=None
        )
    assert exc_info.value.status_code == 400

    with pytest.raises(HTTPException) as exc_info:
        await job_lineage_routes.get_job_lineage_impact(platform=MF, node="job:999999", db=db)
    assert exc_info.value.status_code == 404
