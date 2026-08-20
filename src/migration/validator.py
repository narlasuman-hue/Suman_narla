"""Data validation for migration."""

import logging
from typing import Any, Dict

from .teradata_client import TeradataClient

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate data extraction and quality."""

    def __init__(self, teradata_client: TeradataClient, config: Dict[str, Any]):
        """Initialize validator.

        Args:
            teradata_client: Connected Teradata client
            config: Migration configuration
        """
        self.td_client = teradata_client
        self.config = config
        self.quality_config = config.get("quality", {})

    def validate_table(self, table_name: str) -> Dict[str, Any]:
        """Validate table data.

        Args:
            table_name: Fully qualified table name

        Returns:
            Validation result dictionary
        """
        logger.info(f"Validating table {table_name}")

        results = {
            "table": table_name,
            "status": "passed",
            "checks": {},
            "errors": []
        }

        # Row count validation
        if self.quality_config.get("enable_row_count_validation", True):
            try:
                count = self.td_client.get_row_count(table_name)
                results["checks"]["row_count"] = count
                logger.info(f"Row count validation passed: {count} rows")
            except Exception as e:
                results["status"] = "failed"
                results["errors"].append(f"Row count validation failed: {e}")
                logger.error(f"Row count validation failed: {e}")

        # Schema validation
        if self.quality_config.get("enable_schema_validation", True):
            try:
                schema = self.td_client.get_table_schema(table_name)
                results["checks"]["columns"] = len(schema)
                logger.info(f"Schema validation passed: {len(schema)} columns")
            except Exception as e:
                results["status"] = "failed"
                results["errors"].append(f"Schema validation failed: {e}")
                logger.error(f"Schema validation failed: {e}")

        return results

    def validate_all(self, tables: list) -> Dict[str, Any]:
        """Validate multiple tables.

        Args:
            tables: List of table names to validate

        Returns:
            Validation results for all tables
        """
        logger.info(f"Validating {len(tables)} table(s)")

        all_results = {
            "total_tables": len(tables),
            "passed": 0,
            "failed": 0,
            "tables": {}
        }

        for table_name in tables:
            result = self.validate_table(table_name)
            all_results["tables"][table_name] = result

            if result["status"] == "passed":
                all_results["passed"] += 1
            else:
                all_results["failed"] += 1

        all_results["status"] = "passed" if all_results["failed"] == 0 else "failed"

        return all_results
