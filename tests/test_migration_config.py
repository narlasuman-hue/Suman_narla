"""Tests for migration configuration."""

import tempfile
from pathlib import Path

import pytest

from migration.config import MigrationConfig


@pytest.fixture
def sample_config_file():
    """Create a temporary configuration file."""
    config_content = """
teradata:
  host: "localhost"
  port: 1025
  username: "test_user"
  password: "test_password"

aws:
  region: "us-east-1"
  s3_bucket_raw: "test-raw"
  s3_bucket_processed: "test-processed"

migration:
  batch_size: 5000
  format: "parquet"

tables:
  - name: "schema.table1"
    enabled: true
  - name: "schema.table2"
    enabled: false
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        config_file = f.name

    yield config_file

    # Cleanup
    Path(config_file).unlink()


def test_load_config(sample_config_file):
    """Test loading configuration from file."""
    config = MigrationConfig(sample_config_file)

    assert config.teradata_config["host"] == "localhost"
    assert config.teradata_config["port"] == 1025
    assert config.aws_config["region"] == "us-east-1"
    assert config.migration_config["batch_size"] == 5000


def test_get_tables(sample_config_file):
    """Test retrieving configured tables."""
    config = MigrationConfig(sample_config_file)

    tables = config.tables
    assert len(tables) == 2
    assert tables[0]["name"] == "schema.table1"
    assert tables[0]["enabled"] is True
    assert tables[1]["enabled"] is False


def test_get_config_value(sample_config_file):
    """Test getting configuration values by dotted path."""
    config = MigrationConfig(sample_config_file)

    assert config.get("teradata.host") == "localhost"
    assert config.get("aws.region") == "us-east-1"
    assert config.get("migration.batch_size") == 5000


def test_get_default_value(sample_config_file):
    """Test getting default value for missing config."""
    config = MigrationConfig(sample_config_file)

    assert config.get("nonexistent.key", "default") == "default"
