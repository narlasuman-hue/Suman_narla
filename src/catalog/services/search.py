"""Full-text search and metadata discovery service."""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func, text
from typing import List, Dict, Any, Optional
import logging

from src.catalog.models import Table, Column, View, Database, Job, AssetTag

logger = logging.getLogger(__name__)


class SearchService:
    """Search across metadata catalog."""

    def __init__(self, db: Session):
        """Initialize search service."""
        self.db = db

    def search_tables(
        self,
        query: str,
        database_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for tables by name and description."""
        search_query = self.db.query(Table)

        if database_id:
            search_query = search_query.filter(Table.db_id == database_id)

        # Search in name and description (case-insensitive)
        search_term = f"%{query}%"
        search_query = search_query.filter(
            or_(
                Table.name.ilike(search_term),
                Table.description.ilike(search_term),
            )
        )

        tables = search_query.limit(limit).all()

        return [
            {
                'id': t.id,
                'name': t.name,
                'database': t.database.name if t.database else None,
                'type': t.table_type,
                'description': t.description,
                'created_at': t.created_at.isoformat() if t.created_at else None,
                'row_count': t.row_count,
                'size_mb': t.size_mb,
                'match_type': 'table_name' if query.lower() in t.name.lower() else 'description',
            }
            for t in tables
        ]

    def search_columns(
        self,
        query: str,
        table_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for columns by name and description."""
        search_query = self.db.query(Column).join(Table)

        if table_id:
            search_query = search_query.filter(Column.table_id == table_id)

        # Search in column name and description
        search_term = f"%{query}%"
        search_query = search_query.filter(
            or_(
                Column.name.ilike(search_term),
                Column.description.ilike(search_term),
            )
        )

        columns = search_query.limit(limit).all()

        return [
            {
                'id': c.id,
                'name': c.name,
                'table_id': c.table_id,
                'table_name': c.table.name,
                'database': c.table.database.name if c.table.database else None,
                'data_type': c.data_type,
                'description': c.description,
                'sensitive': c.sensitive_flag,
                'match_type': 'column_name' if query.lower() in c.name.lower() else 'description',
            }
            for c in columns
        ]

    def search_views(
        self,
        query: str,
        database_id: Optional[int] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for views by name."""
        search_query = self.db.query(View)

        if database_id:
            search_query = search_query.filter(View.db_id == database_id)

        search_term = f"%{query}%"
        search_query = search_query.filter(View.name.ilike(search_term))

        views = search_query.limit(limit).all()

        return [
            {
                'id': v.id,
                'name': v.name,
                'database': v.database.name if v.database else None,
                'type': v.view_type,
                'created_at': v.created_at.isoformat() if v.created_at else None,
            }
            for v in views
        ]

    def search_jobs(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for jobs by name and description."""
        search_term = f"%{query}%"
        search_query = self.db.query(Job).filter(
            or_(
                Job.name.ilike(search_term),
                Job.description.ilike(search_term),
            )
        ).limit(limit)

        jobs = search_query.all()

        return [
            {
                'id': j.id,
                'name': j.name,
                'owner': j.owner,
                'description': j.description,
                'frequency': j.frequency,
                'status': j.status.value,
            }
            for j in jobs
        ]

    def search_tags(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Search for assets by tags."""
        search_term = f"%{query}%"
        search_query = self.db.query(AssetTag).filter(
            or_(
                AssetTag.tag_key.ilike(search_term),
                AssetTag.tag_value.ilike(search_term),
            )
        ).limit(limit)

        tags = search_query.all()

        results = []
        for tag in tags:
            if tag.table_id:
                table = tag.table
                results.append({
                    'asset_id': tag.table_id,
                    'asset_type': 'TABLE',
                    'asset_name': table.name if table else None,
                    'tag_key': tag.tag_key,
                    'tag_value': tag.tag_value,
                })
            elif tag.job_id:
                job = tag.job
                results.append({
                    'asset_id': tag.job_id,
                    'asset_type': 'JOB',
                    'asset_name': job.name if job else None,
                    'tag_key': tag.tag_key,
                    'tag_value': tag.tag_value,
                })

        return results

    def global_search(
        self,
        query: str,
        asset_types: Optional[List[str]] = None,
        database_id: Optional[int] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Perform global search across all asset types."""
        if not asset_types:
            asset_types = ['tables', 'columns', 'views', 'jobs', 'tags']

        results = {
            'query': query,
            'total_results': 0,
            'tables': [],
            'columns': [],
            'views': [],
            'jobs': [],
            'tags': [],
        }

        limit_per_type = max(1, limit // len(asset_types))

        if 'tables' in asset_types:
            tables = self.search_tables(query, database_id, limit_per_type)
            results['tables'] = tables
            results['total_results'] += len(tables)

        if 'columns' in asset_types:
            columns = self.search_columns(query, limit=limit_per_type)
            results['columns'] = columns
            results['total_results'] += len(columns)

        if 'views' in asset_types:
            views = self.search_views(query, database_id, limit_per_type)
            results['views'] = views
            results['total_results'] += len(views)

        if 'jobs' in asset_types:
            jobs = self.search_jobs(query, limit_per_type)
            results['jobs'] = jobs
            results['total_results'] += len(jobs)

        if 'tags' in asset_types:
            tags = self.search_tags(query, limit_per_type)
            results['tags'] = tags
            results['total_results'] += len(tags)

        return results

    def find_sensitive_data(self) -> List[Dict[str, Any]]:
        """Find all sensitive columns in catalog."""
        columns = self.db.query(Column).filter(
            Column.sensitive_flag == True
        ).all()

        return [
            {
                'id': c.id,
                'name': c.name,
                'table_id': c.table_id,
                'table_name': c.table.name,
                'database': c.table.database.name if c.table and c.table.database else None,
                'data_type': c.data_type,
                'description': c.description,
            }
            for c in columns
        ]

    def find_by_owner(self, owner: str) -> Dict[str, Any]:
        """Find all assets owned by a specific person."""
        from src.catalog.models import AssetLifecycle

        tables_owned = self.db.query(Table).join(
            AssetLifecycle, Table.id == AssetLifecycle.table_id
        ).filter(
            AssetLifecycle.owner.ilike(f"%{owner}%")
        ).all()

        jobs_owned = self.db.query(Job).filter(
            Job.owner.ilike(f"%{owner}%")
        ).all()

        return {
            'owner': owner,
            'tables': [
                {
                    'id': t.id,
                    'name': t.name,
                    'database': t.database.name if t.database else None,
                    'type': t.table_type,
                }
                for t in tables_owned
            ],
            'jobs': [
                {
                    'id': j.id,
                    'name': j.name,
                    'frequency': j.frequency,
                }
                for j in jobs_owned
            ],
        }

    def search_by_data_type(self, data_type: str) -> List[Dict[str, Any]]:
        """Find all columns with a specific data type."""
        columns = self.db.query(Column).filter(
            Column.data_type.ilike(f"%{data_type}%")
        ).all()

        return [
            {
                'id': c.id,
                'name': c.name,
                'table_id': c.table_id,
                'table_name': c.table.name,
                'database': c.table.database.name if c.table and c.table.database else None,
                'data_type': c.data_type,
                'position': c.position,
            }
            for c in columns
        ]

    def autocomplete_search(self, query: str, asset_type: str = 'table') -> List[str]:
        """Autocomplete suggestions for search."""
        search_term = f"{query}%"

        if asset_type == 'table':
            results = self.db.query(Table.name).filter(
                Table.name.ilike(search_term)
            ).limit(10).all()
        elif asset_type == 'column':
            results = self.db.query(Column.name).filter(
                Column.name.ilike(search_term)
            ).limit(10).all()
        elif asset_type == 'database':
            results = self.db.query(Database.name).filter(
                Database.name.ilike(search_term)
            ).limit(10).all()
        elif asset_type == 'job':
            results = self.db.query(Job.name).filter(
                Job.name.ilike(search_term)
            ).limit(10).all()
        else:
            results = []

        return [r[0] for r in results]
