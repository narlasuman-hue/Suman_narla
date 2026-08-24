"""Reporting and analytics endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta

from src.catalog.database import get_db
from src.catalog.models import Table, AssetStatus, AssetLifecycle
from src.catalog.utils import get_asset_summary

router = APIRouter()


@router.get("/reports/summary", response_model=dict)
async def get_summary(db: Session = Depends(get_db)):
    """Get overall catalog summary."""
    return get_asset_summary(db)


@router.get("/reports/asset-age", response_model=dict)
async def get_asset_age_distribution(db: Session = Depends(get_db)):
    """Get distribution of asset ages."""
    now = datetime.utcnow()

    recent_90d = db.query(func.count(Table.id)).filter(
        Table.created_at >= now - timedelta(days=90),
        Table.status == AssetStatus.ACTIVE,
    ).scalar() or 0

    recent_1y = db.query(func.count(Table.id)).filter(
        Table.created_at >= now - timedelta(days=365),
        Table.created_at < now - timedelta(days=90),
        Table.status == AssetStatus.ACTIVE,
    ).scalar() or 0

    older = db.query(func.count(Table.id)).filter(
        Table.created_at < now - timedelta(days=365),
        Table.status == AssetStatus.ACTIVE,
    ).scalar() or 0

    return {
        "last_90_days": recent_90d,
        "last_1_year": recent_1y,
        "older_than_1_year": older,
    }


@router.get("/reports/storage-usage", response_model=dict)
async def get_storage_usage(db: Session = Depends(get_db)):
    """Get storage usage statistics."""
    total_size_mb = (
        db.query(func.sum(Table.size_mb))
        .filter(Table.size_mb.isnot(None), Table.status == AssetStatus.ACTIVE)
        .scalar()
        or 0
    )

    by_status = {}
    for status in [AssetStatus.ACTIVE, AssetStatus.INACTIVE, AssetStatus.DEPRECATED]:
        size = (
            db.query(func.sum(Table.size_mb))
            .filter(Table.size_mb.isnot(None), Table.status == status)
            .scalar()
            or 0
        )
        by_status[status.value] = round(size, 2)

    return {
        "total_mb": round(total_size_mb, 2),
        "total_gb": round(total_size_mb / 1024, 2),
        "by_status": by_status,
    }


@router.get("/reports/tier-distribution", response_model=dict)
async def get_tier_distribution(db: Session = Depends(get_db)):
    """Get distribution of assets by tier."""
    from src.catalog.models import AssetTier

    tiers = {}
    for tier in AssetTier:
        count = db.query(func.count(AssetLifecycle.id)).filter(
            AssetLifecycle.tier == tier
        ).scalar() or 0
        tiers[tier.value] = count

    return {"tier_distribution": tiers}


@router.get("/reports/lifecycle-transitions", response_model=dict)
async def get_lifecycle_transitions(
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365),
):
    """Get recent lifecycle status transitions."""
    threshold_date = datetime.utcnow() - timedelta(days=days)

    transitions = db.query(AssetLifecycle).filter(
        AssetLifecycle.updated_at >= threshold_date
    ).all()

    by_status = {}
    for transition in transitions:
        status = transition.status.value
        by_status[status] = by_status.get(status, 0) + 1

    return {
        "days": days,
        "threshold_date": threshold_date.isoformat(),
        "total_transitions": len(transitions),
        "by_status": by_status,
    }


@router.get("/reports/most-used-tables", response_model=list)
async def get_most_used_tables(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    period: str = Query("30d", regex="^(7d|30d|90d)$"),
):
    """Get most frequently accessed tables."""
    from src.catalog.models import UsageMetrics

    period_map = {"7d": "access_count_7d", "30d": "access_count_30d", "90d": "access_count_90d"}
    access_column = getattr(UsageMetrics, period_map[period])

    tables = db.query(Table, UsageMetrics).join(UsageMetrics).order_by(
        access_column.desc()
    ).limit(limit).all()

    return [
        {
            "table_id": t.id,
            "name": t.name,
            "database": t.database.name if t.database else None,
            "access_count": getattr(u, period_map[period]),
            "last_accessed": u.last_accessed.isoformat() if u.last_accessed else None,
        }
        for t, u in tables
    ]


@router.get("/reports/least-used-tables", response_model=list)
async def get_least_used_tables(
    db: Session = Depends(get_db),
    limit: int = Query(10, ge=1, le=100),
    period: str = Query("90d", regex="^(7d|30d|90d)$"),
):
    """Get least frequently accessed tables."""
    from src.catalog.models import UsageMetrics

    period_map = {"7d": "access_count_7d", "30d": "access_count_30d", "90d": "access_count_90d"}
    access_column = getattr(UsageMetrics, period_map[period])

    tables = db.query(Table, UsageMetrics).join(UsageMetrics).order_by(
        access_column.asc()
    ).limit(limit).all()

    return [
        {
            "table_id": t.id,
            "name": t.name,
            "database": t.database.name if t.database else None,
            "access_count": getattr(u, period_map[period]),
            "last_accessed": u.last_accessed.isoformat() if u.last_accessed else None,
        }
        for t, u in tables
    ]


@router.get("/reports/data-quality-score", response_model=dict)
async def get_data_quality_score(db: Session = Depends(get_db)):
    """Get overall data quality score based on metadata completeness."""
    total_tables = db.query(func.count(Table.id)).scalar() or 1

    tables_with_description = db.query(func.count(Table.id)).filter(
        Table.description.isnot(None)
    ).scalar() or 0

    tables_with_owner = db.query(func.count(AssetLifecycle.id)).filter(
        AssetLifecycle.owner.isnot(None)
    ).scalar() or 0

    tables_with_usage = db.query(func.count(Table.id)).join(Table.usage).scalar() or 0

    description_pct = (tables_with_description / total_tables) * 100
    owner_pct = (tables_with_owner / total_tables) * 100
    usage_pct = (tables_with_usage / total_tables) * 100

    # Simple average score
    overall_score = (description_pct + owner_pct + usage_pct) / 3

    return {
        "overall_score": round(overall_score, 2),
        "description_coverage": round(description_pct, 2),
        "owner_assignment": round(owner_pct, 2),
        "usage_tracking": round(usage_pct, 2),
    }
