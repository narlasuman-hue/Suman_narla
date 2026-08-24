# Search & Discovery Guide

## Overview

The Database Metadata Catalog provides comprehensive search and discovery capabilities across all metadata assets. Find tables, columns, views, jobs, and tags with powerful search and filtering.

## Quick Start

### Basic Search

```bash
# Global search
curl "http://localhost:8000/api/v1/search?q=customer"

# Search specific type
curl "http://localhost:8000/api/v1/search/tables?q=customer"
curl "http://localhost:8000/api/v1/search/columns?q=email"
```

### Autocomplete

Get suggestions as you type:

```bash
curl "http://localhost:8000/api/v1/search/autocomplete?q=cust&asset_type=table"
```

Returns: `["customers_table", "customer_orders", "customer_details", ...]`

## Search Types

### 1. Table Search

Find tables by name or description:

```bash
curl "http://localhost:8000/api/v1/search/tables?q=customer&database_id=1&limit=50"
```

**Response:**
```json
[
  {
    "id": 42,
    "name": "customers_table",
    "database": "analytics_db",
    "type": "PERMANENT",
    "description": "Customer information including contact details",
    "created_at": "2024-01-01T00:00:00",
    "row_count": 5000000,
    "size_mb": 2048,
    "match_type": "table_name"
  }
]
```

**Query Parameters:**
- `q` (required): Search term
- `database_id`: Filter by database
- `limit`: Results per page (default: 50, max: 500)

### 2. Column Search

Find columns by name or description:

```bash
curl "http://localhost:8000/api/v1/search/columns?q=email&limit=50"
```

**Response:**
```json
[
  {
    "id": 101,
    "name": "email",
    "table_id": 42,
    "table_name": "customers_table",
    "database": "analytics_db",
    "data_type": "VARCHAR(255)",
    "description": "Customer email address",
    "sensitive": true,
    "match_type": "column_name"
  }
]
```

Find columns by table:

```bash
curl "http://localhost:8000/api/v1/search/columns?q=*&table_id=42"
```

### 3. View Search

Find views in catalog:

```bash
curl "http://localhost:8000/api/v1/search/views?q=customer_orders&database_id=1"
```

### 4. Job Search

Find jobs and schedules:

```bash
curl "http://localhost:8000/api/v1/search/jobs?q=customer_sync"
```

### 5. Tag Search

Find assets by tags:

```bash
curl "http://localhost:8000/api/v1/search/tags?q=critical"
```

**Response:**
```json
[
  {
    "asset_id": 42,
    "asset_type": "TABLE",
    "asset_name": "customers_table",
    "tag_key": "tier",
    "tag_value": "critical"
  }
]
```

## Global Search

Search everything at once:

```bash
curl "http://localhost:8000/api/v1/search?q=customer&asset_types=tables,columns,views&limit=100"
```

**Response:**
```json
{
  "query": "customer",
  "total_results": 45,
  "tables": [
    { "id": 42, "name": "customers_table", ... }
  ],
  "columns": [
    { "id": 101, "name": "customer_id", ... }
  ],
  "views": [
    { "id": 85, "name": "customer_orders_view", ... }
  ],
  "jobs": [
    { "id": 5, "name": "customer_sync_job", ... }
  ],
  "tags": [
    { "asset_id": 42, "tag_key": "tier", "tag_value": "critical" }
  ]
}
```

**Query Parameters:**
- `q`: Search query (required)
- `asset_types`: Comma-separated types (tables, columns, views, jobs, tags)
- `database_id`: Filter by database
- `limit`: Maximum total results

## Specialized Searches

### Find Sensitive Data

Locate all columns containing sensitive information:

```bash
curl "http://localhost:8000/api/v1/search/sensitive-data"
```

**Response:**
```json
[
  {
    "id": 101,
    "name": "email",
    "table_id": 42,
    "table_name": "customers_table",
    "database": "analytics_db",
    "data_type": "VARCHAR(255)",
    "description": "Customer email address"
  },
  {
    "id": 102,
    "name": "phone",
    "table_id": 42,
    "table_name": "customers_table",
    "database": "analytics_db",
    "data_type": "VARCHAR(20)",
    "description": "Customer phone number"
  }
]
```

Use case: Compliance audits, data governance, privacy reviews.

### Search by Owner

Find all assets owned by a person:

```bash
curl "http://localhost:8000/api/v1/search/by-owner?owner=john_doe"
```

**Response:**
```json
{
  "owner": "john_doe",
  "tables": [
    {
      "id": 42,
      "name": "customers_table",
      "database": "analytics_db",
      "type": "PERMANENT"
    }
  ],
  "jobs": [
    {
      "id": 5,
      "name": "customer_sync_job",
      "frequency": "DAILY"
    }
  ]
}
```

Use case: Find assets owned by departing employees, identify SPOF.

### Search by Data Type

Find all columns with specific data type:

```bash
curl "http://localhost:8000/api/v1/search/by-data-type?data_type=INTEGER"
```

**Response:**
```json
[
  {
    "id": 102,
    "name": "customer_id",
    "table_id": 42,
    "table_name": "customers_table",
    "database": "analytics_db",
    "data_type": "INTEGER",
    "position": 1
  }
]
```

Use case: Schema analysis, type casting issues, numeric precision.

### Autocomplete Suggestions

Get suggestions while typing:

```bash
curl "http://localhost:8000/api/v1/search/autocomplete?q=cus&asset_type=table"
```

**Response:**
```json
[
  "customers_table",
  "customer_orders",
  "customer_details",
  "customer_history"
]
```

**Asset Types:**
- `table` - Table names
- `column` - Column names
- `database` - Database names
- `job` - Job names

## Search Use Cases

### 1. Data Discovery

New analyst needs to understand available data:

```bash
# Find customer-related tables
curl "http://localhost:8000/api/v1/search?q=customer&asset_types=tables,columns,views&limit=50"

# Understand table structure
curl "http://localhost:8000/api/v1/tables/42"
curl "http://localhost:8000/api/v1/tables/42/columns"
```

### 2. Compliance & Governance

Audit data containing personal information:

```bash
# Find all PII columns
curl "http://localhost:8000/api/v1/search/sensitive-data"

# Find who owns these assets
curl "http://localhost:8000/api/v1/search/by-owner?owner=data_governance_team"
```

### 3. Impact Analysis

Before modifying a column, find all references:

```bash
# Find all tables using email column
curl "http://localhost:8000/api/v1/search/columns?q=email"

# Check lineage for each table
curl "http://localhost:8000/api/v1/lineage/42/full"
```

### 4. Schema Analysis

Find all numeric columns for auditing:

```bash
curl "http://localhost:8000/api/v1/search/by-data-type?data_type=DECIMAL"
```

### 5. Asset Lifecycle

Find all critical tables for decommissioning review:

```bash
curl "http://localhost:8000/api/v1/search/tags?q=critical"
```

### 6. Cost Optimization

Find duplicate or redundant tables:

```bash
# Search for similar names
curl "http://localhost:8000/api/v1/search/tables?q=customer"

# Check lineage - are they both needed?
curl "http://localhost:8000/api/v1/lineage/42/full"
curl "http://localhost:8000/api/v1/lineage/43/full"
```

## Advanced Techniques

### Search with Filtering

Combine search with filters:

```bash
# Find active tables named "customer"
curl "http://localhost:8000/api/v1/search/tables?q=customer" | jq '.[] | select(.status=="active")'

# Find sensitive columns in production tables
curl "http://localhost:8000/api/v1/search/sensitive-data" | jq '.[] | select(.table_name | contains("prod"))'
```

### Programmatic Search

Python example:

```python
import requests

# Global search
response = requests.get("http://localhost:8000/api/v1/search", params={
    "q": "customer",
    "asset_types": ["tables", "columns"],
    "limit": 100
})

results = response.json()
print(f"Found {results['total_results']} results")

# Tables
for table in results['tables']:
    print(f"Table: {table['name']} ({table['database']})")

# Columns
for column in results['columns']:
    print(f"Column: {column['name']} in {column['table_name']}")
```

JavaScript example:

```javascript
// Global search
async function search(query) {
  const response = await fetch(
    `/api/v1/search?q=${encodeURIComponent(query)}&limit=100`
  );
  const results = await response.json();
  
  return {
    tables: results.tables,
    columns: results.columns,
    views: results.views,
    total: results.total_results
  };
}

// Usage
search("customer").then(results => {
  console.log(`Found ${results.total} results`);
  results.tables.forEach(t => console.log(`Table: ${t.name}`));
});
```

## Search Performance

### Tips for Fast Searches

1. **Use specific queries** - "customer_id" faster than "id"
2. **Filter by type** - Search tables only if you need tables
3. **Filter by database** - Narrow scope to relevant DB
4. **Use limits** - Don't retrieve more results than needed

### Indexing

Search uses database indexes:
- Table names indexed
- Column names indexed
- Descriptions indexed
- Tags indexed

### Search Limits

- Maximum results per request: 500
- Autocomplete suggestions: 10
- Global search distributes limit across types

## Troubleshooting

### "No results found"

Check:
1. Spelling and case (search is case-insensitive)
2. Metadata is synced: `python -m src.cli sync`
3. Asset exists in catalog: `GET /api/v1/tables`

### "Sensitive data not showing"

Ensure columns are marked:
1. Check if `sensitive_flag=true` in database
2. Update column: `PATCH /api/v1/tables/{id}/columns/{col_id}`

### "Search is slow"

For large catalogs:
1. Use more specific search terms
2. Filter by database or type
3. Reduce limit parameter
4. Check database health

## Future Enhancements

Planned features:
- [ ] Full-text search with Elasticsearch
- [ ] Advanced query syntax (AND, OR, NOT)
- [ ] Faceted search (filter by multiple dimensions)
- [ ] Search history and saved searches
- [ ] Search analytics (popular searches)
- [ ] Custom search filters
- [ ] AI-powered semantic search

## API Reference

See [API.md](./API.md) for complete endpoint documentation:
- `GET /api/v1/search`
- `GET /api/v1/search/tables`
- `GET /api/v1/search/columns`
- `GET /api/v1/search/views`
- `GET /api/v1/search/jobs`
- `GET /api/v1/search/tags`
- `GET /api/v1/search/sensitive-data`
- `GET /api/v1/search/by-owner`
- `GET /api/v1/search/by-data-type`
- `GET /api/v1/search/autocomplete`
