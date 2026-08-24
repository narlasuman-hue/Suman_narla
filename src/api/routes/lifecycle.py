"""Asset lifecycle management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional
from datetime import datetime

from src.catalog.database import get_db
from src.catalog.models import AssetLifecycle, Table, AssetStatus, AssetTier
from src.catalog.utils import (
    mark_asset_for_decommissioning,
    decommission_asset,
    get_unused_assets,
    get_decommissioning_candidates,
)

router = APIRouter()


@router.get("/lifecycle/summary", response_model=dict)
async def get_lifecycle_summary(db: Session = Depends(get_db)):
    """Get summary of assets by lifecycle status."""
    active = db.query(Table).filter(Table.status == AssetStatus.ACTIVE).count()
    inactive = db.query(Table).filter(Table.status == AssetStatus.INACTIVE).count()
    deprecated = db.query(Table).filter(Table.status == AssetStatus.DEPRECATED).count()
    decommissioned = db.query(Table).filter(
        Table.status == AssetStatus.DECOMMISSIONED
    ).count()

    return {
        "active": active,
        "inactive": inactive,
        "deprecated": deprecated,
        "decommissioned": decommissioned,
        "total": active + inactive + deprecated + decommissioned,
    }


@router.get("/lifecycle/unused-assets", response_model=dict)
async def get_unused(
    db: Session = Depends(get_db),
    days: int = Query(90, ge=1),
):
    """Get assets unused for specified number of days."""
    result = get_unused_assets(db, days)
    return result


@router.get("/lifecycle/decommissioning-candidates", response_model=dict)
async def get_candidates(
    db: Session = Depends(get_db),
    days: int = Query(180, ge=1),
):
    """Get candidates for decommissioning based on usage."""
    result = get_decommissioning_candidates(db, days)
    return result


@router.get("/lifecycle/assets", response_model=List[dict])
async def list_lifecycle_assets(
    db: Session = Depends(get_db),
    status: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
):
    """List assets with lifecycle information."""
    query = select(AssetLifecycle)

    if status:
        try:
            asset_status = AssetStatus(status)
            query = query.where(AssetLifecycle.status == asset_status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    if tier:
        try:
            asset_tier = AssetTier(tier)
            query = query.where(AssetLifecycle.tier == asset_tier)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tier value")

    query = query.offset(skip).limit(limit)
    lifecycles = db.execute(query).scalars().all()

    return [
        {
            "id": lc.id,
            "asset_type": lc.asset_type,
            "status": lc.status.value,
            "tier": lc.tier.value,
            "owner": lc.owner,
            "created_date": lc.created_date.isoformat(),
            "decommissioned_date": lc.decommissioned_date.isoformat()
            if lc.decommissioned_date
            else None,
            "decommissioning_reason": lc.decommissioning_reason,
            "last_reviewed": lc.last_reviewed.isoformat() if lc.last_reviewed else None,
            "table_id": lc.table_id,
            "table_name": lc.table.name if lc.table else None,
        }
        for lc in lifecycles
    ]


@router.patch("/lifecycle/assets/{lifecycle_id}", response_model=dict)
async def update_lifecycle(
    lifecycle_id: int,
    owner: Optional[str] = None,
    tier: Optional[str] = None,
    status: Optional[str] = None,
    review_notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Update asset lifecycle information."""
    lifecycle = db.get(AssetLifecycle, lifecycle_id)
    if not lifecycle:
        raise HTTPException(status_code=404, detail="Lifecycle record not found")

    if owner:
        lifecycle.owner = owner

    if tier:
        try:
            lifecycle.tier = AssetTier(tier)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid tier value")

    if status:
        try:
            lifecycle.status = AssetStatus(status)
            if lifecycle.table:
                lifecycle.table.status = AssetStatus(status)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status value")

    if review_notes:
        lifecycle.review_notes = review_notes
        lifecycle.last_reviewed = datetime.utcnow()

    db.commit()
    db.refresh(lifecycle)

    return {
        "id": lifecycle.id,
        "asset_type": lifecycle.asset_type,
        "status": lifecycle.status.value,
        "tier": lifecycle.tier.value,
        "owner": lifecycle.owner,
        "updated_at": lifecycle.updated_at.isoformat(),
    }


@router.post("/lifecycle/assets/{table_id}/deprecate", response_model=dict)
async def mark_deprecated(
    table_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Mark an asset as deprecated."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if mark_asset_for_decommissioning(db, table_id, reason):
        return {
            "id": table_id,
            "name": table.name,
            "status": "deprecated",
            "reason": reason,
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to mark as deprecated")


@router.post("/lifecycle/assets/{table_id}/decommission", response_model=dict)
async def decommission_table(
    table_id: int,
    reason: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Decommission an asset."""
    table = db.get(Table, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Table not found")

    if decommission_asset(db, table_id, reason):
        return {
            "id": table_id,
            "name": table.name,
            "status": "decommissioned",
            "decommissioned_date": datetime.utcnow().isoformat(),
            "reason": reason,
        }
    else:
        raise HTTPException(status_code=400, detail="Failed to decommission")
