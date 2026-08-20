"""Data extraction from Teradata to S3."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from .aws_client import S3Client
from .teradata_client import TeradataClient

logger = logging.getLogger(__name__)


class TableExtractor:
    """Extract Teradata tables to S3."""

    def __init__(
        self,
        teradata_client: TeradataClient,
        s3_client: S3Client,
        config: Dict[str, Any]
    ):
        """Initialize extractor.

        Args:
            teradata_client: Connected Teradata client
            s3_client: Initialized S3 client
            config: Migration configuration
        """
        self.td_client = teradata_client
        self.s3_client = s3_client
        self.config = config
        self.migration_config = config.get("migration", {})

    def extract_table(self, table_name: str, output_format: str = "parquet") -> bool:
        """Extract table from Teradata to S3.

        Args:
            table_name: Fully qualified table name (schema.table)
            output_format: Output format (parquet, csv, json)

        Returns:
            True if successful, False otherwise
        """
        logger.info(f"Starting extraction of {table_name}")

        try:
            # Get schema information
            schema = self.td_client.get_table_schema(table_name)
            row_count = self.td_client.get_row_count(table_name)

            logger.info(f"Table {table_name}: {row_count} rows, {len(schema)} columns")

            # Extract data in batches
            batch_size = self.migration_config.get("batch_size", 10000)
            batch_num = 0
            total_rows = 0

            for batch in self.td_client.extract_table(table_name, batch_size):
                batch_num += 1
                total_rows += len(batch)

                # Save batch to S3
                s3_key = self._get_s3_key(table_name, batch_num, output_format)
                success = self._save_batch(batch, output_format, s3_key)

                if not success:
                    logger.error(f"Failed to save batch {batch_num} for {table_name}")
                    return False

                logger.debug(f"Saved batch {batch_num} ({len(batch)} rows) to {s3_key}")

            # Save metadata
            metadata = {
                "table_name": table_name,
                "total_rows": total_rows,
                "schema": schema,
                "batches": batch_num,
                "format": output_format
            }
            self._save_metadata(table_name, metadata)

            logger.info(f"Successfully extracted {table_name}: {total_rows} rows in {batch_num} batches")
            return True

        except Exception as e:
            logger.error(f"Extraction failed for {table_name}: {e}")
            return False

    def _get_s3_key(self, table_name: str, batch_num: int, format_type: str) -> str:
        """Generate S3 key for batch data.

        Args:
            table_name: Fully qualified table name
            batch_num: Batch number
            format_type: Data format

        Returns:
            S3 object key
        """
        safe_table_name = table_name.replace(".", "/")
        return f"raw/{safe_table_name}/batch_{batch_num:05d}.{format_type}"

    def _save_batch(self, batch: List[Dict[str, Any]], format_type: str, s3_key: str) -> bool:
        """Save batch of data to S3.

        Args:
            batch: List of row dictionaries
            format_type: Output format
            s3_key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            if format_type == "parquet":
                df = pd.DataFrame(batch)
                data = df.to_parquet(compression=self.migration_config.get("compression", "snappy"))
            elif format_type == "csv":
                df = pd.DataFrame(batch)
                data = df.to_csv(index=False).encode()
            elif format_type == "json":
                data = json.dumps(batch).encode()
            else:
                logger.error(f"Unsupported format: {format_type}")
                return False

            bucket = self.config["aws"]["s3_bucket_raw"]
            return self.s3_client.upload_data(data, bucket, s3_key)

        except Exception as e:
            logger.error(f"Failed to save batch to {s3_key}: {e}")
            return False

    def _save_metadata(self, table_name: str, metadata: Dict[str, Any]) -> bool:
        """Save extraction metadata to S3.

        Args:
            table_name: Table name
            metadata: Metadata dictionary

        Returns:
            True if successful, False otherwise
        """
        try:
            safe_table_name = table_name.replace(".", "/")
            s3_key = f"metadata/{safe_table_name}/extraction.json"
            data = json.dumps(metadata, indent=2).encode()

            bucket = self.config["aws"]["s3_bucket_metadata"]
            return self.s3_client.upload_data(data, bucket, s3_key)

        except Exception as e:
            logger.error(f"Failed to save metadata for {table_name}: {e}")
            return False
