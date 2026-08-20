"""AWS S3 and Glue client for data loading and management."""

import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class S3Client:
    """Client for S3 operations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize S3 client.

        Args:
            config: AWS configuration with region and bucket names
        """
        self.config = config
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize boto3 S3 client."""
        try:
            import boto3
            self.client = boto3.client("s3", region_name=self.config["region"])
            logger.info(f"Initialized S3 client in region {self.config['region']}")
        except ImportError:
            raise ImportError("boto3 package is required. Install with: pip install boto3")

    def upload_file(self, file_path: str, bucket: str, key: str) -> bool:
        """Upload file to S3.

        Args:
            file_path: Local file path
            bucket: S3 bucket name
            key: S3 object key (path)

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.upload_file(file_path, bucket, key)
            logger.info(f"Uploaded {file_path} to s3://{bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload {file_path}: {e}")
            return False

    def upload_data(self, data: bytes, bucket: str, key: str) -> bool:
        """Upload data directly to S3.

        Args:
            data: Data to upload
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.put_object(Bucket=bucket, Key=key, Body=data)
            logger.info(f"Uploaded data to s3://{bucket}/{key}")
            return True
        except Exception as e:
            logger.error(f"Failed to upload data to {key}: {e}")
            return False

    def create_bucket(self, bucket_name: str) -> bool:
        """Create S3 bucket.

        Args:
            bucket_name: Name of bucket to create

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": self.config["region"]}
            )
            logger.info(f"Created S3 bucket: {bucket_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to create bucket {bucket_name}: {e}")
            return False

    def list_objects(self, bucket: str, prefix: str = "") -> list:
        """List objects in S3 bucket.

        Args:
            bucket: S3 bucket name
            prefix: Optional prefix to filter by

        Returns:
            List of object keys
        """
        try:
            response = self.client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            if "Contents" not in response:
                return []
            return [obj["Key"] for obj in response["Contents"]]
        except Exception as e:
            logger.error(f"Failed to list objects in {bucket}: {e}")
            return []


class GlueClient:
    """Client for AWS Glue operations."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize Glue client.

        Args:
            config: AWS configuration
        """
        self.config = config
        self.client = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize boto3 Glue client."""
        try:
            import boto3
            self.client = boto3.client("glue", region_name=self.config["region"])
            logger.info(f"Initialized Glue client in region {self.config['region']}")
        except ImportError:
            raise ImportError("boto3 package is required. Install with: pip install boto3")

    def create_database(self, database_name: str, description: str = "") -> bool:
        """Create Glue database (catalog).

        Args:
            database_name: Name of database to create
            description: Optional description

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.create_database(
                DatabaseInput={"Name": database_name, "Description": description}
            )
            logger.info(f"Created Glue database: {database_name}")
            return True
        except self.client.exceptions.AlreadyExistsException:
            logger.info(f"Database {database_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create database {database_name}: {e}")
            return False

    def create_table(
        self, database_name: str, table_name: str, columns: Dict[str, str], s3_location: str
    ) -> bool:
        """Create Glue table metadata.

        Args:
            database_name: Glue database name
            table_name: Name of table to create
            columns: Dictionary of column_name: data_type
            s3_location: S3 path to data

        Returns:
            True if successful, False otherwise
        """
        try:
            column_definitions = [{"Name": name, "Type": dtype} for name, dtype in columns.items()]

            table_input = {
                "Name": table_name,
                "StorageDescriptor": {
                    "Columns": column_definitions,
                    "Location": s3_location,
                    "InputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat",
                    "OutputFormat": "org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat",
                    "SerdeInfo": {
                        "SerializationLibrary": "org.apache.hadoop.hive.serde2.lazy.LazySimpleSerDe"
                    },
                },
            }

            self.client.create_table(DatabaseName=database_name, TableInput=table_input)
            logger.info(f"Created Glue table: {database_name}.{table_name}")
            return True
        except self.client.exceptions.AlreadyExistsException:
            logger.info(f"Table {table_name} already exists")
            return True
        except Exception as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            return False

    def get_table(self, database_name: str, table_name: str) -> Optional[Dict[str, Any]]:
        """Get table metadata from Glue catalog.

        Args:
            database_name: Glue database name
            table_name: Table name

        Returns:
            Table metadata dictionary or None if not found
        """
        try:
            response = self.client.get_table(DatabaseName=database_name, Name=table_name)
            return response.get("Table")
        except self.client.exceptions.EntityNotFoundException:
            logger.info(f"Table {table_name} not found in Glue catalog")
            return None
        except Exception as e:
            logger.error(f"Failed to get table {table_name}: {e}")
            return None
