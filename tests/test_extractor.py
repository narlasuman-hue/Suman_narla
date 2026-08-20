"""Tests for table extraction."""

from unittest.mock import MagicMock, patch

import pytest

from migration.extractor import TableExtractor


@pytest.fixture
def mock_clients():
    """Create mock clients for testing."""
    td_client = MagicMock()
    s3_client = MagicMock()

    td_client.get_table_schema.return_value = {
        "id": "INTEGER",
        "name": "VARCHAR(100)",
        "created_at": "TIMESTAMP"
    }
    td_client.get_row_count.return_value = 1000

    # Mock batch extraction
    td_client.extract_table.return_value = [
        [{"id": i, "name": f"name_{i}", "created_at": "2024-01-01"} for i in range(100)]
        for _ in range(10)
    ]

    s3_client.upload_data.return_value = True

    return td_client, s3_client


def test_extract_table(mock_clients):
    """Test table extraction."""
    td_client, s3_client = mock_clients
    config = {
        "migration": {"batch_size": 100, "compression": "snappy"},
        "aws": {"s3_bucket_raw": "test-raw", "s3_bucket_metadata": "test-metadata"}
    }

    extractor = TableExtractor(td_client, s3_client, config)
    result = extractor.extract_table("schema.table1", "parquet")

    assert result is True
    td_client.get_table_schema.assert_called_once()
    td_client.get_row_count.assert_called_once()
    assert s3_client.upload_data.call_count > 0


def test_extract_table_failure(mock_clients):
    """Test extraction handling of errors."""
    td_client, s3_client = mock_clients
    td_client.get_table_schema.side_effect = Exception("Connection error")

    config = {
        "migration": {"batch_size": 100},
        "aws": {"s3_bucket_raw": "test-raw", "s3_bucket_metadata": "test-metadata"}
    }

    extractor = TableExtractor(td_client, s3_client, config)
    result = extractor.extract_table("schema.table1")

    assert result is False


def test_s3_key_generation(mock_clients):
    """Test S3 key generation."""
    td_client, s3_client = mock_clients
    config = {
        "migration": {"batch_size": 100},
        "aws": {"s3_bucket_raw": "test-raw", "s3_bucket_metadata": "test-metadata"}
    }

    extractor = TableExtractor(td_client, s3_client, config)
    key = extractor._get_s3_key("schema.table_name", 1, "parquet")

    assert key == "raw/schema/table_name/batch_00001.parquet"
