"""Database inventory endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional

from src.catalog.database import get_db
from src.catalog.models import Database, AssetStatus

router = APIRouter()


class DatabaseResponse:
    """Database response schema."""
    id: int
    name: str
    owner: Optional[str]
    description: Optional[str]
    status: str
    created_at: str
    last_synced: str


@router.get("/databases", response_model=List[dict])
async def list_databases(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """
    List all databases.

    - **status**: Filter by asset status (active, inactive, deprecated, decommissioned)
    - **skip**: Number of records to skip
    - **limit**: Maximum number of records to return
    """
    query = select(Database)

    if status:
        try:
            asset_status = AssetStatus(status)
            query = query.where(Database.status == asset_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    query = query.offset(skip).limit(limit)
    databases = db.execute(query).scalars().all()

    return [
        {
            "id": db.id,
            "name": db.name,
            "owner": db.owner,
            "description": db.description,
            "status": db.status.value,
            "created_at": db.created_at.isoformat(),
            "last_synced": db.last_synced.isoformat(),
        }
        for db in databases
    ]


@router.get("/databases/{database_id}", response_model=dict)
async def get_database(database_id: int, db: Session = Depends(get_db)):
    """Get database details by ID."""
    database = db.get(Database, database_id)
    if not database:
        raise HTTPException(status_code=404, detail="Database not found")

    return {
        "id": database.id,
        "name": database.name,
        "owner": database.owner,
        "description": database.description,
        "status": database.status.value,
        "created_at": database.created_at.isoformat(),
        "last_synced": database.last_synced.isoformat(),
        "table_count": len(database.tables),
        "view_count": len(database.views),
    }


@router.post("/databases", response_model=dict, status_code=201)
async def create_database(
    name: str,
    owner: Optional[str] = None,
    description: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Create a new database record."""
    existing = db.query(Database).filter(Database.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Database already exists")

    database = Database(
        name=name,
        owner=owner,
        description=description,
        status=AssetStatus.ACTIVE,
    )
    db.add(database)
    db.commit()
    db.refresh(database)

    return {
        "id": database.id,
        "name": database.name,
        "owner": database.owner,
        "description": database.description,
        "status": database.status.value,
        "created_at": database.created_at.isoformat(),
    }
