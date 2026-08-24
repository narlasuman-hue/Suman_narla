"""Data lineage extraction and analysis service."""

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Set, Tuple, Optional
import logging
import re

from src.catalog.models import Table, Lineage, Job, Database

logger = logging.getLogger(__name__)


class LineageExtractor:
    """Extract lineage from SQL queries and Teradata metadata."""

    # Pattern to match table references in SQL
    TABLE_PATTERN = re.compile(
        r'\b(?:FROM|JOIN|INSERT\s+INTO|UPDATE|DELETE\s+FROM|CREATE\s+TABLE|CREATE\s+VIEW)\s+'
        r'(?:(?P<db>\w+)\.)?(?P<table>\w+)',
        re.IGNORECASE
    )

    # Pattern to match column references
    COLUMN_PATTERN = re.compile(r'(?P<table>\w+)\.(?P<column>\w+)', re.IGNORECASE)

    def __init__(self, db: Session):
        """Initialize lineage extractor."""
        self.db = db

    def extract_tables_from_sql(self, sql: str) -> List[Dict[str, str]]:
        """Extract table references from SQL query."""
        tables = []
        seen = set()

        for match in self.TABLE_PATTERN.finditer(sql):
            db_name = match.group('db')
            table_name = match.group('table')

            # Skip system tables
            if table_name.upper().startswith(('DBC', 'SYS')):
                continue

            key = (db_name or '', table_name)
            if key not in seen:
                tables.append({
                    'database': db_name,
                    'table': table_name,
                })
                seen.add(key)

        return tables

    def parse_query(self, sql: str) -> Dict[str, Any]:
        """Parse SQL query to identify source and target tables."""
        sql_upper = sql.upper().strip()

        # Determine query type
        query_type = None
        if sql_upper.startswith('SELECT'):
            query_type = 'SELECT'
        elif sql_upper.startswith('INSERT'):
            query_type = 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            query_type = 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            query_type = 'DELETE'
        elif sql_upper.startswith('CREATE'):
            query_type = 'CREATE'
        else:
            query_type = 'OTHER'

        all_tables = self.extract_tables_from_sql(sql)

        # Simplified logic: first table in INSERT/UPDATE/DELETE/CREATE is target
        # All tables in SELECT or JOIN are sources
        target_tables = []
        source_tables = []

        if query_type in ('INSERT', 'UPDATE', 'DELETE', 'CREATE'):
            if all_tables:
                target_tables = [all_tables[0]]
                source_tables = all_tables[1:] if len(all_tables) > 1 else []
        elif query_type == 'SELECT':
            source_tables = all_tables

        return {
            'type': query_type,
            'sources': source_tables,
            'targets': target_tables,
        }

    def find_table_by_name(self, db_name: Optional[str], table_name: str) -> Optional[Table]:
        """Find table in catalog by name."""
        query = self.db.query(Table).join(Database)

        if db_name:
            query = query.filter(Database.name.ilike(db_name))

        table = query.filter(Table.name.ilike(table_name)).first()
        return table

    def create_lineage_from_query(
        self,
        sql: str,
        job_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create lineage records from a query."""
        parsed = self.parse_query(sql)
        created_count = 0
        errors = []

        try:
            # Create source → target lineage
            for source in parsed['sources']:
                source_table = self.find_table_by_name(
                    source.get('database'),
                    source.get('table')
                )

                for target in parsed['targets']:
                    target_table = self.find_table_by_name(
                        target.get('database'),
                        target.get('table')
                    )

                    if source_table and target_table:
                        # Check if lineage already exists
                        existing = self.db.query(Lineage).filter(
                            and_(
                                Lineage.source_id == source_table.id,
                                Lineage.source_type == 'TABLE',
                                Lineage.target_id == target_table.id,
                                Lineage.target_type == 'TABLE',
                            )
                        ).first()

                        if not existing:
                            lineage = Lineage(
                                source_id=source_table.id,
                                source_type='TABLE',
                                target_id=target_table.id,
                                target_type='TABLE',
                                job_id=job_id,
                                created_at=datetime.utcnow(),
                            )
                            self.db.add(lineage)
                            created_count += 1
                    else:
                        if not source_table:
                            errors.append(f"Source table not found: {source.get('database', 'unknown')}.{source.get('table')}")
                        if not target_table:
                            errors.append(f"Target table not found: {target.get('database', 'unknown')}.{target.get('table')}")

        except Exception as e:
            errors.append(f"Error creating lineage: {str(e)}")

        self.db.commit()

        return {
            'created': created_count,
            'errors': errors,
        }


class LineageGraph:
    """Build and analyze lineage graphs."""

    def __init__(self, db: Session):
        """Initialize lineage graph."""
        self.db = db
        self.cache = {}

    def get_upstream_lineage(
        self,
        table_id: int,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Get all upstream dependencies (sources)."""
        visited = set()
        queue = [(table_id, 0)]
        lineage_map = {}

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Find all lineages where current_id is the target
            lineages = self.db.query(Lineage).filter(
                and_(
                    Lineage.target_id == current_id,
                    Lineage.target_type == 'TABLE',
                )
            ).all()

            lineage_map[current_id] = []

            for lineage in lineages:
                source_table = self.db.get(Table, lineage.source_id)
                if source_table:
                    lineage_map[current_id].append({
                        'source_id': lineage.source_id,
                        'source_name': source_table.name,
                        'source_db': source_table.database.name if source_table.database else None,
                        'lineage_id': lineage.id,
                        'job_id': lineage.job_id,
                    })

                    if lineage.source_id not in visited:
                        queue.append((lineage.source_id, depth + 1))

        return {
            'table_id': table_id,
            'lineage': lineage_map,
            'depth': max_depth,
        }

    def get_downstream_lineage(
        self,
        table_id: int,
        max_depth: int = 5,
    ) -> Dict[str, Any]:
        """Get all downstream dependencies (targets)."""
        visited = set()
        queue = [(table_id, 0)]
        lineage_map = {}

        while queue:
            current_id, depth = queue.pop(0)

            if current_id in visited or depth > max_depth:
                continue

            visited.add(current_id)

            # Find all lineages where current_id is the source
            lineages = self.db.query(Lineage).filter(
                and_(
                    Lineage.source_id == current_id,
                    Lineage.source_type == 'TABLE',
                )
            ).all()

            lineage_map[current_id] = []

            for lineage in lineages:
                target_table = self.db.get(Table, lineage.target_id)
                if target_table:
                    lineage_map[current_id].append({
                        'target_id': lineage.target_id,
                        'target_name': target_table.name,
                        'target_db': target_table.database.name if target_table.database else None,
                        'lineage_id': lineage.id,
                        'job_id': lineage.job_id,
                    })

                    if lineage.target_id not in visited:
                        queue.append((lineage.target_id, depth + 1))

        return {
            'table_id': table_id,
            'lineage': lineage_map,
            'depth': max_depth,
        }

    def get_full_lineage(self, table_id: int, max_depth: int = 3) -> Dict[str, Any]:
        """Get complete lineage graph."""
        upstream = self.get_upstream_lineage(table_id, max_depth)
        downstream = self.get_downstream_lineage(table_id, max_depth)

        return {
            'table_id': table_id,
            'upstream': upstream['lineage'],
            'downstream': downstream['lineage'],
        }


class ImpactAnalyzer:
    """Analyze impact of changes to assets."""

    def __init__(self, db: Session):
        """Initialize impact analyzer."""
        self.db = db
        self.lineage_graph = LineageGraph(db)

    def get_impact_of_change(self, table_id: int) -> Dict[str, Any]:
        """Get all tables impacted by changes to a specific table."""
        # Get all downstream tables (direct and transitive)
        downstream = self.lineage_graph.get_downstream_lineage(table_id, max_depth=10)

        # Flatten the tree
        impacted_tables = set()
        for _, targets in downstream['lineage'].items():
            for target in targets:
                impacted_tables.add(target['target_id'])

        # Get table details
        impacted_details = []
        for table_id_impact in impacted_tables:
            table = self.db.get(Table, table_id_impact)
            if table:
                impacted_details.append({
                    'id': table.id,
                    'name': table.name,
                    'database': table.database.name if table.database else None,
                    'type': table.table_type,
                    'size_mb': table.size_mb,
                    'row_count': table.row_count,
                    'status': table.status.value,
                })

        return {
            'source_table_id': table_id,
            'impacted_count': len(impacted_details),
            'impacted_tables': impacted_details,
        }

    def get_dependencies(self, table_id: int) -> Dict[str, Any]:
        """Get all tables this table depends on."""
        # Get all upstream tables (direct and transitive)
        upstream = self.lineage_graph.get_upstream_lineage(table_id, max_depth=10)

        # Flatten the tree
        dependencies = set()
        for _, sources in upstream['lineage'].items():
            for source in sources:
                dependencies.add(source['source_id'])

        # Get table details
        dependency_details = []
        for table_id_dep in dependencies:
            table = self.db.get(Table, table_id_dep)
            if table:
                dependency_details.append({
                    'id': table.id,
                    'name': table.name,
                    'database': table.database.name if table.database else None,
                    'type': table.table_type,
                    'size_mb': table.size_mb,
                    'row_count': table.row_count,
                    'status': table.status.value,
                })

        return {
            'table_id': table_id,
            'dependency_count': len(dependency_details),
            'dependencies': dependency_details,
        }

    def can_safely_drop(self, table_id: int) -> Dict[str, Any]:
        """Determine if a table can be safely dropped."""
        impact = self.get_impact_of_change(table_id)
        table = self.db.get(Table, table_id)

        can_drop = len(impact['impacted_tables']) == 0

        return {
            'table_id': table_id,
            'table_name': table.name if table else None,
            'can_safely_drop': can_drop,
            'impacted_count': impact['impacted_count'],
            'impacted_tables': impact['impacted_tables'] if not can_drop else [],
            'reason': (
                'Safe to drop - no downstream dependencies'
                if can_drop
                else f'{impact["impacted_count"]} tables depend on this table'
            ),
        }
