# Testing Guide

Complete guide for testing the Database Metadata Catalog application with sample data.

## Quick Start with Sample Data

### 1. Load Sample Data

**On Linux/Mac:**
```bash
chmod +x scripts/load_sample_data.sh
./scripts/load_sample_data.sh
```

**On Windows:**
```bash
scripts\load_sample_data.bat
```

**Or manually:**
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Load sample data
python -m src.sample_data
```

### 2. Start Backend
```bash
python main.py
# API available at http://localhost:8000
# Docs available at http://localhost:8000/docs
```

### 3. Start Frontend
```bash
cd frontend
npm install  # Only needed once
npm start
# Frontend available at http://localhost:3000
```

---

## Sample Data Overview

The sample data loader creates a realistic multi-database environment for testing.

### Databases
| Name | Owner | Status | Tables | Purpose |
|------|-------|--------|--------|---------|
| `analytics_db` | analytics_team | ACTIVE | 3 | Analytics and reporting |
| `raw_data` | data_engineering | ACTIVE | 2 | Raw data ingestion |
| `customer_db` | customer_team | ACTIVE | 2 | Customer data and CRM |
| `legacy_warehouse` | legacy_team | DEPRECATED | 1 | Legacy (deprecated) |

### Tables

#### analytics_db
1. **customers_table**
   - 7 columns (customer_id, first_name, last_name, email, phone, created_at, last_login)
   - 5M rows, 2GB size
   - Status: ACTIVE
   - PII data (email, phone marked as sensitive)
   - Last accessed: 2 hours ago

2. **orders_table**
   - 6 columns (order_id, customer_id, order_date, total_amount, status, created_at)
   - 50M rows, 15GB size
   - Status: ACTIVE
   - Last accessed: 1 hour ago
   - Critical tier table

3. **analytics_summary**
   - 5 columns (metric_date, total_orders, total_revenue, unique_customers, avg_order_value)
   - 1K rows, 256MB size
   - Status: ACTIVE
   - Last accessed: 30 minutes ago

#### raw_data
1. **raw_events**
   - 6 columns (event_id, event_type, user_id, event_data, timestamp, processed)
   - 100M rows, 40GB size
   - Status: ACTIVE
   - Last accessed: 5 minutes ago
   - High tier

2. **staging_orders**
   - 5 columns (staging_id, order_id, customer_id, amount, status)
   - 5M rows, 2GB size
   - Status: ACTIVE
   - Temporary table for ETL
   - Last accessed: 6 hours ago

#### customer_db
1. **customer_profiles**
   - 5 columns (profile_id, customer_id, tier, lifetime_value, last_update)
   - 10M rows, 4GB size
   - Status: ACTIVE
   - PII data (email marked as sensitive)
   - Last accessed: 4 hours ago

2. **customer_transactions** (ARCHIVED)
   - 5 columns (txn_id, customer_id, amount, date, status)
   - 30M rows, 12GB size
   - Status: INACTIVE
   - Last accessed: 180 days ago

#### legacy_warehouse
1. **old_customer_data**
   - 4 columns (customer_id, cust_name, cust_email, create_date)
   - 2M rows, 1GB size
   - Status: DEPRECATED
   - Last accessed: 360 days ago
   - Tagged as legacy

### Jobs (4 Total)
1. **daily_analytics_sync**
   - Frequency: DAILY at 2 AM
   - Status: ACTIVE
   - Last execution: SUCCESS (22 hours ago)
   - Rows processed: 50M

2. **customer_segment_update**
   - Frequency: DAILY at 3 AM
   - Status: ACTIVE
   - Owner: analytics_team

3. **data_quality_check**
   - Frequency: HOURLY
   - Status: ACTIVE
   - Last execution: SUCCESS (3 hours ago)

4. **legacy_data_archival**
   - Frequency: WEEKLY (Sunday 1 AM)
   - Status: INACTIVE
   - Last execution: FAILED (1 hour ago)

### Lineage Relationships (4 Total)
1. raw_events → analytics_summary (via daily_analytics_sync job)
2. orders_table → analytics_summary (input)
3. customers_table → customer_summary_view (input)
4. staging_orders → orders_table (transformation via customer_segment_update job)

### Asset Tags
- **Critical tier**: customers_table, orders_table
- **PII**: customers_table, customer_profiles
- **Reporting**: orders_table, analytics_summary
- **Raw data**: raw_events
- **Deprecated**: old_customer_data
- **Legacy**: old_customer_data

---

## Testing Scenarios

### 1. Dashboard Testing
**Path:** http://localhost:3000

**What to verify:**
- [ ] Statistics cards show correct counts
  - Databases: 4
  - Tables: 8
  - Columns: 48
  - Active Assets: 7
- [ ] Recent databases list shows all 4 databases
- [ ] Recent tables shows multiple tables
- [ ] Lifecycle status shows deprecated and decommissioned counts
- [ ] All quick action links are clickable

### 2. Search Functionality
**Path:** http://localhost:3000/search

**Test cases:**
1. **Search for table names**
   - Query: "customer" → Should find customer_table, customer_profiles, customer_transactions
   - Query: "orders" → Should find orders_table
   - Query: "analytics" → Should find analytics_summary

2. **Search for columns**
   - Filter by "Columns"
   - Query: "email" → Should find 2 results (customer email fields)
   - Query: "date" → Should find order_date, create_date, metric_date

3. **Autocomplete suggestions**
   - Type "cus" → Should suggest customer-related tables
   - Type "ord" → Should suggest order-related tables

4. **Results filtering**
   - Toggle asset type filters
   - Verify result counts update

### 3. Asset Details
**Path:** http://localhost:3000/tables/[id]

**Test cases:**
1. **customers_table details**
   - Verify 7 columns displayed
   - Check PII flags on email and phone columns
   - Verify row count: 5,000,000
   - Verify status: ACTIVE
   - Check recent access time

2. **orders_table details**
   - Verify 6 columns
   - Check row count: 50,000,000
   - Verify size: 15360 MB

3. **old_customer_data details** (deprecated table)
   - Verify status: DEPRECATED
   - Check last accessed: 360+ days ago

### 4. Lineage Visualization
**Path:** http://localhost:3000/lineage/[id]

**Test cases:**
1. **analytics_summary lineage**
   - Upstream: Should show orders_table and raw_events
   - Downstream: Should show dependent tables/views
   - Full view: Should show complete graph

2. **orders_table lineage**
   - Upstream: Should show staging_orders
   - Downstream: Should show analytics_summary

3. **customer_transactions lineage**
   - Should show relationships to analytics

### 5. Reports & Analytics
**Path:** http://localhost:3000/reports

**Test cases:**
1. **Summary Statistics**
   - Verify counts match dashboard
   - Databases: 4
   - Tables: 8
   - Columns: 48+

2. **Storage Usage**
   - Should show pie chart of storage by database
   - raw_data should be largest (40GB)

3. **Data Quality Score**
   - Should display quality metrics
   - Show progress bars for different dimensions

4. **Most Used Tables**
   - Bar chart showing query counts
   - raw_events and orders_table should be top users

### 6. Lifecycle Management
**Path:** http://localhost:3000/lifecycle

**Test cases:**
1. **Status Overview**
   - Active: 7 tables
   - Deprecated: 1 table
   - Inactive: 1 table

2. **Unused Assets Tab**
   - Should show customer_transactions (inactive 180+ days)
   - Click to view details

3. **Decommissioning Candidates**
   - Should show old_customer_data (deprecated, 360+ days unused)
   - Review for decommissioning

### 7. Query Analysis
**Path:** http://localhost:3000/analysis

**Test cases:**
1. **Heavy Users**
   - Should display job execution information
   - Show top data consumers

2. **Query Patterns**
   - Should display query statistics
   - Show query type distribution (SELECT, INSERT, etc.)

---

## API Endpoint Testing

### Using curl

#### 1. Health Checks
```bash
# Basic health
curl http://localhost:8000/health
# Expected: {"status": "healthy"}

# Database health
curl http://localhost:8000/health/db
# Expected: {"status": "healthy", "database": "connected"}
```

#### 2. Databases
```bash
# List all databases
curl http://localhost:8000/api/v1/databases
# Expected: Array of 4 databases

# Get specific database
curl http://localhost:8000/api/v1/databases/1
# Expected: Database details
```

#### 3. Tables
```bash
# List all tables
curl http://localhost:8000/api/v1/tables
# Expected: Array of 8 tables

# Get table details
curl http://localhost:8000/api/v1/tables/1

# Get table columns
curl http://localhost:8000/api/v1/tables/1/columns
# Expected: 7 columns for customers_table
```

#### 4. Search
```bash
# Global search
curl "http://localhost:8000/api/v1/search?q=customer&limit=50"

# Search tables
curl "http://localhost:8000/api/v1/search/tables?q=customer"

# Search columns
curl "http://localhost:8000/api/v1/search/columns?q=email"

# Autocomplete
curl "http://localhost:8000/api/v1/search/autocomplete?q=cus&asset_type=table"
```

#### 5. Lineage
```bash
# Get full lineage
curl http://localhost:8000/api/v1/lineage/3/full

# Get upstream lineage
curl http://localhost:8000/api/v1/lineage/3/upstream

# Get downstream lineage
curl http://localhost:8000/api/v1/lineage/3/downstream
```

#### 6. Lifecycle
```bash
# Get lifecycle summary
curl http://localhost:8000/api/v1/lifecycle/summary

# Get unused assets
curl "http://localhost:8000/api/v1/lifecycle/unused-assets?days=90"

# Get decommissioning candidates
curl "http://localhost:8000/api/v1/lifecycle/decommissioning-candidates?days=180"
```

#### 7. Reports
```bash
# Summary report
curl http://localhost:8000/api/v1/reports/summary

# Storage usage
curl http://localhost:8000/api/v1/reports/storage-usage

# Most used tables
curl "http://localhost:8000/api/v1/reports/most-used-tables?limit=10&period=30d"

# Data quality score
curl http://localhost:8000/api/v1/reports/data-quality-score
```

### Using Interactive API Docs
1. Open http://localhost:8000/docs (Swagger UI)
2. Try out endpoints directly from the browser
3. See request/response examples

---

## Testing with Backend Only (No Frontend)

### Using Postman
1. Import endpoints from http://localhost:8000/docs
2. Set up collection with environment variables
3. Test API workflows

### Using curl scripts
Create a test script `test_api.sh`:

```bash
#!/bin/bash

BASE_URL="http://localhost:8000/api/v1"

echo "Testing API Endpoints..."
echo ""

# Test 1: Health
echo "1. Health Check:"
curl -s $BASE_URL/../health | jq .
echo ""

# Test 2: Databases
echo "2. List Databases:"
curl -s $BASE_URL/databases | jq '.[] | {id, name, owner}'
echo ""

# Test 3: Tables
echo "3. List Tables:"
curl -s $BASE_URL/tables | jq '.[] | {id, name, database_id, row_count, size_mb}'
echo ""

# Test 4: Search
echo "4. Search for 'customer':"
curl -s "$BASE_URL/search?q=customer" | jq .
echo ""

# Test 5: Lineage
echo "5. Lineage for table 3:"
curl -s $BASE_URL/lineage/3/full | jq .
echo ""

echo "All tests completed!"
```

Run with: `bash test_api.sh`

---

## Performance Testing

### Load Testing Sample Data
```bash
# Measure data loading time
time python -m src.sample_data

# Expected: < 5 seconds for 8 tables, 48 columns, 4 jobs
```

### API Response Times
```bash
# Test search performance
time curl "http://localhost:8000/api/v1/search?q=customer&limit=100"

# Test list performance
time curl "http://localhost:8000/api/v1/tables?skip=0&limit=100"

# Test lineage performance
time curl "http://localhost:8000/api/v1/lineage/3/full"
```

---

## Troubleshooting

### Sample Data Not Appearing
1. Verify database connection: `curl http://localhost:8000/health/db`
2. Check .env configuration
3. Reinitialize database and reload sample data
4. Check database logs

### Frontend Not Loading Data
1. Verify backend is running: `curl http://localhost:8000/health`
2. Check browser console for errors (F12)
3. Check `REACT_APP_API_BASE_URL` in frontend/.env
4. Check network tab in DevTools for API calls

### Missing Columns or Data
1. Verify sample data loaded completely (check terminal output)
2. Refresh browser (Ctrl+Shift+R or Cmd+Shift+R)
3. Check if API returns data with curl
4. Reinitialize database and reload sample data

---

## Test Data Statistics

| Entity | Count | Notes |
|--------|-------|-------|
| Databases | 4 | 1 deprecated, 3 active |
| Tables | 8 | Mix of active, inactive, deprecated |
| Columns | 48 | Various data types, some marked sensitive |
| Views | 2 | Both in analytics_db |
| Jobs | 4 | 3 active, 1 inactive |
| Job Executions | 4 | Mix of success and failure |
| Lineage Relationships | 4 | Show data flow through system |
| Asset Tags | 10 | Classification across multiple tables |
| Total Rows (approx) | 203M | Realistic dataset size |
| Total Size (approx) | 74GB | Realistic storage usage |

---

## Next Steps After Testing

### If Testing Locally Without Teradata
- Sample data is sufficient for UI and API testing
- Use sample data to verify all features work
- No need to configure Teradata connection

### If Connecting to Real Teradata
1. Configure TERADATA_* variables in .env
2. Run manual sync: `python -m src.cli sync`
3. Data will populate from actual database

### For Production Testing
- Use subset of production data
- Mask sensitive information
- Test with realistic data volumes
- Load test with concurrent users

---

## Quick Reference

| Action | Command |
|--------|---------|
| Load sample data | `./scripts/load_sample_data.sh` (Linux/Mac) or `scripts\load_sample_data.bat` (Windows) |
| Reset data | Delete database and reload sample data |
| Start backend | `python main.py` |
| Start frontend | `cd frontend && npm start` |
| View API docs | `http://localhost:8000/docs` |
| View frontend | `http://localhost:3000` |
| Test API | `bash test_api.sh` (with curl) |
| Check health | `curl http://localhost:8000/health` |
