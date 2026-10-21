"""Tests for the per-platform job list, detail and dataset endpoints."""

import asyncio
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as lineage_routes
from src.api.routes import platform_jobs as routes

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data" / "lineage"


@pytest.fixture
def synced(db, monkeypatch):
    """All five demo platforms synced into the catalog."""
    monkeypatch.setattr(lineage_routes.settings, "lineage_data_dir", str(DEMO_DIR))
    asyncio.run(lineage_routes.sync_job_lineage(db))


async def find_job(db, platform, name):
    return next(j for j in await list_jobs(db, platform) if j["job_name"] == name)


async def list_jobs(db, platform, **filters):
    return await routes.list_platform_jobs(
        platform=platform, db=db, run_status=filters.get("run_status"), skip=0, limit=500
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "platform, count, sample",
    [
        ("MAINFRAME", 13, "TDCRDPST"),
        ("HADOOP_ABINITIO", 11, "bld_fraud_features.mp"),
        ("INFORMATICA_ORACLE", 8, "wf_fact_sales"),
        ("AIRFLOW_SNOWFLAKE", 9, "dbt_finance.fct_revenue"),
        ("DATASTAGE_DB2", 8, "dsj_load_claim_fact"),
    ],
)
async def test_each_platform_lists_its_own_jobs(db, synced, platform, count, sample):
    jobs = await list_jobs(db, platform)
    assert len(jobs) == count
    assert all(j["platform"] == platform for j in jobs)
    assert sample in [j["job_name"] for j in jobs]
    assert [j["job_name"] for j in jobs] == sorted(j["job_name"] for j in jobs)


@pytest.mark.asyncio
async def test_list_includes_last_run_status_and_filters_on_it(db, synced):
    jobs = {j["job_name"]: j for j in await list_jobs(db, "INFORMATICA_ORACLE")}
    assert jobs["wf_fact_sales"]["last_run_status"] == "FAILED"
    assert jobs["wf_fact_sales"]["last_run_error"]
    assert jobs["wf_stg_returns"]["last_run_status"] == "RUNNING"
    assert jobs["wf_stg_orders"]["file_count"] == 2

    failed = await list_jobs(db, "INFORMATICA_ORACLE", run_status="failed")
    assert [j["job_name"] for j in failed] == ["wf_fact_sales"]


@pytest.mark.asyncio
async def test_job_detail_and_datasets(db, synced):
    job = await find_job(db, "AIRFLOW_SNOWFLAKE", "crm_ingest.sync_accounts")

    detail = await routes.get_platform_job("AIRFLOW_SNOWFLAKE", job["id"], db)
    assert detail["scheduler_system"] == "Airflow"
    files = await routes.get_platform_job_files("AIRFLOW_SNOWFLAKE", job["id"], db)
    assert {(f["dataset_name"], f["direction"]) for f in files} == {
        ("salesforce://Account", "INPUT"),
        ("RAW.CRM.ACCOUNTS", "OUTPUT"),
    }


@pytest.mark.asyncio
async def test_job_from_another_platform_is_not_found(db, synced):
    job = await find_job(db, "DATASTAGE_DB2", "dsj_ext_claims")
    with pytest.raises(HTTPException) as exc_info:
        await routes.get_platform_job("MAINFRAME", job["id"], db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_unknown_platform_and_bad_status(db, synced):
    with pytest.raises(HTTPException) as exc_info:
        await list_jobs(db, "NOPE")
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        await list_jobs(db, "MAINFRAME", run_status="BROKEN")
    assert exc_info.value.status_code == 400
