"""Base connector class for database connections."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class BaseConnector(ABC):
    """Abstract base class for database connectors."""

    def __init__(self, host: str, port: int, user: str, password: str, database: str):
        """Initialize connector with connection details."""
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connection = None

    @abstractmethod
    def connect(self) -> None:
        """Establish database connection."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close database connection."""
        pass

    @abstractmethod
    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute query and return results."""
        pass

    @abstractmethod
    def get_databases(self) -> List[str]:
        """Get list of all databases."""
        pass

    @abstractmethod
    def get_tables(self, database: str) -> List[Dict[str, Any]]:
        """Get list of tables in a database."""
        pass

    @abstractmethod
    def get_columns(self, database: str, table: str) -> List[Dict[str, Any]]:
        """Get columns for a specific table."""
        pass

    @abstractmethod
    def get_views(self, database: str) -> List[Dict[str, Any]]:
        """Get list of views in a database."""
        pass

    @abstractmethod
    def get_table_stats(self, database: str, table: str) -> Dict[str, Any]:
        """Get table statistics (row count, size, etc.)."""
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connection is active."""
        pass

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
