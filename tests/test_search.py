"""Tests for search and discovery functionality."""

import pytest
from datetime import datetime

from src.catalog.models import (
    Database,
    Table,
    Column,
    View,
    Job,
    AssetStatus,
    AssetTag,
)
from src.catalog.services.search import SearchService


@pytest.fixture
def sample_data(db):
    """Create sample data for search testing."""
    # Create database
    database = Database(name="test_db", status=AssetStatus.ACTIVE)
    db.add(database)
    db.flush()

    # Create tables
    table1 = Table(
        name="customers_table",
        db_id=database.id,
        table_type="T",
        status=AssetStatus.ACTIVE,
        description="Customer information table",
        created_at=datetime(2024, 1, 1),
    )
    db.add(table1)
    db.flush()

    table2 = Table(
        name="orders_table",
        db_id=database.id,
        table_type="T",
        status=AssetStatus.ACTIVE,
        description="Order details",
        created_at=datetime(2024, 1, 1),
    )
    db.add(table2)
    db.flush()

    # Create columns
    col1 = Column(
        name="email",
        table_id=table1.id,
        data_type="VARCHAR(255)",
        nullable=False,
        sensitive_flag=True,
        position=1,
    )
    db.add(col1)

    col2 = Column(
        name="customer_id",
        table_id=table2.id,
        data_type="INTEGER",
        nullable=False,
        position=1,
    )
    db.add(col2)
    db.flush()

    # Create view
    view = View(
        name="customer_orders_view",
        db_id=database.id,
        view_type="STANDARD",
        status=AssetStatus.ACTIVE,
        created_at=datetime(2024, 1, 1),
    )
    db.add(view)
    db.flush()

    # Create job
    job = Job(
        name="customer_sync_job",
        owner="data_team",
        status=AssetStatus.ACTIVE,
        description="Syncs customer data daily",
        created_at=datetime(2024, 1, 1),
    )
    db.add(job)
    db.flush()

    # Create tags
    tag1 = AssetTag(
        table_id=table1.id,
        asset_type="TABLE",
        tag_key="pii",
        tag_value="true",
    )
    db.add(tag1)

    tag2 = AssetTag(
        table_id=table1.id,
        asset_type="TABLE",
        tag_key="tier",
        tag_value="critical",
    )
    db.add(tag2)
    db.commit()

    return database, table1, table2, col1, col2, view, job


def test_search_tables(db, sample_data):
    """Test searching for tables."""
    database, table1, table2, *_ = sample_data
    search_service = SearchService(db)

    # Search by name
    results = search_service.search_tables("customers")
    assert len(results) > 0
    assert any(t["name"] == "customers_table" for t in results)

    # Search by description
    results = search_service.search_tables("Order")
    assert len(results) > 0
    assert any(t["name"] == "orders_table" for t in results)


def test_search_columns(db, sample_data):
    """Test searching for columns."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    # Search by column name
    results = search_service.search_columns("email")
    assert len(results) > 0
    assert any(c["name"] == "email" for c in results)

    # Search by data type
    results = search_service.search_columns("VARCHAR")
    assert len(results) > 0


def test_search_views(db, sample_data):
    """Test searching for views."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.search_views("customer_orders")
    assert len(results) > 0
    assert any(v["name"] == "customer_orders_view" for v in results)


def test_search_jobs(db, sample_data):
    """Test searching for jobs."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.search_jobs("customer_sync")
    assert len(results) > 0
    assert any(j["name"] == "customer_sync_job" for j in results)


def test_search_tags(db, sample_data):
    """Test searching by tags."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.search_tags("critical")
    assert len(results) > 0
    assert any(t["tag_value"] == "critical" for t in results)


def test_global_search(db, sample_data):
    """Test global search across all types."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.global_search("customer", limit=100)
    assert results["total_results"] > 0
    assert len(results["tables"]) > 0
    assert len(results["views"]) > 0
    assert len(results["jobs"]) > 0


def test_find_sensitive_data(db, sample_data):
    """Test finding sensitive columns."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.find_sensitive_data()
    assert len(results) > 0
    assert any(c["name"] == "email" for c in results)


def test_find_by_owner(db, sample_data):
    """Test finding assets by owner."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.find_by_owner("data_team")
    assert len(results["jobs"]) > 0
    assert any(j["name"] == "customer_sync_job" for j in results["jobs"])


def test_search_by_data_type(db, sample_data):
    """Test searching by data type."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    results = search_service.search_by_data_type("INTEGER")
    assert len(results) > 0
    assert any(c["name"] == "customer_id" for c in results)


def test_autocomplete_search(db, sample_data):
    """Test autocomplete suggestions."""
    database, table1, table2, col1, col2, view, job = sample_data
    search_service = SearchService(db)

    # Autocomplete tables
    results = search_service.autocomplete_search("cust", "table")
    assert len(results) > 0
    assert any("customers" in r.lower() for r in results)

    # Autocomplete columns
    results = search_service.autocomplete_search("em", "column")
    assert len(results) > 0
    assert any("email" in r.lower() for r in results)
