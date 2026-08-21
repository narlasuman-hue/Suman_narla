# Migration Architecture

Detailed architecture documentation for the Teradata to AWS migration system.

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Component Design](#component-design)
4. [Data Flow](#data-flow)
5. [Technology Stack](#technology-stack)
6. [Design Patterns](#design-patterns)
7. [Scalability Considerations](#scalability-considerations)

---

## System Overview

The migration system is designed to transfer Teradata tables to AWS S3 with automated schema registration in AWS Glue, enabling SQL querying through Athena.

### Goals

1. **Reliable Data Transfer**: Batch-based extraction with integrity checks
2. **Metadata Management**: Automatic schema capture and registration
3. **Flexibility**: Support multiple output formats (Parquet, CSV, JSON)
4. **Observability**: Comprehensive logging and validation
5. **Scalability**: Parallel extraction support for multiple tables

### Key Principles

- **Configuration-Driven**: YAML-based configuration with environment variable support
- **Separation of Concerns**: Independent modules for database, cloud, extraction logic
- **Error Resilience**: Detailed logging and error reporting
- **Type Safety**: Python type hints throughout codebase
- **Testability**: Mock-friendly design with dependency injection

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Migration System                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────┐ │
│  │   CLI Interface  │────▶│   Config Loader  │────▶│   Config.    │ │
│  │   (commands)     │     │  (MigrationCfg)  │     │   YAML       │ │
│  └──────────────────┘     └──────────────────┘     └──────────────┘ │
│           │                                                           │
│           ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Extraction Orchestrator                         │    │
│  │              (TableExtractor)                               │    │
│  └─────────────────────────────────────────────────────────────┘    │
│           │                     │                     │              │
│           ▼                     ▼                     ▼              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │ Teradata Client  │  │   S3 Client      │  │  Glue Client     │ │
│  │ (Extract Data)   │  │ (Upload Data)    │  │ (Register Meta)  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│           │                     │                     │              │
│           ▼                     ▼                     ▼              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   Teradata DB    │  │    AWS S3        │  │  AWS Glue Catalog│ │
│  │                  │  │                  │  │                  │ │
│  │ ✓ Connection     │  │ ✓ Raw Zone       │  │ ✓ Table Metadata │ │
│  │ ✓ Schema Fetch   │  │ ✓ Processed Zone │  │ ✓ Partitions     │ │
│  │ ✓ Data Batch     │  │ ✓ Metadata Zone  │  │ ✓ Partitions     │ │
│  │   Extraction     │  │                  │  │                  │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              Data Validation Layer                           │   │
│  │              (DataValidator)                                 │   │
│  │  ✓ Row Count Validation                                      │   │
│  │  ✓ Schema Validation                                         │   │
│  │  ✓ Checksum Validation                                       │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Design

### 1. Configuration Layer (`migration/config.py`)

**Purpose**: Load and manage migration configuration

**Key Classes**:
- `MigrationConfig`: Configuration manager

**Responsibilities**:
- Load YAML configuration files
- Substitute environment variables
- Provide typed access to configuration sections
- Support dotted notation for nested access

**Key Features**:
```python
# Environment variable substitution
teradata:
  host: "${TERADATA_HOST}"  # Replaced with env var value
  password: "${TERADATA_PASSWORD}"

# Dotted notation access
config.get("aws.region")        # "us-east-1"
config.get("migration.batch_size")  # 10000
```

---

### 2. Database Layer (`migration/teradata_client.py`)

**Purpose**: Encapsulate Teradata database operations

**Key Classes**:
- `TeradataClient`: Manages Teradata connections and queries

**Responsibilities**:
- Establish/close database connections
- Fetch table schemas
- Get row counts
- Extract data in batches
- Execute custom queries

**Design Decisions**:
- **Lazy Connection**: Connection established on demand in `connect()`
- **Batch Extraction**: Data fetched in configurable batches to manage memory
- **Schema as Dictionary**: Column info returned as name→type mapping
- **Generator Pattern**: `extract_table()` yields batches for memory efficiency

**Example Flow**:
```
connect() → get_table_schema() → get_row_count() → extract_table() → disconnect()
```

---

### 3. Cloud Layer (`migration/aws_client.py`)

**Purpose**: Manage AWS S3 and Glue operations

**Key Classes**:
- `S3Client`: S3 bucket and object operations
- `GlueClient`: Glue catalog metadata management

**S3Client Responsibilities**:
- Upload files and data to S3
- Create buckets
- List objects
- Handle S3 path conventions

**GlueClient Responsibilities**:
- Create databases in Glue catalog
- Create table metadata
- Retrieve table information
- Handle schema registration

**Design Decisions**:
- **Separation**: S3 and Glue operations in separate classes
- **Boto3 Abstraction**: Direct boto3 calls wrapped for future extensibility
- **Error Handling**: Graceful handling of pre-existing resources

---

### 4. Extraction Layer (`migration/extractor.py`)

**Purpose**: Orchestrate complete table extraction process

**Key Classes**:
- `TableExtractor`: Coordinates extraction from Teradata to S3

**Responsibilities**:
- Orchestrate Teradata client and S3 client
- Process extracted data into S3-compatible format
- Save extraction metadata (row counts, schemas)
- Handle multiple output formats (Parquet, CSV, JSON)
- Manage S3 key generation and organization

**Key Features**:
```
Extract Flow:
1. Get table schema and row count from Teradata
2. Extract data in batches
3. Convert each batch to output format (Parquet/CSV/JSON)
4. Upload to S3 raw zone with numbered batches
5. Save metadata (schema, counts) to metadata zone
```

**S3 Organization**:
```
s3://bucket/
├── raw/
│   └── schema/
│       └── table_name/
│           ├── batch_00001.parquet
│           ├── batch_00002.parquet
│           └── batch_00003.parquet
└── metadata/
    └── schema/
        └── table_name/
            └── extraction.json
```

---

### 5. Validation Layer (`migration/validator.py`)

**Purpose**: Validate data quality and integrity

**Key Classes**:
- `DataValidator`: Performs data quality checks

**Responsibilities**:
- Validate row counts
- Validate schema structure
- Validate checksums (when enabled)
- Generate validation reports

**Validation Types**:
- **Row Count**: Verify extracted rows match source
- **Schema**: Verify column count and types match
- **Checksum**: Optional cryptographic validation

---

### 6. CLI Layer (`migration/cli.py`)

**Purpose**: Provide command-line interface

**Key Classes**:
- `ArgumentParser` subcommands for different operations

**Commands**:
- `extract`: Extract tables from Teradata to S3
- `validate`: Validate extracted data
- `status`: Show migration status

**Design Pattern**:
- Command-driven architecture
- Subcommands map to functions
- Centralized error handling and logging

---

## Data Flow

### Extraction Flow

```
1. User Command
   └─▶ python -m migration extract --table schema.table1

2. CLI Processing
   ├─ Parse arguments
   ├─ Load configuration
   └─ Call extract_command()

3. Client Initialization
   ├─ Create TeradataClient
   ├─ Connect to Teradata
   ├─ Create S3Client
   └─ Create TableExtractor

4. Table Extraction
   ├─ Get table schema
   │  └─ SELECT * FROM table WHERE 1=0
   │     └─ Extract column info
   │
   ├─ Get row count
   │  └─ SELECT COUNT(*) FROM table
   │     └─ Log total rows
   │
   └─ Extract in batches
      ├─ Loop: fetch 10,000 rows
      ├─ Convert to format (Parquet/CSV/JSON)
      ├─ Upload to S3: raw/schema/table/batch_00001.parquet
      └─ Save metadata: metadata/schema/table/extraction.json

5. Completion
   └─ Log results and close connections
```

### Data Transformation

```
Teradata Row (tuple)
        │
        ▼
Convert to Dict
  {"id": 1, "name": "John", ...}
        │
        ▼
Batch as List[Dict]
  [{"id": 1, ...}, {"id": 2, ...}, ...]
        │
        ├─▶ Format: Parquet
        │   └─ pandas.DataFrame.to_parquet()
        │
        ├─▶ Format: CSV
        │   └─ pandas.DataFrame.to_csv()
        │
        └─▶ Format: JSON
            └─ json.dumps() of list
        │
        ▼
Upload to S3
```

---

## Technology Stack

### Core Technologies

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Language | Python | 3.8+ | Implementation |
| Database | Teradata | 17.0+ | Source data |
| Cloud | AWS | - | Target cloud |
| Config | YAML | - | Configuration |
| Testing | pytest | 7.0+ | Unit testing |

### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| boto3 | 1.26.0+ | AWS SDK |
| pandas | 1.5.0+ | Data manipulation |
| teradatasql | 17.0+ | Teradata driver |
| pyyaml | 6.0+ | YAML parsing |
| pyarrow | 25.0+ | Parquet support |

### Optional Dependencies

| Package | Purpose | Optional For |
|---------|---------|--------------|
| pytest-cov | Code coverage | Testing |
| ruff | Code linting | Development |
| mypy | Type checking | Development |
| black | Code formatting | Development |

---

## Design Patterns

### 1. Dependency Injection

All classes receive dependencies through constructor, enabling testing with mocks:

```python
# Production
td_client = TeradataClient(config.teradata_config)
extractor = TableExtractor(td_client, s3_client, config)

# Testing
extractor = TableExtractor(mock_td_client, mock_s3_client, config)
```

### 2. Generator Pattern

Large data extractions use generators for memory efficiency:

```python
# Batches processed without loading entire dataset
for batch in client.extract_table(table_name):
    # Process 10,000 rows at a time
    process_batch(batch)
```

### 3. Factory Pattern

Configuration creates appropriate client instances:

```python
config = MigrationConfig(file)
teradata_config = config.teradata_config  # Dict with all settings
client = TeradataClient(teradata_config)  # Factory-like instantiation
```

### 4. Facade Pattern

CLI and Extractor act as facades, hiding complexity:

```python
# Simple interface
extractor.extract_table(table_name)

# Complex operations hidden:
# - Connection management
# - Schema fetching
# - Batch processing
# - Error handling
# - Metadata saving
```

### 5. Strategy Pattern

Multiple output formats supported:

```python
def _save_batch(self, batch, format_type):
    if format_type == "parquet":
        data = df.to_parquet()
    elif format_type == "csv":
        data = df.to_csv().encode()
    elif format_type == "json":
        data = json.dumps(batch).encode()
```

---

## Scalability Considerations

### Current Limitations

1. **Single-Threaded Extraction**: One table at a time
2. **Memory-Bound Batch Size**: Configurable but tied to available RAM
3. **No Incremental Extraction**: Always full table load
4. **Sequential Batch Upload**: Batches uploaded one at a time

### Scalability Improvements

#### Parallel Table Extraction

```python
# Future enhancement
from concurrent.futures import ThreadPoolExecutor

with ThreadPoolExecutor(max_workers=5) as executor:
    futures = [
        executor.submit(extractor.extract_table, table)
        for table in tables
    ]
```

#### Parallel Batch Upload

```python
# Upload multiple batches in parallel
def upload_batches_parallel(batches, bucket, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(s3_client.upload_data, batch, bucket, key)
            for batch, key in batches
        ]
```

#### Incremental Extraction

```python
# Track last extraction time
# Query only rows: WHERE modified_timestamp > last_extraction_time
# Implement in TeradataClient.extract_incremental()
```

#### Multi-part Upload for Large Objects

```python
# For batches > 5GB, use S3 multipart upload
response = s3_client.create_multipart_upload(Bucket=bucket, Key=key)
# Upload parts in parallel
# Complete multipart upload
```

### Performance Optimization Strategies

| Strategy | Implementation | Impact |
|----------|----------------|--------|
| Batch Size Tuning | Adjust `batch_size` in config | Memory vs I/O trade-off |
| Compression | Enable snappy/gzip in config | Reduce S3 storage by 70-80% |
| Partitioning | Partition by date/range column | Faster Athena queries |
| Format Selection | Use Parquet for analytics | Better compression, faster queries |
| Connection Pooling | Maintain multiple connections | Higher throughput (future) |

### Load Testing Recommendations

```python
# Test configurations:
# Small: 100K rows, 10K batch size, serial
# Medium: 10M rows, 50K batch size, 2 parallel
# Large: 100M+ rows, 100K batch size, 5 parallel
```

---

## Error Handling Strategy

### Error Types and Recovery

| Error Type | Cause | Recovery |
|-----------|-------|----------|
| Connection Error | Unreachable Teradata | Retry with backoff |
| Authentication | Invalid credentials | Fail fast, check config |
| S3 Upload Failed | Network/permissions | Retry batch upload |
| Out of Memory | Batch size too large | Reduce batch size, restart |
| Missing Table | Wrong table name | Skip, continue next table |
| Schema Mismatch | Data type issue | Log warning, continue |

### Logging Strategy

```
Level    | Usage                          | Examples
---------|--------------------------------|-------------------
DEBUG    | Detailed operational info      | Batch details, row counts
INFO     | Progress and milestones        | Table extraction start/end
WARNING  | Recoverable issues             | Validation warnings, skips
ERROR    | Failure requiring attention    | Connection failed, upload error
CRITICAL | System-level failures          | Out of disk space
```

---

## Security Considerations

### Credential Management

1. **Environment Variables**: All sensitive values in .env, never in code
2. **IAM Roles**: Use AWS IAM for S3 and Glue access (not keys when possible)
3. **VPN/Direct Connect**: For on-premises Teradata connections
4. **SSL/TLS**: Enable encryption in transit

### Data Protection

1. **Encryption at Rest**: Enable S3 server-side encryption
2. **Encryption in Transit**: Use HTTPS/TLS for all connections
3. **Access Control**: Restrict S3 bucket access with bucket policies
4. **Audit Logging**: Enable CloudTrail for S3 and Glue operations

### Code Security

1. **Input Validation**: Sanitize table names in SQL queries
2. **Dependency Scanning**: Use pip-audit to check for vulnerabilities
3. **No Hardcoded Secrets**: Use environment variables
4. **Secure Configuration**: YAML files not committed with secrets

---

## Monitoring and Observability

### Metrics to Track

- Extraction time per table
- Rows extracted per second (throughput)
- S3 upload bandwidth
- Error rates and types
- Data validation success rate

### Logging Output

```
[2024-01-15 10:30:45,123] migration.extractor - INFO - Starting extraction of mydb.customers
[2024-01-15 10:30:45,456] migration.teradata_client - DEBUG - Retrieved schema for mydb.customers: 5 columns
[2024-01-15 10:30:45,789] migration.teradata_client - DEBUG - Row count for mydb.customers: 1000000
[2024-01-15 10:30:46,234] migration.extractor - DEBUG - Saved batch 1 (1000 rows) to raw/mydb/customers/batch_00001.parquet
...
[2024-01-15 10:35:12,567] migration.extractor - INFO - Successfully extracted mydb.customers: 1000000 rows in 10 batches
```

---

## Future Enhancements

### Phase 2 Features

1. **Change Data Capture (CDC)**: Incremental extraction for updates
2. **Parallel Extraction**: Extract multiple tables concurrently
3. **Data Transformation**: Built-in ETL transformations
4. **Partition Pruning**: Automatic intelligent partitioning
5. **Deduplication**: Handle duplicate row detection

### Phase 3 Features

1. **Real-time Sync**: Streaming ingestion with Kinesis
2. **Data Quality Framework**: Advanced validation rules
3. **Performance Tuning**: Auto-optimization of batch sizes
4. **Cost Optimization**: Right-sizing S3 storage classes
5. **Multi-region**: Cross-region replication

### Long-term Vision

- **Zero-Copy Data Transfer**: Native cloud data exchange formats
- **AI-powered Optimization**: ML-based parameter tuning
- **Federated Queries**: Query across Teradata and AWS simultaneously
- **Automated Rollback**: Versioning and point-in-time recovery
- **Multi-cloud Support**: Support for Azure, GCP, etc.
