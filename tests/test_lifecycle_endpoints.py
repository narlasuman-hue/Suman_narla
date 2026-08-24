"""Tests for lifecycle management endpoints."""

import pytest
from datetime import datetime

from src.catalog.models import (
    Database,
    Table,
    AssetStatus,
    AssetLifecycle,
    AssetTier,
)


@pytest.fixture
def sample_table(db):
    """Create a sample table for testing."""
    database = Database(name="test_db", status=AssetStatus.ACTIVE)
    db.add(database)
    db.flush()

    table = Table(
        name="test_table",
        db_id=database.id,
        table_type="T",
        status=AssetStatus.ACTIVE,
        created_at=datetime(2023, 1, 1),
    )
    db.add(table)
    db.flush()

    lifecycle = AssetLifecycle(
        table_id=table.id,
        asset_type="TABLE",
        created_date=datetime(2023, 1, 1),
        status=AssetStatus.ACTIVE,
        owner="test_owner",
        tier=AssetTier.TIER_2,
    )
    db.add(lifecycle)
    db.commit()

    return table, lifecycle


def test_get_lifecycle_summary(client):
    """Test lifecycle summary endpoint."""
    response = client.get("/api/v1/lifecycle/summary")
    assert response.status_code == 200
    data = response.json()
    assert "active" in data
    assert "inactive" in data
    assert "deprecated" in data
    assert "decommissioned" in data


def test_get_unused_assets(client):
    """Test unused assets endpoint."""
    response = client.get("/api/v1/lifecycle/unused-assets?days=90")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "unused_table_count" in data
    assert "unused_tables" in data


def test_get_decommissioning_candidates(client):
    """Test decommissioning candidates endpoint."""
    response = client.get("/api/v1/lifecycle/decommissioning-candidates?days=180")
    assert response.status_code == 200
    data = response.json()
    assert "days" in data
    assert "candidate_count" in data
    assert "candidates" in data


def test_list_lifecycle_assets(client, sample_table):
    """Test listing lifecycle assets."""
    response = client.get("/api/v1/lifecycle/assets")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        asset = data[0]
        assert "id" in asset
        assert "asset_type" in asset
        assert "status" in asset
        assert "tier" in asset


def test_list_lifecycle_by_status(client, sample_table):
    """Test filtering lifecycle assets by status."""
    response = client.get("/api/v1/lifecycle/assets?status=active")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)

    # Invalid status
    response = client.get("/api/v1/lifecycle/assets?status=invalid")
    assert response.status_code == 400


def test_list_lifecycle_by_tier(client, sample_table):
    """Test filtering lifecycle assets by tier."""
    response = client.get("/api/v1/lifecycle/assets?tier=tier_2")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_update_lifecycle(client, sample_table):
    """Test updating lifecycle information."""
    table, lifecycle = sample_table

    response = client.patch(
        f"/api/v1/lifecycle/assets/{lifecycle.id}",
        json={
            "owner": "new_owner",
            "tier": "tier_1",
            "review_notes": "Reviewed and updated",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["owner"] == "new_owner"
    assert data["tier"] == "tier_1"


def test_mark_deprecated(client, sample_table):
    """Test marking asset as deprecated."""
    table, lifecycle = sample_table

    response = client.post(
        f"/api/v1/lifecycle/assets/{table.id}/deprecate",
        json={"reason": "No longer in use"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deprecated"


def test_decommission(client, sample_table):
    """Test decommissioning asset."""
    table, lifecycle = sample_table

    response = client.post(
        f"/api/v1/lifecycle/assets/{table.id}/decommission",
        json={"reason": "End of life"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "decommissioned"
    assert "decommissioned_date" in data


def test_nonexistent_lifecycle(client):
    """Test error handling for nonexistent lifecycle."""
    response = client.patch(
        "/api/v1/lifecycle/assets/99999",
        json={"owner": "new_owner"},
    )
    assert response.status_code == 404
