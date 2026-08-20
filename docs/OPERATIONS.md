# Operations Guide

Complete guide for deploying, operating, and troubleshooting the Teradata to AWS migration system.

## Table of Contents

1. [Deployment](#deployment)
2. [Configuration](#configuration)
3. [Running Migrations](#running-migrations)
4. [Monitoring](#monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Maintenance](#maintenance)
7. [Best Practices](#best-practices)

---

## Deployment

### Prerequisites

- Python 3.8 or higher
- Access to Teradata database (network connectivity)
- AWS Account with S3 and Glue permissions
- Git for version control

### Installation Steps

#### 1. Clone the Repository

```bash
git clone https://github.com/narlasuman-hue/Suman_narla.git
cd Suman_narla
```

#### 2. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements-dev.txt
```

#### 4. Install Package in Development Mode

```bash
pip install -e .
```

#### 5. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
nano .env  # or your preferred editor

# Source environment variables
source .env  # On Windows: .env would need to be set manually
```

#### 6. Create Configuration File

```bash
# Copy example configuration
cp config/migration_config.yaml config/migration_config.local.yaml

# Edit with your specific tables and settings
nano config/migration_config.local.yaml
```

#### 7. Verify Installation

```bash
# Run tests to verify everything works
pytest tests/ -v

# Check CLI
python -m migration --help
```

---

### AWS Infrastructure Setup

#### 1. Create S3 Buckets

```bash
# Raw data bucket
aws s3 mb s3://teradata-migration-raw --region us-east-1

# Processed data bucket
aws s3 mb s3://teradata-migration-processed --region us-east-1

# Metadata bucket
aws s3 mb s3://teradata-migration-metadata --region us-east-1
```

#### 2. Create IAM Role for Glue

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::teradata-migration-*/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "glue:CreateDatabase",
        "glue:CreateTable",
        "glue:UpdateTable",
        "glue:GetDatabase",
        "glue:GetTable"
      ],
      "Resource": "*"
    }
  ]
}
```

#### 3. Configure AWS Credentials

```bash
# Using AWS CLI
aws configure

# Or set environment variables
export AWS_ACCESS_KEY_ID=your-key
export AWS_SECRET_ACCESS_KEY=your-secret
export AWS_DEFAULT_REGION=us-east-1
```

#### 4. Verify AWS Access

```bash
# Test S3 access
aws s3 ls

# Test Glue access
aws glue list-databases
```

---

### Network Configuration

#### For On-Premises Teradata

**Option 1: VPN**
```
1. Set up VPN tunnel to data center
2. Configure Teradata host via VPN IP
3. Test connectivity:
   nc -zv teradata-host 1025
```

**Option 2: AWS Direct Connect**
```
1. Request Direct Connect virtual interface
2. Configure BGP routing
3. Peer with on-premises network
```

**Option 3: SSH Tunnel**
```bash
# Create SSH tunnel to bastion host
ssh -L 1025:teradata-host:1025 bastion-host
# Configure migration to connect via localhost:1025
```

#### For Teradata in AWS

```
1. Ensure security group allows inbound 1025
2. Use internal hostname/IP
3. No special network configuration needed
```

---

## Configuration

### Environment Variables

Create `.env` file with:

```bash
# Teradata Connection
TERADATA_HOST=your-teradata-host
TERADATA_PORT=1025
TERADATA_USER=your_username
TERADATA_PASSWORD=your_password
TERADATA_DATABASE=your_database

# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_GLUE_ROLE_ARN=arn:aws:iam::ACCOUNT:role/glue-role

# S3 Buckets
S3_BUCKET_RAW=teradata-migration-raw
S3_BUCKET_PROCESSED=teradata-migration-processed
S3_BUCKET_METADATA=teradata-migration-metadata

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/migration.log
```

### YAML Configuration

Edit `config/migration_config.local.yaml`:

```yaml
teradata:
  host: "${TERADATA_HOST}"
  port: 1025
  username: "${TERADATA_USER}"
  password: "${TERADATA_PASSWORD}"
  database: "${TERADATA_DATABASE}"
  connection_timeout: 30

aws:
  region: "${AWS_REGION}"
  s3_bucket_raw: "${S3_BUCKET_RAW}"
  s3_bucket_processed: "${S3_BUCKET_PROCESSED}"
  s3_bucket_metadata: "${S3_BUCKET_METADATA}"
  glue_role_arn: "${AWS_GLUE_ROLE_ARN}"

migration:
  batch_size: 10000
  format: "parquet"
  compression: "snappy"
  max_parallel_extracts: 5

quality:
  enable_row_count_validation: true
  enable_schema_validation: true

logging:
  level: "${LOG_LEVEL}"
  log_file: "${LOG_FILE}"

tables:
  - name: "schema1.table1"
    enabled: true
    partition_column: null
  - name: "schema1.table2"
    enabled: true
    partition_column: "date_column"
  - name: "schema2.table3"
    enabled: false
```

---

## Running Migrations

### Pre-Migration Checklist

- [ ] Teradata connectivity verified
- [ ] AWS credentials configured
- [ ] S3 buckets created
- [ ] Configuration file updated with tables
- [ ] Tests pass locally
- [ ] Disk space available (at least 2x largest table)
- [ ] Network bandwidth tested
- [ ] Backup of configuration taken

### Step-by-Step Migration

#### Step 1: Test Configuration

```bash
# Test Teradata connection
python -m migration status --config config/migration_config.local.yaml

# Expected output:
# Migration Status Report
# ==================================================
# [ACTIVE] schema1.table1: 1,000,000 rows
# [ACTIVE] schema1.table2: 5,000,000 rows
# [DISABLED] schema2.table3
```

#### Step 2: Start with Small Table

```bash
# Extract a small table first
python -m migration extract \
  --table schema1.table1 \
  --config config/migration_config.local.yaml \
  --format parquet

# Monitor logs
tail -f logs/migration.log
```

#### Step 3: Verify Extracted Data

```bash
# Check S3 for data
aws s3 ls s3://teradata-migration-raw/schema1/table1/

# Check metadata
aws s3 cp s3://teradata-migration-metadata/schema1/table1/extraction.json - | jq

# Validate data
python -m migration validate \
  --table schema1.table1 \
  --config config/migration_config.local.yaml
```

#### Step 4: Extract All Tables

```bash
# Extract all enabled tables
python -m migration extract --config config/migration_config.local.yaml 2>&1 | tee migration.log

# Monitor progress
watch -n 10 'tail -20 logs/migration.log'
```

#### Step 5: Validate All Data

```bash
# Run comprehensive validation
python -m migration validate --config config/migration_config.local.yaml
```

#### Step 6: Register in Glue Catalog

```python
# Create Glue database
from migration.aws_client import GlueClient
from migration.config import MigrationConfig

config = MigrationConfig("config/migration_config.local.yaml")
glue = GlueClient(config.aws_config)
glue.create_database("teradata_migration", "Migrated Teradata tables")

# Manually register tables (currently manual process)
# Future: Automate from extraction metadata
```

#### Step 7: Test Athena Queries

```sql
-- Query extracted data in Athena
SELECT * FROM teradata_migration.schema1_table1 LIMIT 10;

-- Verify row count
SELECT COUNT(*) FROM teradata_migration.schema1_table1;
```

---

## Monitoring

### Log Monitoring

#### Real-Time Monitoring

```bash
# Follow logs in real-time
tail -f logs/migration.log

# Follow with grep filter
tail -f logs/migration.log | grep -i error

# Count errors
grep -c ERROR logs/migration.log
```

#### Log Analysis

```bash
# View extraction progress
grep "Saved batch" logs/migration.log | tail -20

# Check for warnings
grep -i warning logs/migration.log

# Summary of completed tables
grep "Successfully extracted" logs/migration.log
```

### S3 Monitoring

```bash
# Monitor S3 data size
aws s3 ls s3://teradata-migration-raw/ --recursive --summarize

# Check S3 costs (using S3 Storage Lens)
# https://console.aws.amazon.com/s3/

# List tables extracted
aws s3 ls s3://teradata-migration-raw/ --recursive | awk '{print $NF}' | cut -d'/' -f3 | sort -u
```

### Extraction Metrics

```bash
# Extract from logs
python << 'EOF'
import re
from datetime import datetime

with open('logs/migration.log') as f:
    lines = f.readlines()

for line in lines:
    if "Successfully extracted" in line:
        # Parse: Successfully extracted schema.table: 1000000 rows in 10 batches
        match = re.search(r'(\w+\.\w+): (\d+) rows in (\d+) batches', line)
        if match:
            table, rows, batches = match.groups()
            print(f"{table}: {rows} rows, {batches} batches")
EOF
```

### AWS Cost Monitoring

```bash
# Estimate S3 costs
python << 'EOF'
import subprocess
import json

# Get total S3 usage
result = subprocess.run(
    ['aws', 's3', 'ls', 's3://teradata-migration-raw/', '--recursive', '--summarize'],
    capture_output=True, text=True
)

# Parse output to get total bytes
lines = result.stdout.split('\n')
for line in lines:
    if 'Total Size' in line:
        print(f"Total S3 Size: {line}")
        # Calculate cost: ~$0.023 per GB/month
        size_gb = int(line.split(':')[1].strip().split()[0]) / (1024**3)
        cost = size_gb * 0.023
        print(f"Estimated Monthly Cost: ${cost:.2f}")
EOF
```

---

## Troubleshooting

### Connection Issues

#### Teradata Connection Fails

```bash
# Test basic connectivity
nc -zv teradata-host 1025

# Check with telnet
telnet teradata-host 1025

# Verify credentials
python << 'EOF'
import teradatasql
try:
    conn = teradatasql.connect(
        host="teradata-host",
        user="username",
        password="password"
    )
    print("Connection successful!")
    conn.close()
except Exception as e:
    print(f"Connection failed: {e}")
EOF

# Check Teradata version
python << 'EOF'
import teradatasql
conn = teradatasql.connect(host="...", user="...", password="...")
cursor = conn.cursor()
cursor.execute("SELECT * FROM dbc.dbcinfo")
print(cursor.fetchone())
conn.close()
EOF
```

#### S3 Upload Fails

```bash
# Test S3 access
aws s3 ls s3://teradata-migration-raw/

# Check bucket permissions
aws s3api get-bucket-acl --bucket teradata-migration-raw

# Test upload
echo "test" | aws s3 cp - s3://teradata-migration-raw/test.txt

# Check bucket policy
aws s3api get-bucket-policy --bucket teradata-migration-raw
```

### Data Quality Issues

#### Row Count Mismatch

```bash
# Get source row count
python << 'EOF'
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient

config = MigrationConfig("config/migration_config.local.yaml")
client = TeradataClient(config.teradata_config)
client.connect()

count = client.get_row_count("schema.table")
print(f"Source: {count} rows")

client.disconnect()
EOF

# Count rows in S3
python << 'EOF'
import pandas as pd
import boto3

s3 = boto3.client('s3')
bucket = 'teradata-migration-raw'
prefix = 'raw/schema/table/'

response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
total_rows = 0

for obj in response.get('Contents', []):
    if obj['Key'].endswith('.parquet'):
        df = pd.read_parquet(f"s3://{bucket}/{obj['Key']}")
        total_rows += len(df)
        print(f"{obj['Key']}: {len(df)} rows")

print(f"Total: {total_rows} rows")
EOF
```

#### Schema Mismatch

```bash
# Compare schemas
python << 'EOF'
from migration.config import MigrationConfig
from migration.teradata_client import TeradataClient

config = MigrationConfig("config/migration_config.local.yaml")
client = TeradataClient(config.teradata_config)
client.connect()

schema = client.get_table_schema("schema.table")
client.disconnect()

print("Source Schema:")
for col, dtype in schema.items():
    print(f"  {col}: {dtype}")
EOF

# Check metadata in S3
aws s3 cp s3://teradata-migration-metadata/schema/table/extraction.json - | jq '.schema'
```

### Performance Issues

#### Slow Extraction

```bash
# Monitor during extraction
python << 'EOF'
import subprocess
import time

while True:
    result = subprocess.run(
        ['tail', '-1', 'logs/migration.log'],
        capture_output=True, text=True
    )
    print(f"[{time.strftime('%H:%M:%S')}] {result.stdout.strip()}")
    time.sleep(5)
EOF

# Increase batch size in config
migration:
  batch_size: 50000  # Increase from 10000

# Increase parallel extractions
migration:
  max_parallel_extracts: 10  # Increase from 5
```

#### High Memory Usage

```bash
# Reduce batch size in config
migration:
  batch_size: 5000  # Decrease from 10000

# Monitor system resources during run
watch -n 1 'free -h && df -h'

# Profile memory usage
python -m memory_profiler migration/__main__.py extract
```

#### Slow S3 Upload

```bash
# Check S3 transfer rate
python << 'EOF'
import time
import boto3

s3 = boto3.client('s3')
bucket = 'teradata-migration-raw'

# Time an upload
test_data = b"x" * (100 * 1024 * 1024)  # 100MB

start = time.time()
s3.put_object(Bucket=bucket, Key='test-upload', Body=test_data)
elapsed = time.time() - start
rate = (100 / elapsed) if elapsed > 0 else 0

print(f"Upload rate: {rate:.1f} MB/s")
s3.delete_object(Bucket=bucket, Key='test-upload')
EOF

# Solutions:
# - Increase AWS region bandwidth
# - Use S3 Transfer Acceleration
# - Optimize batch size and compression
```

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError: teradatasql` | Driver not installed | `pip install teradatasql` |
| `Connection refused` | Teradata unreachable | Check host, port, network connectivity |
| `Access denied` | Bad credentials | Verify username/password |
| `NoCredentialsError` | AWS creds not found | Set AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY |
| `NoSuchBucket` | S3 bucket doesn't exist | Create bucket: `aws s3 mb s3://bucket-name` |
| `MemoryError` | Batch too large | Reduce batch_size in config |
| `ConnectionTimeout` | Slow network | Increase connection_timeout in config |

---

## Maintenance

### Cleanup Operations

#### Remove Test Data

```bash
# Clean S3 test uploads
aws s3 rm s3://teradata-migration-raw/test/ --recursive

# Remove local logs
rm logs/*.log

# Remove Python cache
find . -type d -name __pycache__ -exec rm -r {} +
rm -rf .pytest_cache htmlcov
```

#### Archive Old Extractions

```bash
# Move old data to Glacier
aws s3 sync \
  s3://teradata-migration-raw/old-data/ \
  s3://teradata-migration-archive/old-data/ \
  --storage-class GLACIER

# Delete from hot tier
aws s3 rm s3://teradata-migration-raw/old-data/ --recursive
```

### Updating Configuration

```bash
# Add new table to config
# Edit migration_config.local.yaml and add:
  - name: "schema.new_table"
    enabled: true
    partition_column: null

# Test new table
python -m migration status --config config/migration_config.local.yaml
```

### Updating Code

```bash
# Update to latest version
git pull origin main

# Install new dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Restart migrations
python -m migration extract --config config/migration_config.local.yaml
```

---

## Best Practices

### Pre-Migration

1. **Inventory Tables**: Document all Teradata tables and schemas
2. **Estimate Data Volume**: Calculate total GB to transfer
3. **Test Network**: Verify bandwidth and latency
4. **Secure Credentials**: Use environment variables, never hardcode
5. **Plan Schedule**: Run during off-peak hours
6. **Document Dependencies**: Note table relationships and foreign keys

### During Migration

1. **Monitor Progress**: Watch logs and S3 metrics
2. **Don't Interrupt**: Let extractions complete cleanly
3. **Verify Each Table**: Validate row counts after each extraction
4. **Keep Logs**: Archive logs for auditing
5. **Track Timing**: Note extraction time for performance analysis

### Post-Migration

1. **Full Validation**: Run complete data quality checks
2. **Performance Testing**: Test Athena query performance
3. **Cost Analysis**: Review S3 and Glue costs
4. **Documentation**: Update migration status and notes
5. **Archive Source**: Keep Teradata tables until validation complete
6. **Train Users**: Help users query data in Athena/S3

### Ongoing Maintenance

1. **Regular Backups**: Back up configuration files
2. **Dependency Updates**: Keep Python packages current
3. **Cost Optimization**: Review S3 storage classes and lifecycle
4. **Access Audit**: Review IAM roles and S3 bucket policies
5. **Documentation**: Keep runbooks updated

### Troubleshooting Workflow

```
1. Check logs
   └─ tail -f logs/migration.log

2. Identify error type
   └─ Connection, Data, AWS, Resource?

3. Verify prerequisites
   └─ Can connect to source/target?

4. Check configuration
   └─ Correct host, credentials, bucket names?

5. Test components individually
   └─ Teradata connection, S3 upload, etc.

6. Review recent changes
   └─ New configuration, code updates?

7. Consult troubleshooting guide above
   └─ Search for similar issues

8. Escalate if needed
   └─ Check AWS/Teradata documentation
```
