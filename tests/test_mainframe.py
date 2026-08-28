"""Tests for mainframe job/file/schedule sync and endpoints."""

import pytest
from fastapi import HTTPException

from src.api.routes import mainframe as mainframe_routes
from src.catalog.models import Job, JobFile
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.connectors.mainframe import MockMainframeConnector


@pytest.fixture
def connector():
    connector = MockMainframeConnector()
    connector.connect()
    yield connector
    connector.disconnect()


def test_mock_connector_lists_jobs(connector):
    jobs = connector.get_jobs()
    assert len(jobs) == 3
    assert any(j["job_name"] == "PAYRDLY1" for j in jobs)


def test_mock_connector_job_files(connector):
    files = connector.get_job_files("PAYRDLY1")
    assert len(files) == 3
    assert any(f["dataset_name"] == "PROD.PAYROLL.EMPLOYEE.MASTER" for f in files)


def test_mock_connector_job_schedule(connector):
    schedule = connector.get_job_schedule("PAYRDLY1")
    assert schedule["scheduler_system"] == "CA-7"
    assert schedule["schedule_name"] == "PAYROLL-DAILY"


def test_mock_connector_unknown_job_raises(connector):
    with pytest.raises(KeyError):
        connector.get_job_details("NOSUCHJOB")


def test_sync_creates_jobs_and_files(db, connector):
    sync_service = create_mainframe_sync_service(db, connector)
    stats = sync_service.sync_all_jobs()

    assert stats["jobs_created"] == 3
    assert stats["jobs_updated"] == 0
    assert stats["errors"] == []

    jobs = db.query(Job).filter(Job.source_system == "MAINFRAME").all()
    assert len(jobs) == 3

    payroll_job = db.query(Job).filter(Job.name == "PAYRDLY1").first()
    assert payroll_job is not None
    assert payroll_job.scheduler_system == "CA-7"
    assert payroll_job.schedule_name == "PAYROLL-DAILY"

    files = db.query(JobFile).filter(JobFile.job_id == payroll_job.id).all()
    assert len(files) == 3


def test_sync_is_idempotent(db, connector):
    sync_service = create_mainframe_sync_service(db, connector)
    sync_service.sync_all_jobs()

    first_count = db.query(Job).filter(Job.source_system == "MAINFRAME").count()

    stats = sync_service.sync_all_jobs()
    second_count = db.query(Job).filter(Job.source_system == "MAINFRAME").count()

    assert first_count == second_count == 3
    assert stats["jobs_created"] == 0
    assert stats["jobs_updated"] == 3


# The shared `client` fixture runs the FastAPI app's TestClient against a
# SQLite in-memory session created on another thread, which SQLite forbids
# (see tests/conftest.py) -- a pre-existing limitation of the test setup, not
# specific to this feature. Route handlers are exercised directly instead,
# reusing the same `db` fixture.


@pytest.mark.asyncio
async def test_list_mainframe_jobs_route(db):
    await mainframe_routes.sync_mainframe_jobs(db)

    jobs = await mainframe_routes.list_mainframe_jobs(
        db=db, status=None, schedule_name=None, skip=0, limit=50
    )
    assert len(jobs) == 3
    assert all(j["schedule_name"] for j in jobs)


@pytest.mark.asyncio
async def test_get_mainframe_job_files_route(db):
    await mainframe_routes.sync_mainframe_jobs(db)
    jobs = await mainframe_routes.list_mainframe_jobs(
        db=db, status=None, schedule_name=None, skip=0, limit=50
    )
    job_id = jobs[0]["id"]

    files = await mainframe_routes.get_mainframe_job_files(job_id, db)
    assert len(files) > 0
    assert "dataset_name" in files[0]


@pytest.mark.asyncio
async def test_get_mainframe_job_schedule_route(db):
    await mainframe_routes.sync_mainframe_jobs(db)
    jobs = await mainframe_routes.list_mainframe_jobs(
        db=db, status=None, schedule_name=None, skip=0, limit=50
    )
    job_id = jobs[0]["id"]

    schedule = await mainframe_routes.get_mainframe_job_schedule(job_id, db)
    assert schedule["schedule_name"]
    assert schedule["scheduler_system"]


@pytest.mark.asyncio
async def test_get_mainframe_job_not_found_route(db):
    with pytest.raises(HTTPException) as exc_info:
        await mainframe_routes.get_mainframe_job(999999, db)
    assert exc_info.value.status_code == 404
