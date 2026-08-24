"""Search and discovery endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from src.catalog.database import get_db
from src.catalog.services.search import SearchService

router = APIRouter()


@router.get("/search", response_model=dict)
async def global_search(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    asset_types: Optional[List[str]] = Query(None),
    database_id: Optional[int] = Query(None),
    limit: int = Query(100, ge=10, le=500),
):
    """
    Global search across all asset types.

    - **q**: Search query (required)
    - **asset_types**: Types to search (tables, columns, views, jobs, tags)
    - **database_id**: Filter by database
    - **limit**: Maximum results per type
    """
    search_service = SearchService(db)
    results = search_service.global_search(
        q,
        asset_types=asset_types,
        database_id=database_id,
        limit=limit,
    )
    return results


@router.get("/search/tables", response_model=list)
async def search_tables(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    database_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=10, le=500),
):
    """Search for tables by name or description."""
    search_service = SearchService(db)
    results = search_service.search_tables(q, database_id, limit)
    return results


@router.get("/search/columns", response_model=list)
async def search_columns(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    table_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=10, le=500),
):
    """Search for columns by name or description."""
    search_service = SearchService(db)
    results = search_service.search_columns(q, table_id, limit)
    return results


@router.get("/search/views", response_model=list)
async def search_views(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    database_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=10, le=500),
):
    """Search for views by name."""
    search_service = SearchService(db)
    results = search_service.search_views(q, database_id, limit)
    return results


@router.get("/search/jobs", response_model=list)
async def search_jobs(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=10, le=500),
):
    """Search for jobs by name or description."""
    search_service = SearchService(db)
    results = search_service.search_jobs(q, limit)
    return results


@router.get("/search/tags", response_model=list)
async def search_tags(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=10, le=500),
):
    """Search for assets by tags."""
    search_service = SearchService(db)
    results = search_service.search_tags(q, limit)
    return results


@router.get("/search/sensitive-data", response_model=list)
async def find_sensitive_data(db: Session = Depends(get_db)):
    """Find all sensitive columns in catalog."""
    search_service = SearchService(db)
    results = search_service.find_sensitive_data()
    return results


@router.get("/search/by-owner", response_model=dict)
async def find_by_owner(
    owner: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Find all assets owned by a specific person."""
    search_service = SearchService(db)
    results = search_service.find_by_owner(owner)
    return results


@router.get("/search/by-data-type", response_model=list)
async def search_by_data_type(
    data_type: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """Find all columns with a specific data type."""
    search_service = SearchService(db)
    results = search_service.search_by_data_type(data_type)
    return results


@router.get("/search/autocomplete", response_model=list)
async def autocomplete(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    asset_type: str = Query("table", regex="^(table|column|database|job)$"),
):
    """
    Autocomplete suggestions for search.

    - **q**: Partial query
    - **asset_type**: Type of asset (table, column, database, job)
    """
    search_service = SearchService(db)
    results = search_service.autocomplete_search(q, asset_type)
    return results
