"""Job lineage endpoints, each for one configured platform (see /job-lineage/platforms)."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.platforms import PlatformConfigError, load_platforms
from src.catalog.services.abinitio_sync import create_abinitio_sync_service
from src.catalog.services.column_lineage import ColumnLineageService
from src.catalog.services.job_lineage import JobLineageService
from src.catalog.services.lineage_sync import LineageSyncService
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.config import settings
from src.connectors.abinitio import MockAbInitioConnector
from src.connectors.lineage_files import (
    CsvLineageConnector,
    LineageFileError,
    has_lineage_files,
)
from src.connectors.mainframe import MockMainframeConnector

router = APIRouter()

PLATFORM_HELP = "Platform id, e.g. MAINFRAME (see GET /job-lineage/platforms)"


@router.get("/job-lineage/platforms", response_model=List[dict])
async def list_job_lineage_platforms(db: Session = Depends(get_db)):
    """
    The configured platforms (from ``platforms.csv``), each with a short summary:
    number of jobs, failed and running jobs, and jobs late against their SLA.
    """
    try:
        platforms = load_platforms()
    except PlatformConfigError as e:
        raise HTTPException(status_code=500, detail=f"Invalid platforms file: {e}")
    service = JobLineageService(db)
    result = []
    for platform in platforms:
        summary = service.get_graph(platform.id)["summary"]
        result.append(
            {
                **platform.to_dict(),
                "summary": {
                    "jobs": summary["jobs"],
                    "failed": len(summary["failed_jobs"]),
                    "running": len(summary["running_jobs"]),
                    "sla_late": summary["sla_late"],
                },
            }
        )
    return result


@router.get("/job-lineage/graph", response_model=dict)
async def get_job_lineage_graph(
    db: Session = Depends(get_db),
    platform: str = Query(..., description=PLATFORM_HELP),
    focus: Optional[str] = Query(None, description="Node id, e.g. job:12 or dataset:FIN_DB.GL"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: Optional[int] = Query(None, ge=1, le=20, description="Job levels from focus"),
):
    """
    Get one platform's job/dataset lineage graph.

    - **platform**: a configured platform id, e.g. MAINFRAME
    - **focus**: Only return nodes connected to this node
    - **direction**: With focus, follow upstream, downstream, or both
    - **depth**: With focus, how many job levels to follow (default: unlimited)
    """
    service = JobLineageService(db)
    try:
        return service.get_graph(platform=platform, focus=focus, direction=direction, depth=depth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Lineage node not found")


@router.get("/job-lineage/tables", response_model=List[dict])
async def search_job_lineage_tables(
    platform: str = Query(..., description=PLATFORM_HELP),
    q: str = Query("", max_length=200, description="Part of the table name"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Search the platform's tables by name.

    Tables are the datasets whose type is one of the platform's ``table_types``
    (e.g. Teradata tables for MAINFRAME, Hive/HDFS for HADOOP_ABINITIO).
    Each result includes the jobs that load and read the table.
    """
    service = JobLineageService(db)
    try:
        return service.search_tables(platform, q, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-lineage/sla", response_model=dict)
async def get_job_lineage_sla(
    platform: str = Query(..., description=PLATFORM_HELP),
    db: Session = Depends(get_db),
):
    """
    SLA tracking: each job with an expected completion time, worst first.

    Status is LATE, COMPLETED_LATE, AT_RISK, ON_TRACK or MET; ``blocked_by``
    lists failed/running upstream jobs (the usual root cause).
    """
    try:
        return JobLineageService(db).get_sla(platform)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-lineage/columns", response_model=List[dict])
async def search_job_lineage_columns(
    platform: str = Query(..., description=PLATFORM_HELP),
    q: str = Query(..., min_length=1, max_length=200, description="Column name or part of it"),
    exact: bool = Query(False, description="Match the whole column name"),
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Every table that has a matching column, with its database and load/read jobs."""
    try:
        return ColumnLineageService(db).search_columns(platform, q, exact, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-lineage/table-columns", response_model=List[dict])
async def get_job_lineage_table_columns(
    platform: str = Query(..., description=PLATFORM_HELP),
    dataset: str = Query(..., description="Dataset node id, e.g. dataset:FINANCE_DB.GL_POSTINGS"),
    db: Session = Depends(get_db),
):
    """Columns of one table/dataset."""
    try:
        return ColumnLineageService(db).list_table_columns(platform, dataset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-lineage/column-lineage", response_model=dict)
async def get_job_lineage_column_lineage(
    platform: str = Query(..., description=PLATFORM_HELP),
    column: str = Query(..., description="Column id, e.g. dataset:CARDS_DB.TXNS::TXN_ID"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: Optional[int] = Query(None, ge=1, le=20, description="Job levels from the column"),
    db: Session = Depends(get_db),
):
    """Column-level lineage: source columns feeding this column and columns it feeds."""
    try:
        return ColumnLineageService(db).get_column_lineage(platform, column, direction, depth)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Column not found")


@router.get("/job-lineage/impact", response_model=dict)
async def get_job_lineage_impact(
    platform: str = Query(..., description=PLATFORM_HELP),
    node: str = Query(..., description="Node id, e.g. job:12"),
    db: Session = Depends(get_db),
):
    """Downstream blast radius of a job or dataset, plus failing/running upstream jobs."""
    service = JobLineageService(db)
    try:
        return service.get_impact(platform, node)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=404, detail="Lineage node not found")


@router.post("/job-lineage/sync", response_model=dict)
async def sync_job_lineage(db: Session = Depends(get_db)):
    """
    Sync every configured platform's jobs into the catalog.

    Reads ``platforms.csv`` and each platform's CSV folder in
    ``settings.lineage_data_dir`` when they exist (see docs/JOB_LINEAGE_DEMO_DATA.md),
    otherwise the built-in mainframe and Ab Initio sample data. For production,
    implement ``BaseLineageConnector`` for a platform's real source.
    """
    data_dir = settings.lineage_data_dir
    results = {}
    try:
        if has_lineage_files(data_dir):
            source = f"files:{data_dir}"
            for platform in load_platforms(data_dir):
                with CsvLineageConnector(data_dir, platform.folder) as connector:
                    results[platform.id] = LineageSyncService(db, platform.id, connector).sync_all()
        else:
            source = "sample"
            with MockMainframeConnector() as mainframe:
                results["MAINFRAME"] = create_mainframe_sync_service(db, mainframe).sync_all_jobs()
            with MockAbInitioConnector() as abinitio:
                results["HADOOP_ABINITIO"] = create_abinitio_sync_service(
                    db, abinitio
                ).sync_all_graphs()
    except (LineageFileError, PlatformConfigError) as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid lineage input file: {e}")

    return {
        "source": source,
        "platforms": results,
        "jobs_synced": sum(r["jobs_created"] + r["jobs_updated"] for r in results.values()),
    }
