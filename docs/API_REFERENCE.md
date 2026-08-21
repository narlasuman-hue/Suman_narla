# Migration API Reference

Complete API documentation for the Teradata to AWS migration framework.

## Table of Contents

1. [Configuration Module](#configuration-module)
2. [Teradata Client](#teradata-client)
3. [AWS Clients](#aws-clients)
4. [Data Extractor](#data-extractor)
5. [Data Validator](#data-validator)
6. [CLI Interface](#cli-interface)

---

## Configuration Module

### `migration.config.MigrationConfig`

Manages loading and accessing migration configuration from YAML files with environment variable substitution.

#### Constructor

```python
MigrationConfig(config_file: str)
```

**Parameters:**
- `config_file` (str): Path to YAML configuration file

**Example:**
```python
from migration.config import MigrationConfig

config = MigrationConfig("config/migration_config.yaml")
```

#### Properties

##### `teradata_config`
Returns Teradata connection configuration dictionary.

```python
config_dict = config.teradata_config
# Returns: {
#   "host": "localhost",
#   "port": 1025,
#   "username": "user",
#   "password": "pass",
#   ...
# }
```

##### `aws_config`
Returns AWS configuration dictionary.

```python
aws_dict = config.aws_config
# Returns: {
#   "region": "us-east-1",
#   "s3_bucket_raw": "bucket-name",
#   ...
# }
```

##### `migration_config`
Returns migration settings dictionary.

```python
migration_dict = config.migration_config
# Returns: {
#   "batch_size": 10000,
#   "format": "parquet",
#   ...
# }
```

##### `tables`
Returns list of table configurations to migrate.

```python
tables = config.tables
# Returns: [
#   {"name": "schema.table1", "enabled": True, ...},
#   {"name": "schema.table2", "enabled": False, ...}
# ]
```

#### Methods

##### `get(key: str, default: Any = None) -> Any`

Get configuration value using dotted notation.

**Parameters:**
- `key` (str): Dotted path to config value (e.g., "aws.region")
- `default` (Any, optional): Default value if key not found

**Returns:** Configuration value or default

**Example:**
```python
region = config.get("aws.region", "us-east-1")
batch_size = config.get("migration.batch_size")
```

---

## Teradata Client

### `migration.teradata_client.TeradataClient`

Manages connections to Teradata database and data extraction operations.

#### Constructor

```python
TeradataClient(config: Dict[str, Any])
```

**Parameters:**
- `config` (Dict): Teradata configuration with keys: `host`, `port`, `username`, `password`, `connection_timeout`

**Example:**
```python
from migration.teradata_client import TeradataClient
from migration.config import MigrationConfig

config = MigrationConfig("config/migration_config.yaml")
client = TeradataClient(config.teradata_config)
client.connect()
```

#### Methods

##### `connect() -> None`

Establish connection to Teradata database.

**Raises:**
- `ImportError`: If teradatasql package not installed
- `Exception`: If connection fails

**Example:**
```python
client = TeradataClient(config.teradata_config)
client.connect()
```

##### `disconnect() -> None`

Close Teradata connection.

**Example:**
```python
client.disconnect()
```

##### `get_table_schema(table_name: str) -> Dict[str, Any]`

Get table schema information.

**Parameters:**
- `table_name` (str): Fully qualified table name (schema.table)

**Returns:** Dictionary with column names as keys and data types as values

**Example:**
```python
schema = client.get_table_schema("mydb.customers")
# Returns: {
#   "customer_id": "INTEGER",
#   "name": "VARCHAR(100)",
#   "created_at": "TIMESTAMP"
# }
```

##### `get_row_count(table_name: str) -> int`

Get total row count for a table.

**Parameters:**
- `table_name` (str): Fully qualified table name

**Returns:** Number of rows in table

**Example:**
```python
count = client.get_row_count("mydb.customers")
# Returns: 1000000
```

##### `extract_table(table_name: str, batch_size: int = 10000)`

Extract all rows from a table in batches.

**Parameters:**
- `table_name` (str): Fully qualified table name
- `batch_size` (int): Number of rows per batch (default: 10000)

**Yields:** List of row dictionaries

**Example:**
```python
for batch in client.extract_table("mydb.customers", batch_size=5000):
    print(f"Extracted {len(batch)} rows")
    for row in batch:
        print(row)
```

##### `execute_query(query: str) -> List[tuple]`

Execute custom SQL query.

**Parameters:**
- `query` (str): SQL query to execute

**Returns:** List of result tuples

**Example:**
```python
results = client.execute_query("SELECT COUNT(*) FROM mydb.customers WHERE status = 'active'")
```

---

## AWS Clients

### `migration.aws_client.S3Client`

Manages S3 bucket operations for uploading data.

#### Constructor

```python
S3Client(config: Dict[str, Any])
```

**Parameters:**
- `config` (Dict): AWS configuration with `region` key

**Example:**
```python
from migration.aws_client import S3Client
from migration.config import MigrationConfig

config = MigrationConfig("config/migration_config.yaml")
s3 = S3Client(config.aws_config)
```

#### Methods

##### `upload_file(file_path: str, bucket: str, key: str) -> bool`

Upload file to S3 bucket.

**Parameters:**
- `file_path` (str): Local file path
- `bucket` (str): S3 bucket name
- `key` (str): S3 object key (path)

**Returns:** True if successful, False otherwise

**Example:**
```python
success = s3.upload_file("/local/file.parquet", "my-bucket", "data/file.parquet")
```

##### `upload_data(data: bytes, bucket: str, key: str) -> bool`

Upload data directly to S3.

**Parameters:**
- `data` (bytes): Data to upload
- `bucket` (str): S3 bucket name
- `key` (str): S3 object key

**Returns:** True if successful, False otherwise

**Example:**
```python
data = b"some data"
success = s3.upload_data(data, "my-bucket", "data/file.txt")
```

##### `create_bucket(bucket_name: str) -> bool`

Create S3 bucket.

**Parameters:**
- `bucket_name` (str): Name of bucket to create

**Returns:** True if successful, False otherwise

**Example:**
```python
success = s3.create_bucket("my-new-bucket")
```

##### `list_objects(bucket: str, prefix: str = "") -> list`

List objects in S3 bucket.

**Parameters:**
- `bucket` (str): S3 bucket name
- `prefix` (str, optional): Filter by prefix

**Returns:** List of object keys

**Example:**
```python
objects = s3.list_objects("my-bucket", prefix="data/")
# Returns: ["data/file1.parquet", "data/file2.parquet"]
```

### `migration.aws_client.GlueClient`

Manages AWS Glue catalog operations for metadata management.

#### Constructor

```python
GlueClient(config: Dict[str, Any])
```

**Parameters:**
- `config` (Dict): AWS configuration with `region` key

**Example:**
```python
from migration.aws_client import GlueClient
from migration.config import MigrationConfig

config = MigrationConfig("config/migration_config.yaml")
glue = GlueClient(config.aws_config)
```

#### Methods

##### `create_database(database_name: str, description: str = "") -> bool`

Create Glue database (catalog).

**Parameters:**
- `database_name` (str): Database name
- `description` (str, optional): Database description

**Returns:** True if successful, False otherwise

**Example:**
```python
success = glue.create_database("migration_db", "Migrated Teradata tables")
```

##### `create_table(database_name: str, table_name: str, columns: Dict[str, str], s3_location: str) -> bool`

Create Glue table metadata.

**Parameters:**
- `database_name` (str): Glue database name
- `table_name` (str): Table name
- `columns` (Dict[str, str]): Column definitions {name: datatype}
- `s3_location` (str): S3 path to data

**Returns:** True if successful, False otherwise

**Example:**
```python
columns = {
    "customer_id": "bigint",
    "name": "string",
    "created_at": "timestamp"
}
success = glue.create_table(
    "migration_db",
    "customers",
    columns,
    "s3://bucket/raw/customers/"
)
```

##### `get_table(database_name: str, table_name: str) -> Optional[Dict[str, Any]]`

Get table metadata from Glue catalog.

**Parameters:**
- `database_name` (str): Database name
- `table_name` (str): Table name

**Returns:** Table metadata dictionary or None if not found

**Example:**
```python
table = glue.get_table("migration_db", "customers")
if table:
    print(table["StorageDescriptor"]["Location"])
```

---

## Data Extractor

### `migration.extractor.TableExtractor`

Orchestrates extraction of Teradata tables to S3 with metadata tracking.

#### Constructor

```python
TableExtractor(
    teradata_client: TeradataClient,
    s3_client: S3Client,
    config: Dict[str, Any]
)
```

**Parameters:**
- `teradata_client` (TeradataClient): Connected Teradata client
- `s3_client` (S3Client): Initialized S3 client
- `config` (Dict): Full migration configuration

**Example:**
```python
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient
from migration.aws_client import S3Client
from migration.extractor import TableExtractor

config = MigrationConfig("config/migration_config.yaml")
td_client = TeradataClient(config.teradata_config)
td_client.connect()
s3_client = S3Client(config.aws_config)

extractor = TableExtractor(td_client, s3_client, config.config)
```

#### Methods

##### `extract_table(table_name: str, output_format: str = "parquet") -> bool`

Extract table from Teradata to S3.

**Parameters:**
- `table_name` (str): Fully qualified table name (schema.table)
- `output_format` (str): Output format - "parquet" (default), "csv", or "json"

**Returns:** True if successful, False otherwise

**Example:**
```python
success = extractor.extract_table("mydb.customers", output_format="parquet")
if success:
    print("Extraction completed successfully")
else:
    print("Extraction failed")
```

**Output Structure:**
```
S3 Layout:
├── raw/mydb/customers/
│   ├── batch_00001.parquet
│   ├── batch_00002.parquet
│   └── ...
└── metadata/mydb/customers/
    └── extraction.json
```

---

## Data Validator

### `migration.validator.DataValidator`

Validates extracted data quality and integrity.

#### Constructor

```python
DataValidator(teradata_client: TeradataClient, config: Dict[str, Any])
```

**Parameters:**
- `teradata_client` (TeradataClient): Connected Teradata client
- `config` (Dict): Full migration configuration

**Example:**
```python
from migration.validator import DataValidator
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient

config = MigrationConfig("config/migration_config.yaml")
td_client = TeradataClient(config.teradata_config)
td_client.connect()

validator = DataValidator(td_client, config.config)
```

#### Methods

##### `validate_table(table_name: str) -> Dict[str, Any]`

Validate single table data.

**Parameters:**
- `table_name` (str): Fully qualified table name

**Returns:** Validation result dictionary with status, checks, and errors

**Example:**
```python
result = validator.validate_table("mydb.customers")
# Returns: {
#   "table": "mydb.customers",
#   "status": "passed",
#   "checks": {
#     "row_count": 1000000,
#     "columns": 10
#   },
#   "errors": []
# }
```

##### `validate_all(tables: list) -> Dict[str, Any]`

Validate multiple tables.

**Parameters:**
- `tables` (list): List of table names

**Returns:** Combined validation results

**Example:**
```python
results = validator.validate_all(["mydb.customers", "mydb.orders"])
# Returns: {
#   "total_tables": 2,
#   "passed": 2,
#   "failed": 0,
#   "status": "passed",
#   "tables": {...}
# }
```

---

## CLI Interface

### Command: `extract`

Extract data from Teradata to S3.

```bash
python -m migration extract [OPTIONS]
```

**Options:**
- `--config FILE`: Path to configuration file (default: config/migration_config.yaml)
- `--table NAME`: Specific table to extract (optional; if not provided, extracts all enabled tables)
- `--format FORMAT`: Output format: parquet (default), csv, or json

**Examples:**
```bash
# Extract all enabled tables
python -m migration extract --config config/migration_config.yaml

# Extract specific table
python -m migration extract --table mydb.customers --config config/migration_config.yaml

# Extract as CSV
python -m migration extract --table mydb.customers --format csv
```

### Command: `validate`

Validate extracted data quality.

```bash
python -m migration validate [OPTIONS]
```

**Options:**
- `--config FILE`: Path to configuration file (default: config/migration_config.yaml)
- `--table NAME`: Specific table to validate (optional)

**Examples:**
```bash
# Validate all tables
python -m migration validate --config config/migration_config.yaml

# Validate specific table
python -m migration validate --table mydb.customers
```

### Command: `status`

Show migration status for all tables.

```bash
python -m migration status [OPTIONS]
```

**Options:**
- `--config FILE`: Path to configuration file (default: config/migration_config.yaml)

**Example:**
```bash
python -m migration status --config config/migration_config.yaml
```

**Output:**
```
Migration Status Report
==================================================
[ACTIVE] mydb.customers: 1,000,000 rows
[ACTIVE] mydb.orders: 5,000,000 rows
[DISABLED] mydb.temp_table
```

---

## Configuration File Format

Complete YAML configuration structure:

```yaml
# Teradata Connection
teradata:
  host: "teradata-hostname"          # Required
  port: 1025                          # Optional, default 1025
  username: "${TERADATA_USER}"        # Use env vars for secrets
  password: "${TERADATA_PASSWORD}"
  database: "default_db"
  connection_timeout: 30              # Seconds

# AWS Configuration
aws:
  region: "us-east-1"                # Required
  s3_bucket_raw: "bucket-raw"        # Raw data location
  s3_bucket_processed: "bucket-proc" # Processed data location
  s3_bucket_metadata: "bucket-meta"  # Metadata location
  glue_role_arn: "${AWS_GLUE_ROLE_ARN}"

# Migration Settings
migration:
  batch_size: 10000                  # Rows per extraction batch
  format: "parquet"                  # parquet, csv, or json
  compression: "snappy"              # snappy, gzip, none
  partition_strategy: "date"         # Partitioning strategy
  max_parallel_extracts: 5           # Concurrent extraction jobs

# Data Quality Checks
quality:
  enable_row_count_validation: true
  enable_checksum_validation: true
  enable_schema_validation: true
  null_handling: "preserve"

# Logging Configuration
logging:
  level: "INFO"                       # DEBUG, INFO, WARNING, ERROR
  log_file: "logs/migration.log"

# Tables to Migrate
tables:
  - name: "schema.table1"
    enabled: true
    full_load: true
    partition_column: null
  - name: "schema.table2"
    enabled: true
    full_load: true
    partition_column: "date_column"
```

---

## Error Handling

### Common Exceptions

| Exception | Cause | Solution |
|-----------|-------|----------|
| `ModuleNotFoundError` | Missing dependency | `pip install -r requirements-dev.txt` |
| `ConnectionError` | Cannot connect to Teradata | Check host, port, credentials, network |
| `S3UploadError` | S3 upload failed | Check AWS credentials, bucket permissions, network |
| `FileNotFoundError` | Config file not found | Verify config file path |
| `ValueError` | Invalid configuration | Check YAML syntax and required fields |

### Logging

All modules use Python's `logging` module. Configure logging level:

```python
import logging

# Set to DEBUG for detailed output
logging.basicConfig(level=logging.DEBUG)
```

---

## Usage Examples

### Complete Extraction Workflow

```python
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient
from migration.aws_client import S3Client
from migration.extractor import TableExtractor
from migration.validator import DataValidator

# Load configuration
config = MigrationConfig("config/migration_config.yaml")

# Initialize clients
td_client = TeradataClient(config.teradata_config)
td_client.connect()

s3_client = S3Client(config.aws_config)

# Extract tables
extractor = TableExtractor(td_client, s3_client, config.config)
for table in config.tables:
    if table.get("enabled"):
        print(f"Extracting {table['name']}...")
        success = extractor.extract_table(table["name"])
        print(f"  Status: {'✓' if success else '✗'}")

# Validate data
validator = DataValidator(td_client, config.config)
results = validator.validate_all([t["name"] for t in config.tables if t.get("enabled")])
print(f"Validation: {results['passed']}/{results['total_tables']} passed")

# Cleanup
td_client.disconnect()
```

### Custom Extraction Script

```python
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient

config = MigrationConfig("config/migration_config.yaml")
td_client = TeradataClient(config.teradata_config)
td_client.connect()

# Get table info
schema = td_client.get_table_schema("mydb.customers")
count = td_client.get_row_count("mydb.customers")

print(f"Table: mydb.customers")
print(f"Rows: {count:,}")
print(f"Columns: {len(schema)}")
for col, dtype in schema.items():
    print(f"  - {col}: {dtype}")

td_client.disconnect()
```

---

## Best Practices

1. **Use environment variables** for sensitive credentials (host, username, password)
2. **Test with small tables first** before running full extractions
3. **Monitor logs** for warnings and errors during extraction
4. **Validate data** after extraction to ensure integrity
5. **Keep backups** of configuration files with table lists
6. **Run extractions during off-peak hours** to minimize Teradata load
7. **Check disk space** on S3 buckets before large extractions
8. **Document custom modifications** to extraction logic
