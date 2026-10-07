"""Cross-platform job lineage endpoints (mainframe/Teradata + Hadoop Ab Initio)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.services.abinitio_sync import create_abinitio_sync_service
from src.catalog.services.job_lineage import JobLineageService
from src.catalog.services.mainframe_sync import create_mainframe_sync_service
from src.connectors.abinitio import MockAbInitioConnector
from src.connectors.mainframe import MockMainframeConnector

router = APIRouter()


@router.get("/job-lineage/graph", response_model=dict)
async def get_job_lineage_graph(
    db: Session = Depends(get_db),
    platform: Optional[str] = Query(None, description="MAINFRAME or HADOOP_ABINITIO"),
    focus: Optional[str] = Query(None, description="Node id, e.g. job:12 or dataset:FIN_DB.GL"),
    direction: str = Query("both", pattern="^(upstream|downstream|both)$"),
    depth: Optional[int] = Query(None, ge=1, le=20, description="Job levels from focus"),
):
    """
    Get the job/dataset lineage graph.

    - **platform**: Restrict to one platform's jobs (and the datasets they touch)
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


@router.get("/job-lineage/impact", response_model=dict)
async def get_job_lineage_impact(
    node: str = Query(..., description="Node id, e.g. job:12"),
    db: Session = Depends(get_db),
):
    """Downstream blast radius of a job or dataset, plus failing/running upstream jobs."""
    service = JobLineageService(db)
    try:
        return service.get_impact(node)
    except KeyError:
        raise HTTPException(status_code=404, detail="Lineage node not found")


@router.post("/job-lineage/sync", response_model=dict)
async def sync_job_lineage(db: Session = Depends(get_db)):
    """
    Sync mainframe/Teradata jobs and Hadoop Ab Initio graphs into the catalog.

    Uses the mock connectors by default; swap in real ``BaseMainframeConnector``
    and ``BaseAbInitioConnector`` implementations to sync production metadata.
    """
    with MockMainframeConnector() as mainframe:
        mainframe_stats = create_mainframe_sync_service(db, mainframe).sync_all_jobs()
    with MockAbInitioConnector() as abinitio:
        abinitio_stats = create_abinitio_sync_service(db, abinitio).sync_all_graphs()

    return {"mainframe": mainframe_stats, "abinitio": abinitio_stats}
