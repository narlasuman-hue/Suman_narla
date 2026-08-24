# Development Guide

## Project Structure

```
suman_narla/
├── src/
│   ├── catalog/              # Core catalog functionality
│   │   ├── __init__.py
│   │   ├── models.py         # SQLAlchemy ORM models
│   │   ├── database.py       # Database connection & session management
│   │   └── services/         # Business logic services (TODO)
│   ├── connectors/           # Database connectors
│   │   ├── base.py           # Abstract base connector
│   │   └── teradata.py       # Teradata connector implementation
│   ├── api/                  # FastAPI application
│   │   ├── main.py           # FastAPI app initialization
│   │   └── routes/           # API endpoints
│   │       ├── health.py     # Health check endpoints
│   │       ├── databases.py  # Database inventory endpoints
│   │       ├── tables.py     # Table inventory endpoints
│   │       └── jobs.py       # Job/schedule endpoints
│   ├── scheduler/            # Background tasks & scheduling
│   │   └── tasks.py          # Metadata collection & update tasks
│   └── config.py             # Application configuration
├── tests/                    # Test suite
│   ├── conftest.py           # Pytest fixtures & configuration
│   ├── test_health.py        # Health check tests
│   └── test_*.py             # Additional tests
├── docs/                     # Documentation
│   └── DEVELOPMENT.md        # This file
├── main.py                   # Application entry point
├── requirements.txt          # Python dependencies
├── .env.example              # Example environment configuration
├── docker-compose.yml        # Docker compose for local development
├── Dockerfile                # Docker image definition
└── CLAUDE.md                 # Project instructions for Claude

```

## Setup & Installation

### Prerequisites
- Python 3.9+
- PostgreSQL 12+ (or use Docker)
- Teradata ODBC driver (for production use)

### Local Development Setup

1. **Clone repository** (already done)

2. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Copy environment configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

5. **Initialize database**:
   ```bash
   python -c "from src.catalog.database import init_db; init_db()"
   ```

6. **Run API server**:
   ```bash
   python main.py
   ```
   API will be available at `http://localhost:8000`

### Docker Development Setup

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up -d
   ```

2. **Access API**:
   - API: `http://localhost:8000`
   - API Docs: `http://localhost:8000/docs`
   - Postgres: `localhost:5432`

3. **View logs**:
   ```bash
   docker-compose logs -f api
   ```

4. **Stop services**:
   ```bash
   docker-compose down
   ```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_health.py

# Run with coverage
pytest --cov=src tests/

# Run with verbose output
pytest -v tests/
```

## Code Quality

### Linting
```bash
ruff check .
```

### Formatting
```bash
black .
ruff format .
```

### Type Checking
```bash
mypy src/
```

### Run All Checks
```bash
black . && ruff check . && mypy src/ && pytest
```

## API Documentation

### Endpoints

#### Health Check
- `GET /health` - Basic health check
- `GET /health/db` - Database connection check

#### Databases
- `GET /api/v1/databases` - List all databases
- `GET /api/v1/databases/{id}` - Get database details
- `POST /api/v1/databases` - Create new database

#### Tables
- `GET /api/v1/tables` - List all tables
- `GET /api/v1/tables/{id}` - Get table details
- `GET /api/v1/tables/{id}/columns` - Get table columns
- `GET /api/v1/tables/{id}/usage` - Get table usage metrics
- `POST /api/v1/tables` - Create new table

#### Jobs
- `GET /api/v1/jobs` - List all jobs
- `GET /api/v1/jobs/{id}` - Get job details
- `GET /api/v1/jobs/{id}/executions` - Get job execution history
- `POST /api/v1/jobs` - Create new job

### Interactive API Docs
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Database Models

### Core Entities
- **Database** - Databases in Teradata
- **Table** - Tables within databases
- **Column** - Columns within tables
- **View** - Views in databases
- **Job** - ETL jobs and schedules
- **JobExecution** - Job execution history

### Lifecycle Tracking
- **AssetLifecycle** - Track creation, decommissioning, ownership, tier
- **UsageMetrics** - Track access frequency and last accessed time
- **AssetTag** - Custom tags and classifications

### Relationships
- **Lineage** - Track data flow between assets
- **AssetTag** - Classification and tagging

## Configuration

Configuration is managed via environment variables (`.env` file). Key settings:

### Database
- `CATALOG_DB_HOST` - PostgreSQL host
- `CATALOG_DB_PORT` - PostgreSQL port
- `CATALOG_DB_NAME` - Database name
- `CATALOG_DB_USER` - Database user
- `CATALOG_DB_PASSWORD` - Database password

### Teradata
- `TERADATA_HOST` - Teradata hostname
- `TERADATA_PORT` - Teradata port (default: 1025)
- `TERADATA_USER` - Teradata username
- `TERADATA_PASSWORD` - Teradata password
- `TERADATA_DATABASE` - Default database

### API
- `API_HOST` - API server host (default: 0.0.0.0)
- `API_PORT` - API server port (default: 8000)
- `API_WORKERS` - Number of worker processes

### Scheduler
- `SCHEDULER_ENABLED` - Enable background scheduler
- `METADATA_SYNC_INTERVAL` - Seconds between metadata syncs (default: 3600)
- `USAGE_STATS_INTERVAL` - Seconds between usage stat updates (default: 1800)

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** and write tests

3. **Run quality checks**:
   ```bash
   black . && ruff check . && mypy src/ && pytest
   ```

4. **Commit changes**:
   ```bash
   git add .
   git commit -m "Add your feature description"
   ```

5. **Push and create PR**:
   ```bash
   git push -u origin feature/your-feature-name
   ```

## Common Issues

### Port Already in Use
If port 8000 is in use:
```bash
# Change API_PORT in .env
API_PORT=8001
```

### Database Connection Errors
1. Ensure PostgreSQL is running
2. Check connection settings in `.env`
3. Verify database exists and user has permissions

### Teradata Connection Errors
1. Check Teradata hostname and port
2. Verify username/password
3. Ensure Teradata driver is installed

## Next Steps

- [ ] Implement metadata sync from Teradata
- [ ] Add usage metrics collection from query logs
- [ ] Implement lineage auto-discovery
- [ ] Add search functionality
- [ ] Create React frontend dashboard
- [ ] Add data quality metrics
- [ ] Implement compliance reporting
- [ ] Add authentication & authorization
