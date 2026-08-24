"""Teradata database connector."""

import teradatasql
from typing import Any, Dict, List, Optional
import logging

from src.connectors.base import BaseConnector

logger = logging.getLogger(__name__)


class TeradataConnector(BaseConnector):
    """Teradata database connector using teradatasql driver."""

    def connect(self) -> None:
        """Establish Teradata connection."""
        try:
            self.connection = teradatasql.connect(
                host=self.host,
                user=self.user,
                password=self.password,
                database=self.database,
            )
            logger.info(f"Connected to Teradata at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to Teradata: {e}")
            raise

    def disconnect(self) -> None:
        """Close Teradata connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Disconnected from Teradata")
            except Exception as e:
                logger.error(f"Error disconnecting from Teradata: {e}")

    def is_connected(self) -> bool:
        """Check if connection is active."""
        if not self.connection:
            return False
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except Exception:
            return False

    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return results as list of dicts."""
        if not self.is_connected():
            raise Exception("Not connected to Teradata")

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql, params or {})
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            cursor.close()

            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise

    def get_databases(self) -> List[str]:
        """Get list of all databases from DBC.Databases."""
        sql = """
        SELECT DISTINCT DatabaseName
        FROM DBC.Databases
        WHERE DatabaseName NOT LIKE 'DBC%'
        AND DatabaseName NOT LIKE 'SYS%'
        ORDER BY DatabaseName
        """
        results = self.query(sql)
        return [row["DatabaseName"] for row in results]

    def get_tables(self, database: str) -> List[Dict[str, Any]]:
        """Get list of tables in a database from DBC.Tables."""
        sql = """
        SELECT
            DatabaseName,
            TableName,
            TableKind,
            CreateTimeStamp,
            LastAlterTimeStamp
        FROM DBC.Tables
        WHERE DatabaseName = ?
        AND TableKind IN ('T', 'O')
        ORDER BY TableName
        """
        results = self.query(sql, {"database": database})
        return results

    def get_columns(self, database: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table from DBC.Columns."""
        sql = """
        SELECT
            DatabaseName,
            TableName,
            ColumnName,
            ColumnType,
            ColumnLength,
            Nullable,
            ColumnPosition
        FROM DBC.Columns
        WHERE DatabaseName = ?
        AND TableName = ?
        ORDER BY ColumnPosition
        """
        results = self.query(sql, {"db": database, "table": table})
        return results

    def get_views(self, database: str) -> List[Dict[str, Any]]:
        """Get list of views in a database."""
        sql = """
        SELECT
            DatabaseName,
            TableName as ViewName,
            CreateTimeStamp,
            LastAlterTimeStamp
        FROM DBC.Tables
        WHERE DatabaseName = ?
        AND TableKind = 'V'
        ORDER BY ViewName
        """
        results = self.query(sql, {"database": database})
        return results

    def get_table_stats(self, database: str, table: str) -> Dict[str, Any]:
        """Get table statistics (row count, size, etc.)."""
        sql = """
        SELECT
            SUM(CurrentPerm) as size_bytes,
            MAX(LastAccessTimeStamp) as last_accessed
        FROM DBC.TableSize
        WHERE DatabaseName = ?
        AND TableName = ?
        """
        results = self.query(sql, {"db": database, "table": table})

        # Get row count
        try:
            row_sql = f"SELECT COUNT(*) as row_count FROM {database}.{table}"
            row_result = self.query(row_sql)
            row_count = row_result[0]["row_count"] if row_result else 0
        except Exception as e:
            logger.warning(f"Failed to get row count for {database}.{table}: {e}")
            row_count = None

        return {
            "size_bytes": results[0]["size_bytes"] if results else 0,
            "last_accessed": results[0]["last_accessed"] if results else None,
            "row_count": row_count,
        }

    def get_query_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get recent query history from DBC.QryLogV."""
        sql = """
        SELECT
            QueryID,
            UserName,
            LogonDateTime,
            QueryStartTime,
            QueryEndTime,
            StatementType,
            SQL
        FROM DBC.QryLogV
        WHERE QueryStartTime >= CURRENT_TIMESTAMP - INTERVAL '1' HOUR * ?
        ORDER BY QueryStartTime DESC
        """
        try:
            results = self.query(sql, {"hours": hours})
            return results
        except Exception as e:
            logger.warning(f"Query history not available: {e}")
            return []
