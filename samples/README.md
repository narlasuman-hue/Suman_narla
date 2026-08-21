# Sample Data and Configuration

This directory contains sample data, configuration files, and examples for the Teradata to AWS migration system.

## Contents

### Configuration Files

#### `sample_config.yaml`
A realistic migration configuration file with multiple tables at different priorities.

**Features**:
- Complete Teradata connection settings
- AWS S3 and Glue configuration
- Multiple table definitions with metadata
- Priority levels for migration scheduling
- Estimated row counts for capacity planning

**Use Cases**:
- Template for creating your production configuration
- Learning about configuration options
- Testing different table combinations

**How to Use**:
```bash
# Copy to your config directory
cp samples/sample_config.yaml config/migration_config.local.yaml

# Edit with your actual connection details
nano config/migration_config.local.yaml

# Test the configuration
python -m migration status --config config/migration_config.local.yaml
```

**Tables Included**:
- **OLTP Tables**: sales.customers, sales.orders, sales.order_items
- **Financial Data**: finance.invoices, finance.payments
- **Reference Data**: reference.products, reference.warehouses, reference.currencies
- **Analytics**: analytics.daily_sales_summary, analytics.customer_metrics
- **Archive**: archive.old_transactions (disabled)

---

### Sample Data Files

#### `sample_data_customers.csv`
Sample customer records in CSV format (10 rows).

**Fields**:
- customer_id, customer_name, email, phone
- country, city, state, postal_code
- created_date, updated_date, account_status
- credit_limit, total_purchases

**Use Cases**:
- Understanding the Teradata table structure
- Testing extraction with small datasets
- Learning data types and formats

**Sample Queries**:
```bash
# View the data
cat samples/sample_data_customers.csv

# Parse with Python
python << 'EOF'
import csv
with open('samples/sample_data_customers.csv') as f:
    reader = csv.DictReader(f)
    for row in reader:
        print(f"{row['customer_id']}: {row['customer_name']}")
EOF

# Convert to JSON
python << 'EOF'
import csv
import json
with open('samples/sample_data_customers.csv') as f:
    reader = csv.DictReader(f)
    data = list(reader)
    print(json.dumps(data, indent=2))
EOF
```

---

#### `sample_data_orders.csv`
Sample order records in CSV format (15 rows).

**Fields**:
- order_id, customer_id, order_date, delivery_date
- order_amount, tax_amount, total_amount
- order_status, payment_method
- shipping_address, notes

**Features**:
- Various order statuses (DELIVERED, IN_TRANSIT, PENDING)
- NULL values (realistic data)
- Multiple payment methods
- Date ranges for partitioning examples

**Use Cases**:
- Testing extraction with date-partitioned tables
- Handling NULL values
- Testing various data types

---

#### `sample_orders_with_nulls.json`
Sample order data in JSON format (5 rows with NULL handling).

**Features**:
- JSON format with null values
- Documents how NULL is represented in JSON
- Good for testing JSON extraction format

**Use Cases**:
- Testing JSON extraction format
- Understanding NULL handling
- API integration examples

**Example**:
```bash
# Parse JSON
python << 'EOF'
import json
with open('samples/sample_orders_with_nulls.json') as f:
    orders = json.load(f)
    for order in orders:
        print(f"Order {order['order_id']}: {order['order_status']} "
              f"(Delivered: {order['delivery_date']})")
EOF
```

---

### Metadata and Reports

#### `sample_extraction_metadata.json`
Complete extraction metadata from a successful migration.

**Contains**:
- Extraction timestamp and duration
- Batch-level details (row counts, file sizes, checksums)
- Schema definition for all columns
- Column statistics (min, max, null counts, distinct values)
- Data quality metrics
- Validation results

**Use Cases**:
- Understanding extraction metadata structure
- Learning about batch organization
- Understanding quality metrics
- Estimating extraction time for similar tables

**Key Sections**:
```json
{
  "table_name": "sales.customers",
  "extraction_timestamp": "2024-08-20T10:30:45.123456Z",
  "total_rows": 125000,
  "total_batches": 3,
  "schema": {...},
  "column_statistics": {...},
  "validation_results": {...}
}
```

**Usage Example**:
```bash
# Parse metadata
python << 'EOF'
import json
with open('samples/sample_extraction_metadata.json') as f:
    metadata = json.load(f)
    print(f"Table: {metadata['table_name']}")
    print(f"Rows: {metadata['total_rows']:,}")
    print(f"Batches: {metadata['total_batches']}")
    print(f"Duration: {metadata['extraction_duration_seconds']} seconds")
    print(f"Throughput: {metadata['rows_per_second']} rows/sec")
EOF
```

---

#### `migration_status_report.txt`
A comprehensive migration status report showing real-world progress.

**Sections**:
- **Summary**: Overall migration progress
- **Completed Tables**: Finished extractions with timing and validation
- **In Progress**: Currently extracting tables with ETA
- **Pending Tables**: Scheduled extractions
- **Disabled Tables**: Tables not being migrated
- **Metrics & Statistics**: Performance data
- **Issues & Resolutions**: Problems encountered and solutions
- **Next Actions**: Tasks for next 24 hours
- **Risks & Mitigations**: Identified risks and mitigation strategies

**Use Cases**:
- Understanding what a migration project looks like in practice
- Learning performance benchmarks
- Understanding risk management
- Reporting to stakeholders

**Key Metrics Shown**:
- Extraction throughput: 517 rows/sec average
- Data quality score: 99.8%
- Estimated weekly costs: $29.50
- Progress: 15% complete

---

## Using the Samples

### Quick Start with Sample Data

1. **Set up environment**:
```bash
# Copy sample configuration
cp samples/sample_config.yaml config/migration_config.local.yaml

# Update connection details
nano config/migration_config.local.yaml
```

2. **Review sample data**:
```bash
# View customers
cat samples/sample_data_customers.csv | head -5

# View orders
cat samples/sample_data_orders.csv | head -5

# View metadata
cat samples/sample_extraction_metadata.json | jq
```

3. **Understand extraction metadata**:
```bash
# Parse metadata
python << 'EOF'
import json
with open('samples/sample_extraction_metadata.json') as f:
    meta = json.load(f)
    print(f"Table: {meta['table_name']}")
    print(f"Rows: {meta['total_rows']:,}")
    for batch in meta['batch_details']:
        print(f"  Batch {batch['batch_number']}: "
              f"{batch['row_count']:,} rows, {batch['file_size_bytes']} bytes")
EOF
```

### Testing Extract, Transform, Load

Use the sample data to practice ETL operations:

```python
# Load sample data
import pandas as pd

# Read CSV
customers = pd.read_csv('samples/sample_data_customers.csv')
orders = pd.read_csv('samples/sample_data_orders.csv')

# Simple transformation
customers['total_purchases'] = customers['total_purchases'].fillna(0)
orders['shipping_address'] = orders['shipping_address'].fillna('Unknown')

# Analysis
print(f"Total customers: {len(customers)}")
print(f"Average credit limit: ${customers['credit_limit'].mean():,.2f}")
print(f"Total order value: ${orders['total_amount'].sum():,.2f}")
```

### Creating Custom Sample Data

To create sample data for your own tables:

1. **Start with CSV format**:
```csv
id,name,amount,date
1,Sample 1,1000.00,2024-01-01
2,Sample 2,2000.00,2024-01-02
```

2. **Convert to JSON**:
```bash
python << 'EOF'
import csv, json
with open('my_data.csv') as f:
    data = list(csv.DictReader(f))
    json.dump(data, open('my_data.json', 'w'), indent=2)
EOF
```

3. **Generate metadata**:
```python
import json
import pandas as pd

df = pd.read_csv('my_data.csv')

metadata = {
    "table_name": "schema.table_name",
    "total_rows": len(df),
    "schema": {col: str(df[col].dtype) for col in df.columns},
    "column_statistics": {
        col: {
            "null_count": df[col].isnull().sum(),
            "distinct_values": df[col].nunique()
        }
        for col in df.columns
    }
}

json.dump(metadata, open('my_metadata.json', 'w'), indent=2)
```

---

## File Sizes and Performance

| File | Size | Rows | Format | Use |
|------|------|------|--------|-----|
| sample_data_customers.csv | 1 KB | 10 | CSV | Learning |
| sample_data_orders.csv | 2 KB | 15 | CSV | Learning |
| sample_orders_with_nulls.json | 2 KB | 5 | JSON | Testing NULLs |
| sample_extraction_metadata.json | 8 KB | - | JSON | Metadata format |
| sample_config.yaml | 3 KB | - | YAML | Configuration |
| migration_status_report.txt | 12 KB | - | TXT | Reporting |

---

## Data Schemas Reference

### sales.customers
```
customer_id: INTEGER (PK)
customer_name: VARCHAR(255)
email: VARCHAR(255)
phone: VARCHAR(20)
country: VARCHAR(50)
city: VARCHAR(50)
state: VARCHAR(5)
postal_code: VARCHAR(20)
created_date: DATE
updated_date: DATE
account_status: VARCHAR(20) {ACTIVE, SUSPENDED, INACTIVE, PENDING}
credit_limit: DECIMAL(15,2)
total_purchases: DECIMAL(15,2)
```

### sales.orders
```
order_id: INTEGER (PK)
customer_id: INTEGER (FK)
order_date: DATE
delivery_date: DATE (nullable)
order_amount: DECIMAL(15,2)
tax_amount: DECIMAL(15,2)
total_amount: DECIMAL(15,2)
order_status: VARCHAR(20) {DELIVERED, IN_TRANSIT, PENDING}
payment_method: VARCHAR(20) {WIRE_TRANSFER, CREDIT_CARD, BANK_TRANSFER}
shipping_address: VARCHAR(255)
notes: TEXT (nullable)
```

---

## Common Workflows

### Workflow 1: Load and Analyze Sample Data

```python
import pandas as pd
import json

# Load all samples
customers = pd.read_csv('samples/sample_data_customers.csv')
orders = pd.read_csv('samples/sample_data_orders.csv')
metadata = json.load(open('samples/sample_extraction_metadata.json'))

# Analyze
print(f"Customers: {len(customers)}")
print(f"Orders: {len(orders)}")
print(f"Extracted rows: {metadata['total_rows']:,}")

# Join
merged = orders.merge(customers, on='customer_id', how='left')
print(f"Merged records: {len(merged)}")
```

### Workflow 2: Test Configuration

```bash
# Copy configuration
cp samples/sample_config.yaml config/test_config.yaml

# Modify table names to match your Teradata
sed -i 's/sales\.customers/your_schema.your_table/g' config/test_config.yaml

# Test (dry run)
python -m migration status --config config/test_config.yaml
```

### Workflow 3: Understanding Extraction Flow

1. Read `sample_extraction_metadata.json` to understand structure
2. Review `sample_config.yaml` for table configuration
3. Look at CSV files to understand data types
4. Read migration status report to see real progress

---

## Next Steps

1. **Review Documentation**: Read docs/MIGRATION_GUIDE.md
2. **Adapt Configuration**: Copy sample_config.yaml and update for your tables
3. **Test Connection**: Use migration status command
4. **Start Small**: Begin with reference tables before large OLTP tables
5. **Monitor Progress**: Track with migration status reports

---

## Support

For questions about the sample data:
- See docs/API_REFERENCE.md for configuration options
- See docs/OPERATIONS.md for deployment steps
- See docs/ARCHITECTURE.md for understanding data flow
