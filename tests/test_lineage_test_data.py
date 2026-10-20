"""Tests that run the edge-case and invalid input files in test_data/lineage/."""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as routes
from src.catalog.services.column_lineage import ColumnLineageService
from src.catalog.services.job_lineage import JobLineageService

TEST_DATA = Path(__file__).resolve().parent.parent / "test_data" / "lineage"
INVALID_CASES = sorted(p for p in (TEST_DATA / "invalid").iterdir() if p.is_dir())


@pytest.fixture
def synced(db, monkeypatch):
    """Sync the valid edge-case set; return the sync stats."""
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(TEST_DATA / "valid"))
    return asyncio.run(routes.sync_job_lineage(db))


def nodes(db, platform_id):
    return {n["name"]: n for n in JobLineageService(db).get_graph(platform_id)["nodes"]}


def sla(db, platform_id):
    return {j["name"]: j for j in JobLineageService(db).get_sla(platform_id)["jobs"]}


def downstream(db, platform_id, job):
    service = JobLineageService(db)
    impact = service.get_impact(platform_id, nodes(db, platform_id)[job]["id"])
    return {j["name"] for j in impact["impacted_jobs"]}


# ---------- valid edge cases ----------


@pytest.mark.asyncio
async def test_valid_set_syncs_all_six_platforms(db, synced):
    assert synced["source"].startswith("files:")
    assert sorted(synced["platforms"]) == [
        "AIRFLOW_SNOWFLAKE", "DATASTAGE_DB2", "HADOOP_ABINITIO", "INFORMATICA_ORACLE",
        "MAINFRAME", "SSIS_SQLSERVER",
    ]
    assert all(stats["errors"] == [] for stats in synced["platforms"].values())

    by_id = {p["id"]: p for p in await routes.list_job_lineage_platforms(db)}
    ssis = by_id["SSIS_SQLSERVER"]
    assert ssis["key"] == "ssis-sqlserver"
    assert (ssis["job_label"], ssis["table_label"], ssis["color"]) == ("Job", "Table", "#4338ca")
    assert ssis["table_types"] == ["AZURESQL", "SQLSERVER"]


@pytest.mark.asyncio
async def test_mainframe_edge_cases(db, synced):
    n = nodes(db, "MAINFRAME")
    assert n["MFEXT01"]["run_status"] == "SUCCESS"  # lower-case "success"
    assert n["MFGDG01"]["run_status"] == "SUCCESS"  # blank status
    assert "MFORPHAN" in n  # job with no datasets
    # TDMERGE1 reads fin_stg.orders_stg in lower case and still links to TDLOAD1
    assert {"TDMERGE1", "TDRPT01"} <= downstream(db, "MAINFRAME", "TDLOAD1")

    statuses = sla(db, "MAINFRAME")
    assert statuses["TDLOAD1"]["sla"]["status"] == "LATE"
    assert "TDLOAD1" in [b["name"] for b in statuses["TDMERGE1"]["blocked_by"]]

    found = ColumnLineageService(db).search_columns("MAINFRAME", "AMOUNT", exact=True)
    assert "FIN_DB.ORDERS" in {r["dataset_name"] for r in found}


@pytest.mark.asyncio
async def test_abinitio_hdfs_paths_match_exactly(db, synced):
    n = nodes(db, "HADOOP_ABINITIO")
    assert "/data/raw/events" in n and "/DATA/RAW/EVENTS" in n  # two separate datasets
    impacted = downstream(db, "HADOOP_ABINITIO", "bld_events_daily.mp")
    assert {"agg_events.mp", "chk_late.mp"} <= impacted  # Hive names case-insensitive
    assert "bld_case_mismatch.mp" not in downstream(db, "HADOOP_ABINITIO", "ing_events.mp")

    statuses = sla(db, "HADOOP_ABINITIO")
    assert statuses["ing_events.mp"]["sla"]["status"] == "MET"
    assert statuses["chk_late.mp"]["sla"]["status"] == "COMPLETED_LATE"


@pytest.mark.asyncio
async def test_informatica_without_optional_files(db, synced):
    assert ColumnLineageService(db).search_columns("INFORMATICA_ORACLE", "", exact=False) == []
    n = nodes(db, "INFORMATICA_ORACLE")
    assert n["wf_upsert_customer_dim"]["run_status"] == "FAILED"  # " failed " with spaces
    assert {"wf_exp_customers", "wf_audit_only"} <= downstream(
        db, "INFORMATICA_ORACLE", "wf_upsert_customer_dim"
    )
    assert sla(db, "INFORMATICA_ORACLE")["wf_upsert_customer_dim"]["sla"]["status"] == "LATE"


@pytest.mark.asyncio
async def test_airflow_urls_match_exactly(db, synced):
    n = nodes(db, "AIRFLOW_SNOWFLAKE")
    assert "s3://acme/Orders/" in n and "s3://acme/orders/" in n
    assert not n["s3://acme/Orders/"]["is_table"]
    assert n["reverse_etl.push_orders"]["job_type"] == "JOB"
    assert n["dbt.fct_orders"]["job_type"] == "LOAD"
    assert "reverse_etl.push_orders" in downstream(db, "AIRFLOW_SNOWFLAKE", "dbt.fct_orders")


@pytest.mark.asyncio
async def test_datastage_inout_and_monthly(db, synced):
    statuses = sla(db, "DATASTAGE_DB2")
    assert statuses["dsj_load_mart"]["sla"]["status"] == "MET"  # MONTHLY period
    assert nodes(db, "DATASTAGE_DB2")["dsj_merge_claims"]["run_status"] == "RUNNING"
    found = ColumnLineageService(db).search_columns("DATASTAGE_DB2", "PAID_AMT", exact=True)
    assert "EDW.CLAIMS" in {r["dataset_name"] for r in found}


@pytest.mark.asyncio
async def test_ssis_new_platform_chain(db, synced):
    n = nodes(db, "SSIS_SQLSERVER")
    assert n["cloud.CustomerSummary"]["is_table"]  # AzureSQL in table_types
    assert {"pkg_build_mart", "pkg_sync_azure"} <= downstream(
        db, "SSIS_SQLSERVER", "pkg_load_customers"
    )


# ---------- invalid files: one broken rule each ----------


@pytest.mark.asyncio
@pytest.mark.parametrize("case", INVALID_CASES, ids=lambda p: p.name)
async def test_invalid_case_reports_expected_error(db, monkeypatch, case):
    expected = (case / "expected_error.txt").read_text(encoding="utf-8").strip()
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(case))
    with pytest.raises(HTTPException) as exc_info:
        await routes.sync_job_lineage(db)
    assert exc_info.value.status_code == 400
    assert expected in exc_info.value.detail
