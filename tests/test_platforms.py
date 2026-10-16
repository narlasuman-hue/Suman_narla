"""Tests for configurable lineage platforms (platforms.csv) and the generic CSV sync."""

from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as routes
from src.catalog.platforms import (
    DEFAULT_PLATFORMS,
    PlatformConfigError,
    get_platform,
    load_platforms,
)
from src.catalog.services.column_lineage import ColumnLineageService
from src.catalog.services.job_lineage import JobLineageService
from src.catalog.services.lineage_sync import LineageSyncService
from src.connectors.lineage_files import CsvLineageConnector, LineageFileError

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data" / "lineage"
PLATFORMS_HEADER = "platform_id,folder,name,description,job_label,table_label,table_types,color\n"


def sync_demo(db, folder, platform_id):
    with CsvLineageConnector(str(DEMO_DIR), folder) as connector:
        stats = LineageSyncService(db, platform_id, connector).sync_all()
    assert stats["errors"] == []
    return stats


# ---------- platforms.csv ----------


def test_defaults_without_platforms_file(tmp_path):
    assert load_platforms(str(tmp_path)) == DEFAULT_PLATFORMS


def test_shipped_platforms_file():
    platforms = {p.id: p for p in load_platforms(str(DEMO_DIR))}
    assert list(platforms) == [
        "MAINFRAME", "HADOOP_ABINITIO", "INFORMATICA_ORACLE", "AIRFLOW_SNOWFLAKE", "DATASTAGE_DB2",
    ]
    assert platforms["HADOOP_ABINITIO"].table_types == {"HIVE", "HDFS"}
    assert platforms["AIRFLOW_SNOWFLAKE"].folder == "airflow"
    assert platforms["AIRFLOW_SNOWFLAKE"].is_table("snowflake")
    assert not platforms["AIRFLOW_SNOWFLAKE"].is_table("S3")


def test_get_platform_unknown(tmp_path):
    with pytest.raises(ValueError, match="Unknown platform"):
        get_platform("NOPE", str(tmp_path))


@pytest.mark.parametrize(
    "rows, message",
    [
        ("X1,x1,Name,,,,ORACLE,#123456\nX1,x2,Name,,,,ORACLE,#123456\n", "duplicate platform_id"),
        ("X1,x1,Name,,,,ORACLE,#123456\nX2,x1,Name,,,,ORACLE,#123456\n", "duplicate folder"),
        ("1BAD,x1,Name,,,,ORACLE,#123456\n", "platform_id"),
        ("X1,X 1,Name,,,,ORACLE,#123456\n", "folder"),
        ("X1,x1,,,,,ORACLE,#123456\n", "name is empty"),
        ("X1,x1,Name,,,,,#123456\n", "table_types is empty"),
        ("X1,x1,Name,,,,ORACLE,blue\n", "hex color"),
        ("", "no platforms defined"),
    ],
)
def test_platforms_file_validation(tmp_path, rows, message):
    (tmp_path / "platforms.csv").write_text(PLATFORMS_HEADER + rows)
    with pytest.raises(PlatformConfigError, match=message):
        load_platforms(str(tmp_path))


def test_platforms_file_missing_column(tmp_path):
    (tmp_path / "platforms.csv").write_text("platform_id,folder,name\nX1,x1,Name\n")
    with pytest.raises(PlatformConfigError, match="missing column"):
        load_platforms(str(tmp_path))


# ---------- the three new demo platforms ----------


@pytest.mark.parametrize(
    "folder, platform_id, failed, running, late_downstream",
    [
        ("informatica", "INFORMATICA_ORACLE", "wf_fact_sales", "wf_stg_returns",
         "wf_agg_daily_sales"),
        ("airflow", "AIRFLOW_SNOWFLAKE", "dbt_finance.fct_revenue", "dbt_core.fct_sessions",
         "bi_refresh.revenue_daily"),
        ("datastage", "DATASTAGE_DB2", "dsj_load_provider_dim", "dsj_ext_pharmacy",
         "dsj_load_claim_fact"),
    ],
)
def test_new_demo_platforms(db, folder, platform_id, failed, running, late_downstream):
    sync_demo(db, folder, platform_id)
    service = JobLineageService(db)

    summary = service.get_graph(platform_id)["summary"]
    assert summary["failed_jobs"] == [failed]
    assert summary["running_jobs"] == [running]
    assert summary["tables_loaded"] > 0

    impact = service.get_impact(platform_id, next(
        n["id"] for n in service.get_graph(platform_id)["nodes"] if n.get("name") == failed
    ))
    assert late_downstream in [j["name"] for j in impact["impacted_jobs"]]

    sla = {j["name"]: j for j in service.get_sla(platform_id)["jobs"]}
    assert sla[failed]["sla"]["status"] == "LATE"
    assert sla[late_downstream]["sla"]["status"] in ("LATE", "AT_RISK")
    assert failed in [b["name"] for b in sla[late_downstream]["blocked_by"]]


def test_tables_and_load_jobs_follow_table_types(db):
    sync_demo(db, "airflow", "AIRFLOW_SNOWFLAKE")
    nodes = {n["name"]: n for n in JobLineageService(db).get_graph("AIRFLOW_SNOWFLAKE")["nodes"]}

    assert nodes["RAW.EVENTS.APP_EVENTS"]["is_table"]  # SNOWFLAKE
    assert not nodes["s3://acme-lake/events/app/"]["is_table"]  # S3 source
    assert nodes["RAW.EVENTS.APP_EVENTS"]["database"] == "RAW.EVENTS"
    assert nodes["s3://acme-lake/events/app/"]["database"] == "s3://acme-lake"
    assert nodes["events_ingest.copy_app_events"]["job_type"] == "LOAD"
    # Writes only to Salesforce, not to a Snowflake table
    assert nodes["reverse_etl.push_revenue_to_crm"]["job_type"] == "JOB"

    tables = [t["name"] for t in JobLineageService(db).search_tables("AIRFLOW_SNOWFLAKE", "")]
    assert "s3://acme-lake/events/app/" not in tables
    assert "ANALYTICS.FINANCE.FCT_REVENUE" in tables


def test_column_search_on_new_platform(db):
    sync_demo(db, "datastage", "DATASTAGE_DB2")
    found = ColumnLineageService(db).search_columns("DATASTAGE_DB2", "MEMBER_ID", exact=True)
    assert {r["dataset_name"] for r in found} == {
        "STAGE.CLAIMS_STG", "STAGE.MEMBERS_STG", "STAGE.RX_CLAIMS_STG", "EDW.MEMBER_DIM",
    }


# ---------- routes ----------


@pytest.mark.asyncio
async def test_platforms_route(db, monkeypatch):
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(DEMO_DIR))
    await routes.sync_job_lineage(db)
    platforms = await routes.list_job_lineage_platforms(db)

    by_id = {p["id"]: p for p in platforms}
    assert len(platforms) == 5
    assert by_id["INFORMATICA_ORACLE"]["key"] == "informatica"
    assert by_id["INFORMATICA_ORACLE"]["table_label"] == "Oracle table"
    assert by_id["MAINFRAME"]["summary"] == {"jobs": 13, "failed": 2, "running": 1, "sla_late": 4}


@pytest.mark.asyncio
async def test_brand_new_platform_from_files_only(db, monkeypatch, tmp_path):
    """Adding a platform needs only a platforms.csv row and its CSV folder: no code."""
    (tmp_path / "platforms.csv").write_text(
        PLATFORMS_HEADER
        + "SSIS_SQLSERVER,ssis,SSIS → SQL Server,SSIS packages,SSIS package,"
        "SQL Server table,SQLSERVER,#b45309\n"
    )
    (tmp_path / "ssis").mkdir()
    (tmp_path / "ssis/jobs.csv").write_text(
        "job_name,scheduler_system,schedule_name,last_run_status,last_run,expected_completion\n"
        "pkg_load_orders,SQL Agent,NIGHTLY,FAILED,-2h,-1h\npkg_build_mart,SQL Agent,NIGHTLY,"
        "SUCCESS,-26h,+1h\n"
    )
    (tmp_path / "ssis/job_datasets.csv").write_text(
        "job_name,dataset_name,direction,dataset_type\n"
        "pkg_load_orders,/in/orders.csv,INPUT,FILE\n"
        "pkg_load_orders,dbo.Orders,OUTPUT,SQLSERVER\n"
        "pkg_build_mart,dbo.Orders,INPUT,SQLSERVER\n"
        "pkg_build_mart,mart.DailyOrders,OUTPUT,SQLSERVER\n"
    )
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(tmp_path))

    stats = await routes.sync_job_lineage(db)
    assert stats["platforms"]["SSIS_SQLSERVER"]["jobs_created"] == 2

    (platform,) = await routes.list_job_lineage_platforms(db)
    assert platform["name"] == "SSIS → SQL Server"
    assert platform["summary"]["failed"] == 1

    graph = await routes.get_job_lineage_graph(
        db=db, platform="SSIS_SQLSERVER", focus=None, direction="both", depth=None
    )
    impacted = {n["name"] for n in graph["nodes"] if n["impacted"]}
    assert {"dbo.Orders", "pkg_build_mart", "mart.DailyOrders"} <= impacted


@pytest.mark.asyncio
async def test_sync_reports_missing_platform_folder(db, monkeypatch, tmp_path):
    (tmp_path / "platforms.csv").write_text(
        PLATFORMS_HEADER + "X1,nothere,Name,,,,ORACLE,#123456\n"
    )
    monkeypatch.setattr(routes.settings, "lineage_data_dir", str(tmp_path))
    with pytest.raises(HTTPException) as exc_info:
        await routes.sync_job_lineage(db)
    assert exc_info.value.status_code == 400
    assert "no jobs file" in exc_info.value.detail


def test_connector_missing_jobs_file(tmp_path):
    with pytest.raises(LineageFileError, match="no jobs file"):
        CsvLineageConnector(str(tmp_path), "missing").connect()
