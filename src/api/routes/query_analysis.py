"""Query log analysis and performance endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.models import Table
from src.catalog.services.query_log import QueryLogParser

router = APIRouter()


@router.post("/analysis/parse-logs", response_model=dict)
async def parse_query_logs(
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=720),
):
    """
    Parse Teradata query logs and update usage metrics.

    - **hours**: Hours of logs to analyze (default: 24, max: 30 days)
    """
    try:
        from src.connectors.teradata import TeradataConnector
        from src.config import settings

        connector = TeradataConnector(
            host=settings.teradata_host,
            port=settings.teradata_port,
            user=settings.teradata_user,
            password=settings.teradata_password,
            database=settings.teradata_database,
        )
        connector.connect()

        parser = QueryLogParser(db, connector)
        stats = parser.parse_query_logs(hours)
        connector.disconnect()

        return {
            "status": "success",
            "hours_analyzed": hours,
            **stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing logs: {str(e)}")


@router.get("/analysis/table/{table_id}/patterns", response_model=dict)
async def get_query_patterns(
    table_id: int,
    db: Session = Depends(get_db),
    hours: int = Query(24, ge=1, le=168),
):
    """
    Get query patterns for a specific table.

    - **table_id**: Table ID
    - **hours**: Hours of history to analyze
    """
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        from src.connectors.teradata import TeradataConnector
        from src.config import settings

        connector = TeradataConnector(
            host=settings.teradata_host,
            port=settings.teradata_port,
            user=settings.teradata_user,
            password=settings.teradata_password,
            database=settings.teradata_database,
        )
        connector.connect()

        parser = QueryLogParser(db, connector)
        patterns = parser.get_query_patterns(table_id, hours)
        connector.disconnect()

        return patterns
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error analyzing patterns: {str(e)}")


@router.get("/analysis/heavy-users", response_model=list)
async def get_heavy_users(
    db: Session = Depends(get_db),
):
    """Get top users with most table access in the last 24 hours."""
    try:
        from src.connectors.teradata import TeradataConnector
        from src.config import settings

        connector = TeradataConnector(
            host=settings.teradata_host,
            port=settings.teradata_port,
            user=settings.teradata_user,
            password=settings.teradata_password,
            database=settings.teradata_database,
        )
        connector.connect()

        parser = QueryLogParser(db, connector)
        users = parser.identify_heavy_users()
        connector.disconnect()

        return users
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error identifying users: {str(e)}")


@router.get("/analysis/table/{table_id}/performance", response_model=dict)
async def get_query_performance(
    table_id: int,
    db: Session = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get query performance statistics for a table.

    - **table_id**: Table ID
    - **limit**: Maximum number of queries to return
    """
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    try:
        from src.connectors.teradata import TeradataConnector
        from src.config import settings

        connector = TeradataConnector(
            host=settings.teradata_host,
            port=settings.teradata_port,
            user=settings.teradata_user,
            password=settings.teradata_password,
            database=settings.teradata_database,
        )
        connector.connect()

        parser = QueryLogParser(db, connector)
        performance = parser.get_query_performance(table_id, limit)
        connector.disconnect()

        return performance
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting performance: {str(e)}")
