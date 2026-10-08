"""Tests for SLA tracking, database grouping, column search and column-level lineage."""

from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi import HTTPException

from src.api.routes import job_lineage as routes
from src.catalog.models import Job, JobSla
from src.catalog.services.abinitio_sync import create_abinitio_sync_service
from src.catalog.services.column_lineage import ColumnLineageService, column_node_id
from src.catalog.services.job_lineage import JobLineageService, database_of
from src.catalog.services.job_metadata import upsert_sla
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.catalog.services.sla import evaluate_sla
from src.connectors.lineage_files import (
    CsvAbInitioConnector,
    CsvMainframeConnector,
    LineageFileError,
    parse_deadline,
)

DEMO_DIR = Path(__file__).resolve().parent.parent / "demo_data" / "lineage"
MF, AI = "MAINFRAME", "HADOOP_ABINITIO"
NOW = datetime(2026, 10, 8, 12, 0)


@pytest.fixture
def demo_db(db):
    with CsvMainframeConnector(str(DEMO_DIR)) as mf:
        assert create_mainframe_sync_service(db, mf).sync_all_jobs()["errors"] == []
    with CsvAbInitioConnector(str(DEMO_DIR)) as ai:
        assert create_abinitio_sync_service(db, ai).sync_all_graphs()["errors"] == []
    return db


def _job(status="SUCCESS", duration=600, frequency="DAILY", impacted_by=()):
    return {
        "run_status": status,
        "run_duration_seconds": duration,
        "frequency": frequency,
        "impacted": bool(impacted_by),
        "impacted_by": list(impacted_by),
    }


# ---------- SLA rules ----------


def hours(n: float) -> timedelta:
    return timedelta(hours=n)


@pytest.mark.parametrize(
    "job, expected, last_run, status, late_by",
    [
        (_job(), NOW - hours(1), NOW - hours(2), "MET", 0),
        (_job(duration=3 * 3600), NOW - hours(1), NOW - hours(3), "COMPLETED_LATE", 60),
        (_job("FAILED"), NOW - hours(2), NOW - hours(3), "LATE", 120),
        (_job("RUNNING"), NOW - hours(0.25), NOW - hours(1), "LATE", 15),
        # yesterday's success does not count toward today's SLA
        (_job(), NOW - hours(1), NOW - hours(27), "LATE", 60),
        (_job(impacted_by=["UPSTREAM"]), NOW + hours(3), NOW - hours(26), "AT_RISK", 0),
        (_job("FAILED"), NOW + hours(3), NOW - hours(1), "AT_RISK", 0),
        (_job("RUNNING"), NOW + timedelta(minutes=20), NOW - hours(0.2), "AT_RISK", 0),
        (_job(), NOW + hours(5), NOW - hours(20), "ON_TRACK", 0),
        # hourly job: a run 3 hours ago is a previous cycle
        (_job(frequency="HOURLY"), NOW - hours(0.5), NOW - hours(3), "LATE", 30),
    ],
)
def test_evaluate_sla(job, expected, last_run, status, late_by):
    result = evaluate_sla(job, expected, last_run, NOW)
    assert result["status"] == status
    assert result["late_by_minutes"] == late_by


def test_parse_deadline_clock_time_and_offsets():
    assert parse_deadline("06:30", NOW) == datetime(2026, 10, 8, 6, 30)
    assert parse_deadline("+2h", NOW) == NOW + timedelta(hours=2)
    assert parse_deadline("", NOW) is None
    with pytest.raises(ValueError):
        parse_deadline("25:00", NOW)


def test_demo_sla_story(demo_db):
    service = JobLineageService(demo_db)

    mf = service.get_sla(MF)
    assert mf["counts"] == {
        "LATE": 3, "COMPLETED_LATE": 1, "AT_RISK": 4, "ON_TRACK": 1, "MET": 4,
    }
    worst_first = [j["name"] for j in mf["jobs"][:3]]
    assert worst_first == ["TDLNSLD1", "CRDTXN01", "TDCRDLD1"]
    late_load = next(j for j in mf["jobs"] if j["name"] == "TDCRDLD1")
    assert [b["name"] for b in late_load["blocked_by"]] == ["CRDTXN01"]

    ai = service.get_sla(AI)
    assert ai["counts"]["LATE"] == 3
    met = next(j for j in ai["jobs"] if j["name"] == "bld_digital_sessions.mp")
    assert met["sla"]["status"] == "MET" and met["blocked_by"] == []

    summary = service.get_graph(MF)["summary"]
    assert (summary["sla_late"], summary["sla_at_risk"]) == (4, 4)


def test_upsert_sla_clears_when_removed(db):
    job = Job(name="J1", source_system=MF)
    db.add(job)
    db.flush()
    upsert_sla(db, job, NOW)
    db.flush()
    assert db.query(JobSla).count() == 1
    upsert_sla(db, job, None)
    db.flush()
    assert db.query(JobSla).count() == 0


# ---------- database grouping ----------


@pytest.mark.parametrize(
    "name, dataset_type, database",
    [
        ("FINANCE_DB.GL_POSTINGS", "TERADATA", "FINANCE_DB"),
        ("cards_raw.Auth_Events", "HIVE", "cards_raw"),
        ("/data/raw/cards/auth", "HDFS", "/data/raw"),
        ("PROD.PAYROLL.GL.EXTRACT", "PS", "PROD.PAYROLL"),
    ],
)
def test_database_of(name, dataset_type, database):
    assert database_of(name, dataset_type) == database


def test_dataset_nodes_carry_database(demo_db):
    nodes = JobLineageService(demo_db).get_graph(AI)["nodes"]
    hive = next(n for n in nodes if n["name"] == "cards_cur.txn_enriched")
    assert hive["database"] == "cards_cur"


# ---------- column search ----------


def test_column_search_lists_every_table_with_the_column(demo_db):
    results = ColumnLineageService(demo_db).search_columns(MF, "customer_id", exact=True)
    tables = {r["dataset_name"]: r for r in results}
    assert {
        "CUSTOMER_DB.CUSTOMER_MASTER",
        "CARDS_DB.CARD_TRANSACTIONS",
        "RISK_DB.FRAUD_ALERTS_DAILY",
        "RISK_DB.COLLECTIONS_QUEUE",
        "LOANS_DB.DELINQUENCY_DAILY",
    } <= set(tables)
    master = tables["CUSTOMER_DB.CUSTOMER_MASTER"]
    assert master["database"] == "CUSTOMER_DB"
    assert master["data_type"] == "VARCHAR(12)"
    assert [j["name"] for j in master["loaded_by"]] == ["TDCUSLD1"]
    assert master["loaded_by"][0]["run_status"] == "RUNNING"
    assert master["loaded_by"][0]["sla_status"] == "AT_RISK"
    assert tables["CARDS_DB.CARD_TRANSACTIONS"]["impacted"]  # downstream of CRDTXN01


def test_column_search_partial_and_empty(demo_db):
    service = ColumnLineageService(demo_db)
    names = {r["column"] for r in service.search_columns(AI, "score")}
    assert names == {"fraud_score", "amount_zscore"}  # any part of the name
    assert service.search_columns(AI, "  ") == []


def test_list_table_columns_in_file_order(demo_db):
    columns = ColumnLineageService(demo_db).list_table_columns(
        MF, "dataset:CARDS_DB.CARD_TRANSACTIONS"
    )
    assert [c["column"] for c in columns] == [
        "TXN_ID", "CUSTOMER_ID", "CARD_NUMBER", "TXN_DATE", "MERCHANT_ID", "TXN_AMOUNT",
    ]
    customer_id = columns[1]
    assert (customer_id["upstream_columns"], customer_id["downstream_columns"]) == (1, 1)


# ---------- column lineage ----------


def test_column_lineage_upstream_traces_to_source(demo_db):
    service = ColumnLineageService(demo_db)
    focus = column_node_id("RISK_DB.FRAUD_ALERTS_DAILY", "CUSTOMER_ID")

    lineage = service.get_column_lineage(MF, focus, "upstream")
    ids = {n["id"] for n in lineage["nodes"]}
    assert column_node_id("PROD.CIF.CUSTOMER.MASTER", "CIF_ID") in ids
    jobs = {e["job_name"] for e in lineage["edges"]}
    assert jobs == {"TDFRAUD1", "TDCRDPST", "TDCUSLD1", "CUSTEXT1"}
    lookup = next(e for e in lineage["edges"] if e["job_name"] == "TDCRDPST")
    assert lookup["transformation"] == "Lookup on CARD_NUMBER"
    assert [j["name"] for j in lineage["focus"]["loaded_by"]] == ["TDFRAUD1"]

    one_level = service.get_column_lineage(MF, focus, "upstream", depth=1)
    assert {n["id"] for n in one_level["nodes"]} == {
        focus, column_node_id("CARDS_DB.CARD_TRANSACTIONS", "CUSTOMER_ID"),
    }


def test_column_lineage_downstream_fans_out(demo_db):
    lineage = ColumnLineageService(demo_db).get_column_lineage(
        AI, column_node_id("cards_cur.txn_enriched", "amount"), "downstream"
    )
    targets = {(n["dataset_name"], n["column"]) for n in lineage["nodes"]}
    assert ("risk_out.fraud_scores", "fraud_score") in targets
    assert ("analytics.customer_spend_monthly", "total_spend") in targets


def test_column_lineage_unknown_column(demo_db):
    with pytest.raises(KeyError):
        ColumnLineageService(demo_db).get_column_lineage(MF, "dataset:NOPE::X")


# ---------- input file validation ----------


def _write(base: Path, mapping_row: str, columns: str = "") -> Path:
    (base / "mainframe").mkdir(parents=True)
    (base / "mainframe/jobs.csv").write_text(
        "job_name,scheduler_system,schedule_name,last_run_status,expected_completion\n"
        "JOB1,CA-7,S1,SUCCESS,07:00\n"
    )
    (base / "mainframe/job_datasets.csv").write_text(
        "job_name,dataset_name,direction,dataset_type\n"
        "JOB1,PROD.IN.FILE,INPUT,PS\nJOB1,DW.OUT_TABLE,OUTPUT,TERADATA\n"
    )
    (base / "mainframe/column_lineage.csv").write_text(
        "job_name,source_dataset,source_column,target_dataset,target_column,transformation\n"
        + mapping_row
    )
    if columns:
        (base / "mainframe/table_columns.csv").write_text(
            "dataset_name,column_name,data_type\n" + columns
        )
    return base


def test_column_mapping_valid_case_insensitive(tmp_path):
    base = _write(tmp_path, "JOB1,prod.in.file,A,dw.out_table,B,\n")
    with CsvMainframeConnector(str(base)) as connector:
        assert len(connector.get_job_column_lineage("JOB1")) == 1
        assert connector.get_job_details("JOB1")["expected_completion"].hour == 7


@pytest.mark.parametrize(
    "row, message",
    [
        ("JOB1,OTHER.FILE,A,DW.OUT_TABLE,B,\n", "does not read 'OTHER.FILE'"),
        ("JOB1,PROD.IN.FILE,A,PROD.IN.FILE,B,\n", "does not write 'PROD.IN.FILE'"),
        ("NOPE,PROD.IN.FILE,A,DW.OUT_TABLE,B,\n", "'NOPE' is unknown"),
        ("JOB1,PROD.IN.FILE,,DW.OUT_TABLE,B,\n", "empty source_column"),
    ],
)
def test_column_mapping_errors(tmp_path, row, message):
    base = _write(tmp_path, row)
    with pytest.raises(LineageFileError, match=message):
        CsvMainframeConnector(str(base)).connect()


def test_duplicate_table_column(tmp_path):
    base = _write(tmp_path, "", columns="DW.OUT_TABLE,B,INT\ndw.out_table,b,INT\n")
    with pytest.raises(LineageFileError, match="duplicate column"):
        CsvMainframeConnector(str(base)).connect()


# ---------- routes ----------


@pytest.mark.asyncio
async def test_new_routes(demo_db):
    sla = await routes.get_job_lineage_sla(platform=MF, db=demo_db)
    assert sla["counts"]["LATE"] == 3

    found = await routes.search_job_lineage_columns(
        platform=AI, q="customer_id", exact=True, limit=200, db=demo_db
    )
    assert len(found) >= 5

    columns = await routes.get_job_lineage_table_columns(
        platform=AI, dataset="dataset:RISK_OUT.FRAUD_SCORES", db=demo_db
    )
    assert [c["column"] for c in columns] == ["customer_id", "txn_ts", "fraud_score"]

    lineage = await routes.get_job_lineage_column_lineage(
        platform=AI, column=columns[2]["id"], direction="both", depth=None, db=demo_db
    )
    assert lineage["edges"]

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_job_lineage_column_lineage(
            platform=AI, column="dataset:NOPE::X", direction="both", depth=None, db=demo_db
        )
    assert exc_info.value.status_code == 404

    with pytest.raises(HTTPException) as exc_info:
        await routes.get_job_lineage_sla(platform="NOPE", db=demo_db)
    assert exc_info.value.status_code == 400
