"""Table inventory endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from src.catalog.database import get_db
from src.catalog.models import Table, Column, Database, AssetStatus

router = APIRouter()


@router.get("/tables", response_model=List[dict])
async def list_tables(
    db: Session = Depends(get_db),
    database_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List all tables.

    - **database_id**: Filter by database ID
    - **status**: Filter by asset status
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    query = select(Table)

    if database_id:
        query = query.where(Table.db_id == database_id)

    if status:
        try:
            asset_status = AssetStatus(status)
            query = query.where(Table.status == asset_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    query = query.offset(skip).limit(limit)
    tables = db.execute(query).scalars().all()

    return [
        {
            "id": t.id,
            "database_id": t.db_id,
            "name": t.name,
            "type": t.table_type,
            "status": t.status.value,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "last_accessed": t.last_accessed.isoformat() if t.last_accessed else None,
            "row_count": t.row_count,
            "size_mb": t.size_mb,
            "column_count": len(t.columns),
        }
        for t in tables
    ]


@router.get("/tables/{table_id}", response_model=dict)
async def get_table(table_id: int, db: Session = Depends(get_db)):
    """Get table details by ID."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return {
        "id": table.id,
        "database_id": table.db_id,
        "name": table.name,
        "type": table.table_type,
        "status": table.status.value,
        "description": table.description,
        "created_at": table.created_at.isoformat() if table.created_at else None,
        "last_accessed": table.last_accessed.isoformat() if table.last_accessed else None,
        "last_modified": table.last_modified.isoformat() if table.last_modified else None,
        "row_count": table.row_count,
        "size_mb": table.size_mb,
        "column_count": len(table.columns),
        "columns": [
            {
                "id": c.id,
                "name": c.name,
                "data_type": c.data_type,
                "nullable": c.nullable,
                "sensitive": c.sensitive_flag,
                "description": c.description,
                "position": c.position,
            }
            for c in table.columns
        ],
    }


@router.get("/tables/{table_id}/columns", response_model=List[dict])
async def get_table_columns(table_id: int, db: Session = Depends(get_db)):
    """Get columns for a specific table."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    return [
        {
            "id": c.id,
            "name": c.name,
            "data_type": c.data_type,
            "nullable": c.nullable,
            "sensitive": c.sensitive_flag,
            "description": c.description,
            "position": c.position,
        }
        for c in table.columns
    ]


@router.get("/tables/{table_id}/usage", response_model=dict)
async def get_table_usage(table_id: int, db: Session = Depends(get_db)):
    """Get usage metrics for a table."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if not table.usage:
        return {
            "table_id": table_id,
            "last_accessed": None,
            "access_count_7d": 0,
            "access_count_30d": 0,
            "access_count_90d": 0,
            "total_access_count": 0,
        }

    return {
        "table_id": table_id,
        "last_accessed": table.usage.last_accessed.isoformat() if table.usage.last_accessed else None,
        "access_count_7d": table.usage.access_count_7d,
        "access_count_30d": table.usage.access_count_30d,
        "access_count_90d": table.usage.access_count_90d,
        "total_access_count": table.usage.total_access_count,
    }


@router.post("/tables", response_model=dict, status_code=201)
async def create_table(
    database_id: int,
    name: str,
    table_type: str = "PERMANENT",
    description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new table record."""
    database = db.get(Database, database_id)
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")

    existing = db.query(Table).filter(
        Table.db_id == database_id,
        Table.name == name
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Table already exists in this database")

    table = Table(
        db_id=database_id,
        name=name,
        table_type=table_type,
        description=description,
        status=AssetStatus.ACTIVE,
    )
    db.add(table)
    db.commit()
    db.refresh(table)

    return {
        "id": table.id,
        "database_id": table.db_id,
        "name": table.name,
        "type": table.table_type,
        "status": table.status.value,
        "created_at": table.created_at.isoformat(),
    }
