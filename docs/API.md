# API Documentation

The Database Metadata Catalog provides a comprehensive REST API for querying and managing metadata.

## Base URL

```
http://localhost:8000/api/v1
```

## Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## Authentication

Currently, the API is open (no authentication required). Authentication will be added in a future release.

## Health Check Endpoints

### Basic Health Check

```http
GET /health
```

Returns application health status.

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-08-24T12:34:56.789Z",
  "app": "Database Metadata Catalog",
  "version": "0.1.0"
}
```

### Database Health Check

```http
GET /health/db
```

Returns database connection status.

**Response**:
```json
{
  "status": "healthy",
  "database": "connected",
  "timestamp": "2024-08-24T12:34:56.789Z"
}
```

## Database Management

### List Databases

```http
GET /api/v1/databases
```

**Query Parameters**:
- `status` (string): Filter by status (active, inactive, deprecated, decommissioned)
- `skip` (integer): Number of records to skip (default: 0)
- `limit` (integer): Maximum records to return (default: 50, max: 500)

**Response**:
```json
[
  {
    "id": 1,
    "name": "database_name",
    "owner": "owner_name",
    "description": "Database description",
    "status": "active",
    "created_at": "2024-01-01T00:00:00",
    "last_synced": "2024-08-24T12:34:56"
  }
]
```

### Get Database Details

```http
GET /api/v1/databases/{database_id}
```

**Response**:
```json
{
  "id": 1,
  "name": "database_name",
  "owner": "owner_name",
  "description": "Database description",
  "status": "active",
  "created_at": "2024-01-01T00:00:00",
  "last_synced": "2024-08-24T12:34:56",
  "table_count": 125,
  "view_count": 42
}
```

### Create Database

```http
POST /api/v1/databases
```

**Request Body**:
```json
{
  "name": "new_database",
  "owner": "owner_name",
  "description": "Database description"
}
```

**Response**: `201 Created`

## Table Management

### List Tables

```http
GET /api/v1/tables
```

**Query Parameters**:
- `database_id` (integer): Filter by database
- `status` (string): Filter by status
- `skip` (integer): Number of records to skip
- `limit` (integer): Maximum records to return

**Response**:
```json
[
  {
    "id": 1,
    "database_id": 1,
    "name": "table_name",
    "type": "PERMANENT",
    "status": "active",
    "created_at": "2024-01-01T00:00:00",
    "last_accessed": "2024-08-24T10:00:00",
    "row_count": 1000000,
    "size_mb": 512.5,
    "column_count": 25
  }
]
```

### Get Table Details

```http
GET /api/v1/tables/{table_id}
```

**Response**:
```json
{
  "id": 1,
  "database_id": 1,
  "name": "table_name",
  "type": "PERMANENT",
  "status": "active",
  "description": "Table description",
  "created_at": "2024-01-01T00:00:00",
  "last_accessed": "2024-08-24T10:00:00",
  "last_modified": "2024-08-24T09:00:00",
  "row_count": 1000000,
  "size_mb": 512.5,
  "column_count": 25,
  "columns": [
    {
      "id": 1,
      "name": "id",
      "data_type": "INTEGER",
      "nullable": false,
      "sensitive": false,
      "description": null,
      "position": 1
    }
  ]
}
```

### Get Table Columns

```http
GET /api/v1/tables/{table_id}/columns
```

### Get Table Usage Metrics

```http
GET /api/v1/tables/{table_id}/usage
```

**Response**:
```json
{
  "table_id": 1,
  "last_accessed": "2024-08-24T10:00:00",
  "access_count_7d": 150,
  "access_count_30d": 450,
  "access_count_90d": 1200,
  "total_access_count": 5000
}
```

### Create Table

```http
POST /api/v1/tables
```

**Request Body**:
```json
{
  "database_id": 1,
  "name": "new_table",
  "table_type": "PERMANENT",
  "description": "Table description"
}
```

## Job Management

### List Jobs

```http
GET /api/v1/jobs
```

**Query Parameters**:
- `status` (string): Filter by status
- `skip` (integer): Number of records to skip
- `limit` (integer): Maximum records to return

### Get Job Details

```http
GET /api/v1/jobs/{job_id}
```

### Get Job Execution History

```http
GET /api/v1/jobs/{job_id}/executions
```

**Query Parameters**:
- `skip` (integer): Number of records to skip
- `limit` (integer): Maximum records to return

### Create Job

```http
POST /api/v1/jobs
```

**Request Body**:
```json
{
  "name": "job_name",
  "owner": "owner_name",
  "schedule": "0 2 * * *",
  "frequency": "DAILY",
  "description": "Job description"
}
```

## Lifecycle Management

### Get Lifecycle Summary

```http
GET /api/v1/lifecycle/summary
```

**Response**:
```json
{
  "active": 1100,
  "inactive": 100,
  "deprecated": 40,
  "decommissioned": 10,
  "total": 1250
}
```

### Get Unused Assets

```http
GET /api/v1/lifecycle/unused-assets?days=90
```

**Query Parameters**:
- `days` (integer): Number of days of inactivity (default: 90)

### Get Decommissioning Candidates

```http
GET /api/v1/lifecycle/decommissioning-candidates?days=180
```

**Query Parameters**:
- `days` (integer): Number of days of inactivity (default: 180)

### List Lifecycle Assets

```http
GET /api/v1/lifecycle/assets
```

**Query Parameters**:
- `status` (string): Filter by status
- `tier` (string): Filter by tier
- `skip` (integer): Number of records to skip
- `limit` (integer): Maximum records to return

### Update Lifecycle Asset

```http
PATCH /api/v1/lifecycle/assets/{lifecycle_id}
```

**Request Body**:
```json
{
  "owner": "new_owner",
  "tier": "tier_1",
  "status": "active",
  "review_notes": "Reviewed and updated"
}
```

### Mark Asset as Deprecated

```http
POST /api/v1/lifecycle/assets/{table_id}/deprecate
```

**Request Body**:
```json
{
  "reason": "No longer in use"
}
```

### Decommission Asset

```http
POST /api/v1/lifecycle/assets/{table_id}/decommission
```

**Request Body**:
```json
{
  "reason": "End of life"
}
```

## Reporting

### Get Summary

```http
GET /api/v1/reports/summary
```

**Response**:
```json
{
  "total_tables": 1250,
  "active_tables": 1100,
  "inactive_tables": 100,
  "deprecated_tables": 40,
  "decommissioned_tables": 10,
  "total_size_mb": 5234.50
}
```

### Get Asset Age Distribution

```http
GET /api/v1/reports/asset-age
```

**Response**:
```json
{
  "last_90_days": 150,
  "last_1_year": 300,
  "older_than_1_year": 800
}
```

### Get Storage Usage

```http
GET /api/v1/reports/storage-usage
```

**Response**:
```json
{
  "total_mb": 5234.50,
  "total_gb": 5.11,
  "by_status": {
    "active": 4500.00,
    "inactive": 600.00,
    "deprecated": 134.50
  }
}
```

### Get Tier Distribution

```http
GET /api/v1/reports/tier-distribution
```

### Get Lifecycle Transitions

```http
GET /api/v1/reports/lifecycle-transitions?days=30
```

### Get Most Used Tables

```http
GET /api/v1/reports/most-used-tables?limit=10&period=30d
```

**Query Parameters**:
- `limit` (integer): Number of tables to return (default: 10, max: 100)
- `period` (string): Time period - 7d, 30d, or 90d (default: 30d)

### Get Least Used Tables

```http
GET /api/v1/reports/least-used-tables?limit=10&period=90d
```

### Get Data Quality Score

```http
GET /api/v1/reports/data-quality-score
```

**Response**:
```json
{
  "overall_score": 75.5,
  "description_coverage": 80.2,
  "owner_assignment": 70.0,
  "usage_tracking": 76.3
}
```

## Error Responses

### 400 Bad Request

```json
{
  "detail": "Invalid status value"
}
```

### 404 Not Found

```json
{
  "detail": "Table not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error"
}
```

## Pagination

List endpoints support pagination:

- `skip`: Number of records to skip (default: 0)
- `limit`: Maximum records per page (default: 50, max: 500)

Example:
```http
GET /api/v1/tables?skip=50&limit=100
```

## Filtering

Many endpoints support filtering:

```http
GET /api/v1/tables?database_id=1&status=active
GET /api/v1/lifecycle/assets?tier=tier_1&status=deprecated
```

## Response Headers

All responses include:

- `Content-Type: application/json`
- `X-Total-Count`: Total number of records (list endpoints)

## Rate Limiting

Currently no rate limiting is implemented. This will be added in a future release.

## CORS

CORS is enabled for all origins. This can be customized in `src/api/main.py`.

## Examples

### Get all active tables in a database

```bash
curl "http://localhost:8000/api/v1/tables?database_id=1&status=active"
```

### Get unused assets in the last 180 days

```bash
curl "http://localhost:8000/api/v1/lifecycle/unused-assets?days=180"
```

### Mark a table as deprecated

```bash
curl -X POST "http://localhost:8000/api/v1/lifecycle/assets/42/deprecate" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Replaced by new_table_v2"}'
```

### Get detailed usage metrics

```bash
curl "http://localhost:8000/api/v1/tables/42/usage"
```

## Webhooks & Events

Webhooks and event subscriptions are planned for a future release.
