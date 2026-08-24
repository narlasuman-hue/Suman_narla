"""Tests for metadata sync service."""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock

from src.catalog.database import get_session
from src.catalog.models import Database, Table, Column, View, AssetStatus
from src.catalog.services.sync import create_sync_service
from src.connectors.teradata import TeradataConnector


@pytest.fixture
def mock_connector():
    """Create mock Teradata connector."""
    connector = Mock(spec=TeradataConnector)
    connector.is_connected.return_value = True

    # Mock database list
    connector.get_databases.return_value = ["database1", "database2"]

    # Mock tables
    connector.get_tables.return_value = [
        {
            "TableName": "table1",
            "TableKind": "T",
            "CreateTimeStamp": datetime(2024, 1, 1),
            "LastAlterTimeStamp": datetime(2024, 1, 15),
        },
        {
            "TableName": "table2",
            "TableKind": "T",
            "CreateTimeStamp": datetime(2024, 2, 1),
            "LastAlterTimeStamp": datetime(2024, 2, 15),
        },
    ]

    # Mock columns
    def get_columns_side_effect(db_name, table_name):
        if table_name == "table1":
            return [
                {
                    "ColumnName": "id",
                    "ColumnType": "INTEGER",
                    "Nullable": False,
                    "ColumnPosition": 1,
                },
                {
                    "ColumnName": "name",
                    "ColumnType": "VARCHAR(255)",
                    "Nullable": True,
                    "ColumnPosition": 2,
                },
            ]
        return []

    connector.get_columns.side_effect = get_columns_side_effect

    # Mock views
    connector.get_views.return_value = [
        {
            "ViewName": "view1",
            "CreateTimeStamp": datetime(2024, 1, 1),
        }
    ]

    # Mock table stats
    connector.get_table_stats.return_value = {
        "size_bytes": 1024 * 1024 * 100,  # 100 MB
        "row_count": 10000,
        "last_accessed": datetime(2024, 2, 20),
    }

    return connector


def test_sync_databases(db, mock_connector):
    """Test syncing databases."""
    sync_service = create_sync_service(db, mock_connector)
    sync_service._sync_databases()

    databases = db.query(Database).all()
    assert len(databases) == 2
    assert any(d.name == "database1" for d in databases)
    assert any(d.name == "database2" for d in databases)


def test_sync_tables(db, mock_connector):
    """Test syncing tables."""
    # Create a database first
    database = Database(name="database1", status=AssetStatus.ACTIVE)
    db.add(database)
    db.commit()

    sync_service = create_sync_service(db, mock_connector)
    sync_service._sync_tables_for_database(database)

    tables = db.query(Table).filter(Table.db_id == database.id).all()
    assert len(tables) == 2
    assert any(t.name == "table1" for t in tables)
    assert any(t.name == "table2" for t in tables)


def test_sync_columns(db, mock_connector):
    """Test syncing columns."""
    database = Database(name="database1", status=AssetStatus.ACTIVE)
    table = Table(
        name="table1",
        db_id=1,
        table_type="T",
        status=AssetStatus.ACTIVE,
    )
    database.tables.append(table)
    db.add(database)
    db.commit()

    sync_service = create_sync_service(db, mock_connector)
    sync_service._sync_columns_for_table("database1", table)

    columns = db.query(Column).filter(Column.table_id == table.id).all()
    assert len(columns) == 2
    assert any(c.name == "id" for c in columns)
    assert any(c.name == "name" for c in columns)


def test_sync_views(db, mock_connector):
    """Test syncing views."""
    database = Database(name="database1", status=AssetStatus.ACTIVE)
    db.add(database)
    db.commit()

    sync_service = create_sync_service(db, mock_connector)
    sync_service._sync_views_for_database(database)

    views = db.query(View).filter(View.db_id == database.id).all()
    assert len(views) == 1
    assert views[0].name == "view1"


def test_sync_idempotency(db, mock_connector):
    """Test that syncing twice creates no duplicates."""
    sync_service = create_sync_service(db, mock_connector)

    # First sync
    sync_service._sync_databases()
    db1_count = db.query(Database).count()

    # Second sync
    sync_service._sync_databases()
    db2_count = db.query(Database).count()

    assert db1_count == db2_count == 2


def test_sync_stats(db, mock_connector):
    """Test sync statistics tracking."""
    sync_service = create_sync_service(db, mock_connector)
    sync_service._sync_databases()

    assert sync_service.sync_stats["databases_created"] == 2
    assert sync_service.sync_stats["databases_updated"] == 0

    # Sync again
    sync_service._sync_databases()
    assert sync_service.sync_stats["databases_created"] == 2
    assert sync_service.sync_stats["databases_updated"] == 2


def test_error_handling(db):
    """Test error handling in sync service."""
    # Create a connector that raises an error
    mock_connector = Mock(spec=TeradataConnector)
    mock_connector.is_connected.return_value = True
    mock_connector.get_databases.side_effect = Exception("Connection error")

    sync_service = create_sync_service(db, mock_connector)
    stats = sync_service.sync_all_metadata()

    assert len(stats["errors"]) > 0
    assert "Connection error" in str(stats["errors"])
