"""Utility functions for catalog operations."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.catalog.models import Table, UsageMetrics, AssetStatus, AssetLifecycle

logger_utils = __import__('logging').getLogger(__name__)


def get_unused_assets(db: Session, days: int = 90) -> dict:
    """Get assets not accessed for specified days."""
    threshold_date = datetime.utcnow() - timedelta(days=days)

    unused_tables = db.query(Table).filter(
        (Table.last_accessed < threshold_date) | (Table.last_accessed.is_(None)),
        Table.status == AssetStatus.ACTIVE,
    ).all()

    return {
        "threshold_date": threshold_date,
        "days": days,
        "unused_table_count": len(unused_tables),
        "unused_tables": [
            {
                "id": t.id,
                "name": t.name,
                "database": t.database.name if t.database else None,
                "last_accessed": t.last_accessed.isoformat() if t.last_accessed else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in unused_tables
        ],
    }


def get_decommissioning_candidates(db: Session, days: int = 180) -> dict:
    """Get assets as candidates for decommissioning based on usage."""
    threshold_date = datetime.utcnow() - timedelta(days=days)

    candidates = db.query(Table).filter(
        (Table.last_accessed < threshold_date) | (Table.last_accessed.is_(None)),
        Table.status == AssetStatus.ACTIVE,
    ).all()

    return {
        "threshold_date": threshold_date,
        "days": days,
        "candidate_count": len(candidates),
        "candidates": [
            {
                "id": t.id,
                "name": t.name,
                "database": t.database.name if t.database else None,
                "last_accessed": t.last_accessed.isoformat() if t.last_accessed else None,
                "size_mb": t.size_mb,
                "row_count": t.row_count,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "lifecycle_status": t.lifecycle.status.value if t.lifecycle else None,
            }
            for t in candidates
        ],
    }


def mark_asset_for_decommissioning(
    db: Session,
    table_id: int,
    reason: str = None,
) -> bool:
    """Mark an asset for decommissioning."""
    try:
        table = db.query(Table).filter(Table.id == table_id).first()
        if not table:
            return False

        table.status = AssetStatus.DEPRECATED

        if table.lifecycle:
            table.lifecycle.status = AssetStatus.DEPRECATED
            table.lifecycle.decommissioning_reason = reason
        else:
            lifecycle = AssetLifecycle(
                table_id=table.id,
                asset_type="TABLE",
                created_date=table.created_at or datetime.utcnow(),
                status=AssetStatus.DEPRECATED,
                decommissioning_reason=reason,
            )
            db.add(lifecycle)

        db.commit()
        logger_utils.info(f"Marked table {table.name} for decommissioning")
        return True
    except Exception as e:
        logger_utils.error(f"Error marking asset for decommissioning: {e}")
        db.rollback()
        return False


def decommission_asset(
    db: Session,
    table_id: int,
    reason: str = None,
) -> bool:
    """Decommission an asset."""
    try:
        table = db.query(Table).filter(Table.id == table_id).first()
        if not table:
            return False

        table.status = AssetStatus.DECOMMISSIONED

        if table.lifecycle:
            table.lifecycle.status = AssetStatus.DECOMMISSIONED
            table.lifecycle.decommissioned_date = datetime.utcnow()
            table.lifecycle.decommissioning_reason = reason
        else:
            lifecycle = AssetLifecycle(
                table_id=table.id,
                asset_type="TABLE",
                created_date=table.created_at or datetime.utcnow(),
                status=AssetStatus.DECOMMISSIONED,
                decommissioned_date=datetime.utcnow(),
                decommissioning_reason=reason,
            )
            db.add(lifecycle)

        db.commit()
        logger_utils.info(f"Decommissioned table {table.name}")
        return True
    except Exception as e:
        logger_utils.error(f"Error decommissioning asset: {e}")
        db.rollback()
        return False


def get_asset_summary(db: Session) -> dict:
    """Get summary statistics of all assets."""
    try:
        total_tables = db.query(func.count(Table.id)).scalar() or 0
        active_tables = (
            db.query(func.count(Table.id))
            .filter(Table.status == AssetStatus.ACTIVE)
            .scalar()
            or 0
        )
        inactive_tables = (
            db.query(func.count(Table.id))
            .filter(Table.status == AssetStatus.INACTIVE)
            .scalar()
            or 0
        )
        deprecated_tables = (
            db.query(func.count(Table.id))
            .filter(Table.status == AssetStatus.DEPRECATED)
            .scalar()
            or 0
        )
        decommissioned_tables = (
            db.query(func.count(Table.id))
            .filter(Table.status == AssetStatus.DECOMMISSIONED)
            .scalar()
            or 0
        )

        total_size_mb = (
            db.query(func.sum(Table.size_mb)).filter(
                Table.size_mb.isnot(None)
            ).scalar()
            or 0
        )

        return {
            "total_tables": total_tables,
            "active_tables": active_tables,
            "inactive_tables": inactive_tables,
            "deprecated_tables": deprecated_tables,
            "decommissioned_tables": decommissioned_tables,
            "total_size_mb": round(total_size_mb, 2),
        }
    except Exception as e:
        logger_utils.error(f"Error getting asset summary: {e}")
        return {}
