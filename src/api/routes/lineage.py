"""Data lineage and impact analysis endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from src.catalog.database import get_db
from src.catalog.models import Table
from src.catalog.services.lineage import LineageGraph, ImpactAnalyzer, LineageExtractor

router = APIRouter()


@router.get("/lineage/{table_id}/upstream", response_model=dict)
async def get_upstream_lineage(
    table_id: int,
    db: Session = Depends(get_db),
    max_depth: int = Query(5, ge=1, le=10),
):
    """Get upstream dependencies for a table (sources)."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    graph = LineageGraph(db)
    lineage = graph.get_upstream_lineage(table_id, max_depth)

    return {
        "table_id": table_id,
        "table_name": table.name,
        "database": table.database.name if table.database else None,
        "upstream": lineage["lineage"],
        "depth": max_depth,
    }


@router.get("/lineage/{table_id}/downstream", response_model=dict)
async def get_downstream_lineage(
    table_id: int,
    db: Session = Depends(get_db),
    max_depth: int = Query(5, ge=1, le=10),
):
    """Get downstream dependencies for a table (targets)."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    graph = LineageGraph(db)
    lineage = graph.get_downstream_lineage(table_id, max_depth)

    return {
        "table_id": table_id,
        "table_name": table.name,
        "database": table.database.name if table.database else None,
        "downstream": lineage["lineage"],
        "depth": max_depth,
    }


@router.get("/lineage/{table_id}/full", response_model=dict)
async def get_full_lineage(
    table_id: int,
    db: Session = Depends(get_db),
    max_depth: int = Query(3, ge=1, le=5),
):
    """Get complete lineage graph (upstream and downstream)."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    graph = LineageGraph(db)
    lineage = graph.get_full_lineage(table_id, max_depth)

    return {
        "table_id": table_id,
        "table_name": table.name,
        "database": table.database.name if table.database else None,
        "upstream": lineage["upstream"],
        "downstream": lineage["downstream"],
        "depth": max_depth,
    }


@router.post("/lineage/extract-from-sql", response_model=dict)
async def extract_lineage_from_sql(
    sql: str,
    db: Session = Depends(get_db),
):
    """Extract table references and lineage from SQL query."""
    extractor = LineageExtractor(db)
    parsed = extractor.parse_query(sql)

    # Find tables in catalog
    sources = []
    for source in parsed['sources']:
        table = extractor.find_table_by_name(source.get('database'), source.get('table'))
        sources.append({
            'database': source.get('database'),
            'table': source.get('table'),
            'found_in_catalog': table is not None,
            'table_id': table.id if table else None,
        })

    targets = []
    for target in parsed['targets']:
        table = extractor.find_table_by_name(target.get('database'), target.get('table'))
        targets.append({
            'database': target.get('database'),
            'table': target.get('table'),
            'found_in_catalog': table is not None,
            'table_id': table.id if table else None,
        })

    return {
        'query_type': parsed['type'],
        'sources': sources,
        'targets': targets,
    }


@router.post("/lineage/create-from-sql", response_model=dict)
async def create_lineage_from_sql(
    sql: str,
    job_id: int = Query(None),
    db: Session = Depends(get_db),
):
    """Create lineage records from a SQL query."""
    extractor = LineageExtractor(db)
    result = extractor.create_lineage_from_query(sql, job_id)

    return {
        'created': result['created'],
        'errors': result['errors'],
    }


@router.get("/impact/{table_id}", response_model=dict)
async def get_impact_of_change(
    table_id: int,
    db: Session = Depends(get_db),
):
    """Get all tables impacted by changes to a specific table."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    analyzer = ImpactAnalyzer(db)
    impact = analyzer.get_impact_of_change(table_id)

    return {
        "source_table": {
            "id": table.id,
            "name": table.name,
            "database": table.database.name if table.database else None,
        },
        **impact,
    }


@router.get("/dependencies/{table_id}", response_model=dict)
async def get_table_dependencies(
    table_id: int,
    db: Session = Depends(get_db),
):
    """Get all tables this table depends on."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    analyzer = ImpactAnalyzer(db)
    dependencies = analyzer.get_dependencies(table_id)

    return {
        "table": {
            "id": table.id,
            "name": table.name,
            "database": table.database.name if table.database else None,
        },
        **dependencies,
    }


@router.get("/drop-safety/{table_id}", response_model=dict)
async def check_drop_safety(
    table_id: int,
    db: Session = Depends(get_db),
):
    """Check if a table can be safely dropped."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    analyzer = ImpactAnalyzer(db)
    safety = analyzer.can_safely_drop(table_id)

    return {
        "table": {
            "id": table.id,
            "name": table.name,
            "database": table.database.name if table.database else None,
        },
        **safety,
    }
