"""Tests for the CSV (demo) job lineage input files."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as job_lineage_routes
from src.catalog.models import Job
from src.catalog.services.job_lineage import JobLineageService
from src.catalog.services.lineage_sync import LineageSyncService
from src.connectors.lineage_files import CsvLineageConnector, LineageFileError, parse_time

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data" / "lineage"

MF_JOBS = (
    "job_name,owner,scheduler_system,schedule_name,frequency,last_run,last_run_status,"
    "return_code,duration_seconds,next_run\n"
)
MF_DATASETS = "job_name,dd_name,dataset_name,direction,dataset_type\n"
AI_GRAPHS = (
    "graph_name,owner,scheduler_system,schedule_name,last_run,last_run_status,"
    "duration_seconds,error_message,next_run\n"
)
AI_DATASETS = "graph_name,port,dataset_name,direction,dataset_type\n"


def sync(db, base, folder="mainframe", platform="MAINFRAME"):
    with CsvLineageConnector(str(base), folder) as connector:
        return LineageSyncService(db, platform, connector).sync_all()


def write_files(base: Path, mf_jobs="", mf_ds="", ai_graphs="", ai_ds="") -> Path:
    (base / "mainframe").mkdir(parents=True)
    (base / "abinitio").mkdir(parents=True)
    (base / "mainframe/jobs.csv").write_text(MF_JOBS + mf_jobs)
    (base / "mainframe/job_datasets.csv").write_text(MF_DATASETS + mf_ds)
    (base / "abinitio/graphs.csv").write_text(AI_GRAPHS + ai_graphs)
    (base / "abinitio/graph_datasets.csv").write_text(AI_DATASETS + ai_ds)
    return base


def test_parse_time_relative_and_iso():
    now = datetime(2026, 10, 7, 12, 0)
    assert parse_time("-9h", now) == now - timedelta(hours=9)
    assert parse_time("+2d", now) == now + timedelta(days=2)
    assert parse_time("-30m", now) == now - timedelta(minutes=30)
    assert parse_time("2026-10-06T23:15", now) == datetime(2026, 10, 6, 23, 15)
    assert parse_time("", now) is None
    with pytest.raises(ValueError):
        parse_time("yesterday", now)


def test_shipped_demo_files_load(db):
    """The demo files in demo_data/lineage are valid and tell the intended story."""
    assert sync(db, DEMO_DIR)["errors"] == []
    assert sync(db, DEMO_DIR, "abinitio", "HADOOP_ABINITIO")["errors"] == []

    service = JobLineageService(db)
    mf = service.get_graph("MAINFRAME")["summary"]
    assert set(mf["failed_jobs"]) == {"CRDTXN01", "TDLNSLD1"}
    assert mf["running_jobs"] == ["TDCUSLD1"]
    assert mf["impacted_jobs"] >= 3

    ai = service.get_graph("HADOOP_ABINITIO")["summary"]
    assert set(ai["failed_jobs"]) == {"bld_cards_txn_enriched.mp", "bld_loan_funnel.mp"}
    assert ai["running_jobs"] == ["ing_web_clickstream.mp"]
    assert ai["impacted_jobs"] >= 3

    (table,) = service.search_tables("MAINFRAME", "CARD_TRANSACTIONS")
    assert [j["name"] for j in table["loaded_by"]] == ["TDCRDPST"]
    assert table["impacted"]


def test_csv_values_reach_the_catalog(db, tmp_path):
    base = write_files(
        tmp_path,
        mf_jobs="TDLOAD1,DW_TEAM,CA-7,DW-DAILY,DAILY,-2h,FAILED,CC 0008,95,+22h\n",
        mf_ds=(
            "TDLOAD1,IN1,PROD.SALES.EXTRACT,INPUT,PS\n"
            "TDLOAD1,TDTGT,sales_db.daily_sales,output,teradata\n"
        ),
    )
    sync(db, base)

    job = db.query(Job).filter(Job.name == "TDLOAD1").one()
    assert (job.scheduler_system, job.schedule_name, job.frequency) == ("CA-7", "DW-DAILY", "DAILY")
    assert job.executions[0].status == "FAILED"
    assert job.executions[0].error_message == "CC 0008"
    assert job.executions[0].duration_seconds == 95

    (table,) = JobLineageService(db).search_tables("MAINFRAME", "daily_sales")
    assert table["dataset_type"] == "TERADATA"  # direction/type are case-insensitive
    assert table["loaded_by"][0]["name"] == "TDLOAD1"


def test_running_status_from_files(db, tmp_path):
    base = write_files(tmp_path, mf_jobs="JOB1,,CA-7,S1,,-10m,RUNNING,,,\n")
    sync(db, base)
    assert db.query(Job).filter(Job.name == "JOB1").one().executions[0].status == "RUNNING"


def test_status_kept_without_last_run(db, tmp_path):
    """FAILED/RUNNING with a blank last_run keep their status; blank SUCCESS stays UNKNOWN."""
    base = write_files(
        tmp_path,
        mf_jobs=(
            "JOB1,,CA-7,S1,,,FAILED,ABEND S0C7,,\n"
            "JOB2,,CA-7,S1,,,RUNNING,,,\n"
            "JOB3,,CA-7,S1,,,,,,\n"
        ),
        mf_ds="JOB1,OUT,A.B,OUTPUT,TERADATA\nJOB2,IN,A.B,INPUT,TERADATA\n",
    )
    sync(db, base)
    sync(db, base)  # re-sync updates the undated run in place

    job1 = db.query(Job).filter(Job.name == "JOB1").one()
    assert len(job1.executions) == 1
    assert job1.executions[0].start_time is None
    nodes = {n["name"]: n for n in JobLineageService(db).get_graph("MAINFRAME")["nodes"]}
    assert nodes["JOB1"]["run_status"] == "FAILED"
    assert nodes["JOB1"]["run_error"] == "ABEND S0C7"
    assert nodes["JOB2"]["run_status"] == "RUNNING"
    assert nodes["JOB2"]["impacted"]
    assert nodes["JOB3"]["run_status"] == "UNKNOWN"

    # A dated run later replaces the undated one
    (tmp_path / "mainframe/jobs.csv").write_text(
        MF_JOBS + "JOB1,,CA-7,S1,,-1h,SUCCESS,,,\nJOB2,,CA-7,S1,,,RUNNING,,,\n"
    )
    sync(db, base)
    db.refresh(job1)
    assert [(e.status, e.start_time is None) for e in job1.executions] == [("SUCCESS", False)]


@pytest.mark.parametrize(
    "files, message",
    [
        ({"mf_jobs": "JOB1,,CA-7,S1,,-1h,BROKEN,,,\n"}, "last_run_status 'BROKEN'"),
        ({"mf_jobs": "JOB1,,CA-7,S1,,last week,SUCCESS,,,\n"}, "invalid time"),
        ({"mf_jobs": "JOB1,,CA-7,S1,,-1h,SUCCESS,,ten,\n"}, "duration_seconds"),
        (
            {"mf_jobs": "JOB1,,CA-7,S1,,-1h,SUCCESS,,,\nJOB1,,CA-7,S1,,-1h,SUCCESS,,,\n"},
            "duplicate job_name",
        ),
        ({"mf_ds": "NOPE,DD1,A.B,INPUT,PS\n"}, "'NOPE' is not in mainframe/jobs.csv"),
        (
            {"mf_jobs": "JOB1,,CA-7,S1,,-1h,SUCCESS,,,\n", "mf_ds": "JOB1,DD1,A.B,READ,PS\n"},
            "direction 'READ'",
        ),
    ],
)
def test_invalid_files_report_line_and_problem(tmp_path, files, message):
    base = write_files(tmp_path, **files)
    with pytest.raises(LineageFileError, match=message) as exc_info:
        CsvLineageConnector(str(base), "mainframe").connect()
    assert "line" in str(exc_info.value)


def test_missing_column_and_file(tmp_path):
    base = write_files(tmp_path)
    (base / "abinitio/graphs.csv").write_text("graph_name,owner\n")
    with pytest.raises(LineageFileError, match="missing column"):
        CsvLineageConnector(str(base), "abinitio").connect()

    (base / "abinitio/graph_datasets.csv").unlink()
    (base / "abinitio/graphs.csv").write_text(AI_GRAPHS)
    with pytest.raises(LineageFileError, match="file not found"):
        CsvLineageConnector(str(base), "abinitio").connect()


@pytest.mark.asyncio
async def test_sync_route_uses_files_when_present(db, monkeypatch):
    monkeypatch.setattr(job_lineage_routes.settings, "lineage_data_dir", str(DEMO_DIR))
    stats = await job_lineage_routes.sync_job_lineage(db)
    assert stats["source"].startswith("files:")
    created = {p: r["jobs_created"] for p, r in stats["platforms"].items()}
    assert created == {
        "MAINFRAME": 13,
        "HADOOP_ABINITIO": 11,
        "INFORMATICA_ORACLE": 8,
        "AIRFLOW_SNOWFLAKE": 9,
        "DATASTAGE_DB2": 8,
    }
    assert stats["jobs_synced"] == 49


@pytest.mark.asyncio
async def test_sync_route_reports_bad_files(db, monkeypatch, tmp_path):
    base = write_files(tmp_path, mf_ds="NOPE,DD1,A.B,INPUT,PS\n")
    monkeypatch.setattr(job_lineage_routes.settings, "lineage_data_dir", str(base))
    with pytest.raises(HTTPException) as exc_info:
        await job_lineage_routes.sync_job_lineage(db)
    assert exc_info.value.status_code == 400
    assert "NOPE" in exc_info.value.detail
