# Data Lineage & Impact Analysis Guide

## Overview

The Database Metadata Catalog provides comprehensive data lineage tracking and impact analysis capabilities. Understand data flows, dependencies, and the impact of changes across your Teradata environment.

## Data Lineage

### What is Data Lineage?

Data lineage tracks the flow of data through your systems:
- **Upstream lineage** (sources) - Where data comes from
- **Downstream lineage** (targets) - Where data goes

Example:
```
source_table → transformation_job → target_table
                      ↓
              dependent_analytics_table
```

## Lineage Extraction

### Automatic Lineage Detection

Lineage is automatically extracted from:
1. **SQL Queries** - INSERT, UPDATE, CREATE statements
2. **Job Definitions** - ETL/transformation jobs
3. **Query Logs** - Teradata query execution logs

### Manual Lineage Creation

Create lineage from SQL queries:

```bash
# Via API
curl -X POST "http://localhost:8000/api/v1/lineage/create-from-sql" \
  -H "Content-Type: application/json" \
  -d '{"sql": "INSERT INTO target_table SELECT * FROM source_table"}'

# Via CLI (planned for future release)
python -m src.cli lineage extract-from-sql "INSERT INTO..."
```

### Supported Query Types

- **SELECT** - Read operations (sources)
- **INSERT** - Write to table (target)
- **UPDATE** - Modify table (target + sources)
- **CREATE TABLE** - New table creation (target)
- **CREATE VIEW** - View definition (target)
- **DELETE** - Delete from table (target)

## API: Viewing Lineage

### Get Upstream Lineage (Sources)

Find all tables feeding into a specific table:

```bash
curl "http://localhost:8000/api/v1/lineage/{table_id}/upstream?max_depth=5"
```

**Response:**
```json
{
  "table_id": 42,
  "table_name": "analytics_table",
  "database": "analytics_db",
  "upstream": {
    "42": [
      {
        "source_id": 10,
        "source_name": "raw_events",
        "source_db": "raw_data",
        "lineage_id": 1,
        "job_id": 5
      }
    ]
  },
  "depth": 5
}
```

### Get Downstream Lineage (Targets)

Find all tables that depend on a specific table:

```bash
curl "http://localhost:8000/api/v1/lineage/{table_id}/downstream?max_depth=5"
```

### Get Full Lineage Graph

Get complete upstream and downstream in one call:

```bash
curl "http://localhost:8000/api/v1/lineage/{table_id}/full?max_depth=3"
```

## Impact Analysis

### What Breaks If I Change This?

When considering changes to a table, understand the impact:

```bash
curl "http://localhost:8000/api/v1/impact/{table_id}"
```

**Response:**
```json
{
  "source_table": {
    "id": 10,
    "name": "raw_events",
    "database": "raw_data"
  },
  "impacted_count": 5,
  "impacted_tables": [
    {
      "id": 42,
      "name": "analytics_table",
      "database": "analytics_db",
      "type": "PERMANENT",
      "size_mb": 1024,
      "row_count": 10000000
    }
  ]
}
```

### Get Table Dependencies

Find all tables a table depends on:

```bash
curl "http://localhost:8000/api/v1/dependencies/{table_id}"
```

Returns all upstream tables (direct and transitive).

### Check Drop Safety

Before dropping a table, verify it's safe:

```bash
curl "http://localhost:8000/api/v1/drop-safety/{table_id}"
```

**Safe to Drop:**
```json
{
  "table": {
    "id": 10,
    "name": "raw_events",
    "database": "raw_data"
  },
  "can_safely_drop": true,
  "impacted_count": 0,
  "impacted_tables": [],
  "reason": "Safe to drop - no downstream dependencies"
}
```

**Not Safe:**
```json
{
  "table": {
    "id": 10,
    "name": "raw_events",
    "database": "raw_data"
  },
  "can_safely_drop": false,
  "impacted_count": 5,
  "impacted_tables": [
    {
      "id": 42,
      "name": "analytics_table",
      ...
    }
  ],
  "reason": "5 tables depend on this table"
}
```

## SQL Lineage Extraction

### Extract From SQL Query

Parse SQL to identify sources and targets:

```bash
curl -X POST "http://localhost:8000/api/v1/lineage/extract-from-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO target_table SELECT * FROM source_table WHERE date > 2024-01-01"
  }'
```

**Response:**
```json
{
  "query_type": "INSERT",
  "sources": [
    {
      "database": "source_db",
      "table": "source_table",
      "found_in_catalog": true,
      "table_id": 10
    }
  ],
  "targets": [
    {
      "database": "target_db",
      "table": "target_table",
      "found_in_catalog": true,
      "table_id": 42
    }
  ]
}
```

### Create Lineage From SQL

Register extracted lineage in the catalog:

```bash
curl -X POST "http://localhost:8000/api/v1/lineage/create-from-sql" \
  -H "Content-Type: application/json" \
  -d '{
    "sql": "INSERT INTO target_table SELECT * FROM source_table",
    "job_id": 5
  }'
```

## Query Log Analysis

### Parse Query Logs

Extract lineage from actual query executions:

```bash
curl -X POST "http://localhost:8000/api/v1/analysis/parse-logs?hours=24"
```

Updates lineage based on real Teradata query activity.

### Get Query Patterns

Understand how a table is used:

```bash
curl "http://localhost:8000/api/v1/analysis/table/{table_id}/patterns?hours=24"
```

**Response:**
```json
{
  "table_id": 42,
  "table_name": "analytics_table",
  "queries_total": 150,
  "query_types": {
    "SELECT": 145,
    "UPDATE": 5
  },
  "top_users": {
    "analyst_john": 75,
    "analyst_jane": 50,
    "admin_team": 25
  },
  "query_times": [
    {
      "start": "2024-08-24T10:00:00",
      "duration_seconds": 2.5
    }
  ]
}
```

### Identify Heavy Users

Find who uses Teradata most:

```bash
curl "http://localhost:8000/api/v1/analysis/heavy-users"
```

### Query Performance

Get performance metrics for table queries:

```bash
curl "http://localhost:8000/api/v1/analysis/table/{table_id}/performance?limit=20"
```

## Lineage Use Cases

### 1. Data Quality Issues

When data quality drops, trace the source:

1. **Find upstream** lineage of affected table
2. **Check sources** for data quality issues
3. **Analyze dependencies** in quality score

```bash
# Find upstream sources
curl "http://localhost:8000/api/v1/lineage/{affected_table_id}/upstream"

# Get source data quality
curl "http://localhost:8000/api/v1/reports/data-quality-score"
```

### 2. Impact Assessment

Before modifying critical tables:

1. **Check impact** - what tables depend on it?
2. **Identify downstream** stakeholders
3. **Assess risk** - how many tables would be affected?

```bash
curl "http://localhost:8000/api/v1/impact/{table_id}"
```

### 3. Data Migration

Understand data flow before migration:

1. **Get full lineage** - source to target
2. **Identify intermediate** transformations
3. **Plan cutover** - when to switch

```bash
curl "http://localhost:8000/api/v1/lineage/{table_id}/full?max_depth=10"
```

### 4. Decommissioning

Before retiring a table:

1. **Check drop safety** - are other tables dependent?
2. **Notify stakeholders** - who will be affected?
3. **Plan cutover** - when and how to migrate?

```bash
curl "http://localhost:8000/api/v1/drop-safety/{table_id}"
```

### 5. Cost Optimization

Find redundant or unused tables:

1. **Get usage metrics** - when was it last accessed?
2. **Check downstream** - who depends on it?
3. **Decide** - optimize, consolidate, or retire?

```bash
curl "http://localhost:8000/api/v1/lifecycle/unused-assets?days=180"
curl "http://localhost:8000/api/v1/impact/{table_id}"
```

## Visualization

### Lineage Graphs

The API returns data suitable for graph visualization:

```json
{
  "upstream": {
    "table_id": [
      { "source_id": 10, "source_name": "source1" },
      { "source_id": 20, "source_name": "source2" }
    ]
  }
}
```

Frontend libraries for visualization:
- **Cytoscape.js** - Interactive graphs
- **D3.js** - Custom visualizations
- **vis.js** - Network diagrams
- **Graphviz** - Static diagrams

Example rendering (pseudo-code):
```javascript
// Parse API response
const lineage = await fetch('/api/v1/lineage/42/full').then(r => r.json());

// Create graph nodes and edges
const nodes = extractNodes(lineage);
const edges = extractEdges(lineage);

// Render with Cytoscape
const cy = cytoscape({
  container: document.getElementById('cy'),
  elements: [...nodes, ...edges],
  style: cytoscape.stylesheet()
});
```

## Best Practices

### 1. Keep Lineage Updated

- Enable automatic query log parsing
- Manually register complex lineage from jobs
- Review lineage monthly for accuracy

### 2. Document Non-SQL Lineage

For ETL tools, spreadsheets, or manual processes:
- Create lineage records manually via API
- Use job_id to link to ETL jobs
- Add descriptions for context

### 3. Monitor Lineage Changes

Watch for:
- New dependencies appearing
- Data sources changing
- Unused tables accumulating

### 4. Plan Changes with Lineage

Always check impact before:
- Dropping tables
- Changing table schemas
- Redirecting data flows
- Retiring data sources

## Troubleshooting

### "Table not found in lineage"

- Ensure table exists in catalog
- Run metadata sync: `python -m src.cli sync`
- Check table name spelling and database

### "No lineage data available"

- Query logs not parsed recently
- Enable scheduled query log analysis
- Manually create lineage if needed

### "Impact analysis incomplete"

- Run query log parser: POST `/analysis/parse-logs`
- Wait for automatic scheduled sync
- Manually add missing lineage

## Limitations

- Lineage requires table to exist in catalog
- Complex SQL (subqueries, CTEs) may not extract fully
- Lineage is graph-like; circular references possible
- Performance degrades with very deep lineage (10+ levels)

## Future Enhancements

Planned for upcoming releases:
- [ ] Lineage visualization dashboard
- [ ] Lineage diff tracking (changes over time)
- [ ] Subquery and CTE support
- [ ] Lineage export (Mermaid, Graphviz)
- [ ] Column-level lineage
- [ ] Lineage versioning/history
