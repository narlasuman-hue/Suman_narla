"""Job lineage endpoints for the mainframe/Teradata and Hadoop/Ab Initio platforms."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.services.abinitio_sync import create_abinitio_sync_service
from src.catalog.services.job_lineage import JobLineageService
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.config import settings
from src.connectors.abinitio import MockAbInitioConnector
from src.connectors.lineage_files import (
    CsvAbInitioConnector,
    CsvMainframeConnector,
    LineageFileError,
    has_lineage_files,
)
from src.connectors.mainframe import MockMainframeConnector

router = APIRouter()


@router.get("/job-lineage/graph", response_model=dict)
async def get_job_lineage_graph(
    db: Session = Depends(get_db),
    platform: str = Query(..., description="MAINFRAME or HADOOP_ABINITIO"),
    focus: Optional[str] = Query(None, description="Node id, e.g. job:12 or dataset:FIN_DB.GL"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: Optional[int] = Query(None, ge=1, le=20, description="Job levels from focus"),
):
    """
    Get one platform's job/dataset lineage graph.

    - **platform**: MAINFRAME (mainframe jobs loading Teradata tables) or
      HADOOP_ABINITIO (Ab Initio graphs loading Hadoop tables)
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
    platform: str = Query(..., description="MAINFRAME or HADOOP_ABINITIO"),
    q: str = Query("", max_length=200, description="Part of the table name"),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    Search the platform's tables by name.

    MAINFRAME searches Teradata tables (loaded by mainframe jobs);
    HADOOP_ABINITIO searches Hive/HDFS tables (loaded by Ab Initio graphs).
    Each result includes the jobs that load and read the table.
    """
    service = JobLineageService(db)
    try:
        return service.search_tables(platform, q, limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/job-lineage/impact", response_model=dict)
async def get_job_lineage_impact(
    platform: str = Query(..., description="MAINFRAME or HADOOP_ABINITIO"),
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
    Sync mainframe/Teradata jobs and Hadoop Ab Initio graphs into the catalog.

    Reads the CSV input files in ``settings.lineage_data_dir`` when they exist
    (see docs/JOB_LINEAGE_DEMO_DATA.md), otherwise the built-in sample data.
    Swap in real ``BaseMainframeConnector`` / ``BaseAbInitioConnector``
    implementations to sync production metadata.
    """
    data_dir = settings.lineage_data_dir
    if has_lineage_files(data_dir):
        source = f"files:{data_dir}"
        mainframe, abinitio = CsvMainframeConnector(data_dir), CsvAbInitioConnector(data_dir)
    else:
        source = "sample"
        mainframe, abinitio = MockMainframeConnector(), MockAbInitioConnector()

    try:
        with mainframe:
            mainframe_stats = create_mainframe_sync_service(db, mainframe).sync_all_jobs()
        with abinitio:
            abinitio_stats = create_abinitio_sync_service(db, abinitio).sync_all_graphs()
    except LineageFileError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Invalid lineage input file: {e}")

    return {"source": source, "mainframe": mainframe_stats, "abinitio": abinitio_stats}
