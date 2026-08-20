"""Teradata database client for extraction operations."""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class TeradataClient:
    """Client for connecting to and querying Teradata."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Teradata client.

        Args:
            config: Teradata configuration dictionary with host, port, username, password
        """
        self.config = config
        self.connection = None

    def connect(self) -> None:
        """Establish connection to Teradata."""
        try:
            # Import here to handle optional dependency
            import teradatasql

            self.connection = teradatasql.connect(
                host=self.config["host"],
                user=self.config["username"],
                password=self.config["password"],
                port=self.config.get("port", 1025),
                timeout=self.config.get("connection_timeout", 30)
            )
            logger.info(f"Connected to Teradata at {self.config['host']}")
        except ImportError:
            raise ImportError("teradatasql package is required. Install with: pip install teradatasql")
        except Exception as e:
            logger.error(f"Failed to connect to Teradata: {e}")
            raise

    def disconnect(self) -> None:
        """Close Teradata connection."""
        if self.connection:
            self.connection.close()
            logger.info("Disconnected from Teradata")

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get table schema information.

        Args:
            table_name: Fully qualified table name (schema.table)

        Returns:
            Dictionary with column names and types
        """
        if not self.connection:
            raise RuntimeError("Not connected to Teradata")

        schema_dict = {}
        try:
            cursor = self.connection.cursor()
            # Query to get table structure
            query = f"SELECT * FROM {table_name} WHERE 1=0"
            cursor.execute(query)

            # Extract column information
            for description in cursor.description:
                schema_dict[description[0]] = str(description[1])

            logger.debug(f"Retrieved schema for {table_name}: {schema_dict}")
            return schema_dict
        finally:
            cursor.close()

    def get_row_count(self, table_name: str) -> int:
        """Get total row count for a table.

        Args:
            table_name: Fully qualified table name

        Returns:
            Number of rows in the table
        """
        if not self.connection:
            raise RuntimeError("Not connected to Teradata")

        try:
            cursor = self.connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            logger.debug(f"Row count for {table_name}: {count}")
            return count
        finally:
            cursor.close()

    def extract_table(self, table_name: str, batch_size: int = 10000) -> List[Dict[str, Any]]:
        """Extract all rows from a table.

        Args:
            table_name: Fully qualified table name
            batch_size: Number of rows to fetch at once

        Yields:
            List of dictionaries representing rows
        """
        if not self.connection:
            raise RuntimeError("Not connected to Teradata")

        cursor = self.connection.cursor()
        try:
            cursor.execute(f"SELECT * FROM {table_name}")

            while True:
                rows = cursor.fetchmany(batch_size)
                if not rows:
                    break

                # Convert to list of dictionaries
                batch = []
                for row in rows:
                    row_dict = {}
                    for i, desc in enumerate(cursor.description):
                        row_dict[desc[0]] = row[i]
                    batch.append(row_dict)

                yield batch
        finally:
            cursor.close()

    def execute_query(self, query: str) -> List[tuple]:
        """Execute a custom query and return results.

        Args:
            query: SQL query to execute

        Returns:
            List of result tuples
        """
        if not self.connection:
            raise RuntimeError("Not connected to Teradata")

        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            return cursor.fetchall()
        finally:
            cursor.close()
