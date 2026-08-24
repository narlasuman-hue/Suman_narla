"""Teradata query log parsing and usage metrics extraction."""

from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import logging
import re

from src.catalog.models import Table, UsageMetrics, Lineage
from src.catalog.services.lineage import LineageExtractor

logger = logging.getLogger(__name__)


class QueryLogParser:
    """Parse Teradata query logs and extract usage information."""

    def __init__(self, db: Session, connector=None):
        """Initialize query log parser."""
        self.db = db
        self.connector = connector
        self.lineage_extractor = LineageExtractor(db)

    def parse_query_logs(self, hours: int = 24) -> Dict[str, Any]:
        """Parse query logs from Teradata and update usage metrics."""
        if not self.connector:
            logger.warning("Connector not available for query log parsing")
            return {'errors': ['Connector not available']}

        stats = {
            'logs_processed': 0,
            'tables_updated': 0,
            'lineages_created': 0,
            'errors': [],
        }

        try:
            # Get query logs from Teradata
            query_logs = self.connector.get_query_history(hours)
            logger.info(f"Retrieved {len(query_logs)} query logs")

            for log in query_logs:
                try:
                    self._process_query_log(log)
                    stats['logs_processed'] += 1
                except Exception as e:
                    error_msg = f"Error processing log: {str(e)}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)

            # Update usage metrics
            self._update_usage_metrics()
            stats['tables_updated'] = self._count_updated_tables()

            self.db.commit()

        except Exception as e:
            error_msg = f"Error parsing query logs: {str(e)}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            self.db.rollback()

        return stats

    def _process_query_log(self, log: Dict[str, Any]) -> None:
        """Process a single query log entry."""
        sql = log.get('SQL', '')
        if not sql:
            return

        # Skip certain statement types
        statement_type = log.get('StatementType', '').upper()
        if statement_type in ('DCL', 'DDL', 'UTILITY'):
            return

        # Extract tables from query
        query_result = self.lineage_extractor.parse_query(sql)

        # Record access for source tables
        for source in query_result['sources']:
            table = self.lineage_extractor.find_table_by_name(
                source.get('database'),
                source.get('table')
            )
            if table:
                self._record_table_access(table, log.get('QueryEndTime'))

        # Record write for target tables
        for target in query_result['targets']:
            table = self.lineage_extractor.find_table_by_name(
                target.get('database'),
                target.get('table')
            )
            if table:
                self._record_table_access(table, log.get('QueryEndTime'))

        # Create lineage from query
        self.lineage_extractor.create_lineage_from_query(sql)

    def _record_table_access(self, table: Table, access_time: Optional[datetime]) -> None:
        """Record table access in usage metrics."""
        # Create or update usage metrics
        if not table.usage:
            usage = UsageMetrics(
                table_id=table.id,
                last_accessed=access_time or datetime.utcnow(),
                access_count_7d=1,
                access_count_30d=1,
                access_count_90d=1,
                total_access_count=1,
            )
            self.db.add(usage)
        else:
            # Update existing metrics
            usage = table.usage
            usage.last_accessed = access_time or datetime.utcnow()
            usage.total_access_count = (usage.total_access_count or 0) + 1

            # Increment time-windowed counts
            if access_time:
                now = datetime.utcnow()
                days_ago = (now - access_time).days

                if days_ago < 7:
                    usage.access_count_7d = (usage.access_count_7d or 0) + 1
                if days_ago < 30:
                    usage.access_count_30d = (usage.access_count_30d or 0) + 1
                if days_ago < 90:
                    usage.access_count_90d = (usage.access_count_90d or 0) + 1

    def _update_usage_metrics(self) -> None:
        """Recalculate usage metrics for all tables."""
        tables = self.db.query(Table).all()

        for table in tables:
            if not table.usage:
                continue

            # Reset counters and recalculate from lineage
            now = datetime.utcnow()

            # Get lineages where this table is source (reads)
            lineages = self.db.query(Lineage).filter(
                Lineage.source_id == table.id,
                Lineage.source_type == 'TABLE',
            ).all()

            # Simple calculation based on recent lineage
            # In production, would sum actual query execution counts
            access_7d = len([l for l in lineages if (now - l.created_at).days < 7])
            access_30d = len([l for l in lineages if (now - l.created_at).days < 30])
            access_90d = len([l for l in lineages if (now - l.created_at).days < 90])

            if table.usage:
                if access_7d > 0:
                    table.usage.access_count_7d = access_7d
                if access_30d > 0:
                    table.usage.access_count_30d = access_30d
                if access_90d > 0:
                    table.usage.access_count_90d = access_90d

    def _count_updated_tables(self) -> int:
        """Count tables with updated access times."""
        threshold = datetime.utcnow() - timedelta(hours=1)
        count = self.db.query(UsageMetrics).filter(
            UsageMetrics.last_updated >= threshold
        ).count()
        return count

    def get_query_patterns(self, table_id: int, hours: int = 24) -> Dict[str, Any]:
        """Get query patterns for a specific table."""
        if not self.connector:
            return {'errors': ['Connector not available']}

        try:
            logs = self.connector.get_query_history(hours)
            table = self.db.get(Table, table_id)

            if not table:
                return {'errors': ['Table not found']}

            patterns = {
                'table_id': table_id,
                'table_name': table.name,
                'queries_total': 0,
                'query_types': {},
                'top_users': {},
                'query_times': [],
            }

            # Analyze queries
            for log in logs:
                sql = log.get('SQL', '')
                if not sql:
                    continue

                # Check if query references our table
                if table.name.lower() not in sql.lower():
                    continue

                patterns['queries_total'] += 1

                # Track query type
                query_type = log.get('StatementType', 'UNKNOWN')
                patterns['query_types'][query_type] = patterns['query_types'].get(query_type, 0) + 1

                # Track users
                user = log.get('UserName', 'UNKNOWN')
                patterns['top_users'][user] = patterns['top_users'].get(user, 0) + 1

                # Track query times
                if log.get('QueryStartTime'):
                    patterns['query_times'].append({
                        'start': log.get('QueryStartTime').isoformat(),
                        'duration_seconds': log.get('Duration', 0),
                    })

            return patterns

        except Exception as e:
            logger.error(f"Error analyzing query patterns: {e}")
            return {'errors': [str(e)]}

    def identify_heavy_users(self) -> List[Dict[str, Any]]:
        """Identify users with most table access."""
        if not self.connector:
            return []

        try:
            logs = self.connector.get_query_history(hours=24)
            user_stats = {}

            for log in logs:
                user = log.get('UserName', 'UNKNOWN')
                if user not in user_stats:
                    user_stats[user] = {
                        'queries': 0,
                        'errors': 0,
                        'tables': set(),
                    }

                user_stats[user]['queries'] += 1

                # Extract tables
                sql = log.get('SQL', '')
                tables = self.lineage_extractor.extract_tables_from_sql(sql)
                for table_ref in tables:
                    user_stats[user]['tables'].add(
                        f"{table_ref.get('database', '')}.{table_ref.get('table', '')}"
                    )

            # Convert to sorted list
            result = [
                {
                    'user': user,
                    'queries': stats['queries'],
                    'unique_tables': len(stats['tables']),
                    'tables': list(stats['tables'])[:5],  # Top 5 tables
                }
                for user, stats in user_stats.items()
            ]

            return sorted(result, key=lambda x: x['queries'], reverse=True)[:20]

        except Exception as e:
            logger.error(f"Error identifying heavy users: {e}")
            return []

    def get_query_performance(self, table_id: int, limit: int = 20) -> Dict[str, Any]:
        """Get query performance statistics for a table."""
        if not self.connector:
            return {'errors': ['Connector not available']}

        try:
            logs = self.connector.get_query_history(hours=24)
            table = self.db.get(Table, table_id)

            if not table:
                return {'errors': ['Table not found']}

            queries = []
            for log in logs:
                sql = log.get('SQL', '')
                if not sql or table.name.lower() not in sql.lower():
                    continue

                queries.append({
                    'user': log.get('UserName'),
                    'start_time': log.get('QueryStartTime'),
                    'end_time': log.get('QueryEndTime'),
                    'duration_seconds': log.get('Duration'),
                    'status': log.get('Status'),
                })

            return {
                'table_id': table_id,
                'table_name': table.name,
                'total_queries': len(queries),
                'avg_duration_seconds': (
                    sum(q.get('duration_seconds', 0) for q in queries) / len(queries)
                    if queries else 0
                ),
                'max_duration_seconds': (
                    max(q.get('duration_seconds', 0) for q in queries)
                    if queries else 0
                ),
                'recent_queries': queries[:limit],
            }

        except Exception as e:
            logger.error(f"Error getting query performance: {e}")
            return {'errors': [str(e)]}
