"""Tests for lineage extraction and analysis."""

import pytest
from datetime import datetime

from src.catalog.models import (
    Database,
    Table,
    Lineage,
    AssetStatus,
)
from src.catalog.services.lineage import (
    LineageExtractor,
    LineageGraph,
    ImpactAnalyzer,
)


@pytest.fixture
def sample_tables(db):
    """Create sample tables for lineage testing."""
    database = Database(name="test_db", status=AssetStatus.ACTIVE)
    db.add(database)
    db.flush()

    # Create tables
    source_table = Table(
        name="source_table",
        db_id=database.id,
        table_type="T",
        status=AssetStatus.ACTIVE,
        created_at=datetime(2024, 1, 1),
    )
    db.add(source_table)
    db.flush()

    target_table = Table(
        name="target_table",
        db_id=database.id,
        table_type="T",
        status=AssetStatus.ACTIVE,
        created_at=datetime(2024, 1, 1),
    )
    db.add(target_table)
    db.flush()

    # Create lineage
    lineage = Lineage(
        source_id=source_table.id,
        source_type="TABLE",
        target_id=target_table.id,
        target_type="TABLE",
        created_at=datetime.utcnow(),
    )
    db.add(lineage)
    db.commit()

    return source_table, target_table, database


def test_extract_tables_from_sql(db):
    """Test extracting table references from SQL."""
    extractor = LineageExtractor(db)

    sql = "SELECT * FROM db1.table1 JOIN db2.table2 ON db1.table1.id = db2.table2.id"
    tables = extractor.extract_tables_from_sql(sql)

    assert len(tables) >= 2
    table_names = [t["table"] for t in tables]
    assert "table1" in table_names
    assert "table2" in table_names


def test_parse_select_query(db):
    """Test parsing SELECT query."""
    extractor = LineageExtractor(db)

    sql = "SELECT * FROM source_table WHERE id > 100"
    parsed = extractor.parse_query(sql)

    assert parsed["type"] == "SELECT"
    assert len(parsed["sources"]) > 0
    assert len(parsed["targets"]) == 0


def test_parse_insert_query(db):
    """Test parsing INSERT query."""
    extractor = LineageExtractor(db)

    sql = "INSERT INTO target_table SELECT * FROM source_table"
    parsed = extractor.parse_query(sql)

    assert parsed["type"] == "INSERT"
    assert len(parsed["targets"]) > 0


def test_parse_update_query(db):
    """Test parsing UPDATE query."""
    extractor = LineageExtractor(db)

    sql = "UPDATE table1 SET col1 = (SELECT MAX(col2) FROM table2)"
    parsed = extractor.parse_query(sql)

    assert parsed["type"] == "UPDATE"


def test_create_lineage_from_query(db, sample_tables):
    """Test creating lineage from query."""
    source, target, database = sample_tables
    extractor = LineageExtractor(db)

    sql = f"INSERT INTO {target.name} SELECT * FROM {source.name}"
    result = extractor.create_lineage_from_query(sql)

    # Check if lineage was created
    lineages = db.query(Lineage).filter(
        Lineage.source_id == source.id,
        Lineage.target_id == target.id,
    ).all()

    assert len(lineages) > 0


def test_get_upstream_lineage(db, sample_tables):
    """Test getting upstream lineage."""
    source, target, database = sample_tables

    graph = LineageGraph(db)
    upstream = graph.get_upstream_lineage(target.id)

    assert upstream["table_id"] == target.id
    assert "lineage" in upstream


def test_get_downstream_lineage(db, sample_tables):
    """Test getting downstream lineage."""
    source, target, database = sample_tables

    graph = LineageGraph(db)
    downstream = graph.get_downstream_lineage(source.id)

    assert downstream["table_id"] == source.id
    assert "lineage" in downstream


def test_get_full_lineage(db, sample_tables):
    """Test getting full lineage graph."""
    source, target, database = sample_tables

    graph = LineageGraph(db)
    full_lineage = graph.get_full_lineage(target.id)

    assert full_lineage["table_id"] == target.id
    assert "upstream" in full_lineage
    assert "downstream" in full_lineage


def test_get_impact_of_change(db, sample_tables):
    """Test analyzing impact of changes."""
    source, target, database = sample_tables

    analyzer = ImpactAnalyzer(db)
    impact = analyzer.get_impact_of_change(source.id)

    assert impact["source_table_id"] == source.id
    assert "impacted_count" in impact
    assert "impacted_tables" in impact


def test_get_dependencies(db, sample_tables):
    """Test getting dependencies."""
    source, target, database = sample_tables

    analyzer = ImpactAnalyzer(db)
    dependencies = analyzer.get_dependencies(target.id)

    assert dependencies["table_id"] == target.id
    assert "dependency_count" in dependencies
    assert "dependencies" in dependencies


def test_can_safely_drop(db, sample_tables):
    """Test checking if table can be safely dropped."""
    source, target, database = sample_tables

    analyzer = ImpactAnalyzer(db)

    # Source table has dependents
    result_source = analyzer.can_safely_drop(source.id)
    assert not result_source["can_safely_drop"]

    # Target table has no dependents
    result_target = analyzer.can_safely_drop(target.id)
    assert result_target["can_safely_drop"]
