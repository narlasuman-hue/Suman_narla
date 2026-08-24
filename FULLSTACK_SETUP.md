# Full-Stack Setup Guide

Complete guide to setting up and running the Database Metadata Catalog application (both backend API and React frontend).

## System Requirements

- **Python 3.9+** (for backend)
- **Node.js 16+** and npm/yarn (for frontend)
- **PostgreSQL 12+** (can use Docker)
- **Teradata ODBC driver** (for production Teradata access)

## Quick Start (Local Development)

### 1. Clone and Setup Repository

```bash
git clone https://github.com/narlasuman-hue/Suman_narla.git
cd Suman_narla
```

### 2. Backend Setup

#### Option A: Docker Compose (Recommended)

The easiest way to run the backend with PostgreSQL:

```bash
# Start services
docker-compose up -d

# Check API
curl http://localhost:8000/health

# View Swagger UI
open http://localhost:8000/docs
```

#### Option B: Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your database credentials

# Initialize database
python -c "from src.catalog.database import init_db; init_db()"

# Run API server
python main.py
```

The API will be available at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Setup environment
cp .env.example .env
# Edit .env if backend is on different URL

# Start dev server
npm start
```

The frontend will open at `http://localhost:3000`

---

## Detailed Backend Setup

### Prerequisites

- PostgreSQL 12+ (for catalog database)
- Python 3.9+
- Teradata connection (optional, for syncing live data)

### Environment Configuration

1. **Copy example configuration**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env`** with your settings:

   ```env
   # Catalog Database (PostgreSQL)
   CATALOG_DB_HOST=localhost
   CATALOG_DB_PORT=5432
   CATALOG_DB_NAME=metadata_catalog
   CATALOG_DB_USER=postgres
   CATALOG_DB_PASSWORD=postgres

   # Teradata Connection
   TERADATA_HOST=teradata.example.com
   TERADATA_PORT=1025
   TERADATA_USER=your_username
   TERADATA_PASSWORD=your_password
   TERADATA_DATABASE=your_database

   # API Server
   API_HOST=0.0.0.0
   API_PORT=8000
   API_WORKERS=4

   # Scheduler
   SCHEDULER_ENABLED=true
   METADATA_SYNC_INTERVAL=3600
   USAGE_STATS_INTERVAL=1800
   ```

### Database Setup

#### Using Docker (Recommended)

```bash
# Docker Compose will automatically:
# 1. Start PostgreSQL
# 2. Run database initialization
# 3. Start the API server

docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

#### Manual PostgreSQL Setup

```bash
# Create database and user
createdb -U postgres metadata_catalog

# Initialize tables
python -c "from src.catalog.database import init_db; init_db()"
```

### Running the Backend

```bash
# Activate virtual environment
source venv/bin/activate

# Run development server with auto-reload
python main.py

# API will be at http://localhost:8000
# API docs at http://localhost:8000/docs
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_health.py
```

### Quality Checks

```bash
# Format code
ruff format .

# Lint code
ruff check .

# Type check
mypy src/

# Run all checks
ruff format . && ruff check . && mypy src/ && pytest
```

---

## Detailed Frontend Setup

### Prerequisites

- Node.js 16+
- npm or yarn
- Backend API running (see Backend Setup above)

### Environment Configuration

1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```

2. **Copy example configuration**:
   ```bash
   cp .env.example .env
   ```

3. **Edit `.env`** (default should work if backend is on localhost:8000):
   ```env
   REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
   REACT_APP_ENV=development
   ```

### Installing Dependencies

```bash
# Using npm
npm install

# Or using yarn
yarn install
```

### Running Development Server

```bash
# Start with npm
npm start

# Or with yarn
yarn start
```

The frontend will automatically open at `http://localhost:3000`

### Building for Production

```bash
# Create production build
npm run build

# Output will be in build/ directory
```

### Testing & Linting

```bash
# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Lint code
npm run lint

# Format code
npm run format
```

---

## Verifying Full-Stack Setup

Once both backend and frontend are running:

### 1. Backend Health Check

```bash
# Test API
curl http://localhost:8000/health
# Expected response: {"status": "healthy"}

# Test database connection
curl http://localhost:8000/health/db
# Expected response: {"status": "healthy", "database": "connected"}

# View API documentation
# Open http://localhost:8000/docs
```

### 2. Frontend Health Check

```bash
# Frontend should be running at http://localhost:3000
# You should see:
# - Dashboard page with statistics
# - Search functionality
# - Navigation sidebar with all pages

# Check browser console for any errors
# (Open DevTools: Ctrl+Shift+I or Cmd+Option+I)
```

### 3. API Integration Test

In the frontend:

1. Go to Dashboard (home page)
2. You should see:
   - Catalog statistics (databases, tables, columns)
   - Recent databases list
   - Recent tables list
3. Try searching for a table (if any exist in catalog)
4. Check that search results appear

If you see data loading, the full-stack integration is working!

---

## Common Issues & Troubleshooting

### Backend Issues

#### Port 8000 Already in Use

```bash
# Change API_PORT in .env
API_PORT=8001

# Then restart the API
python main.py
```

#### Database Connection Failed

```bash
# Check PostgreSQL is running
docker-compose ps

# Check connection credentials in .env
# Verify database exists
psql -U postgres -d metadata_catalog

# Reinitialize database
python -c "from src.catalog.database import init_db; init_db()"
```

#### Teradata Connection Error

- Ensure `TERADATA_HOST` is correct
- Verify Teradata credentials in `.env`
- For local testing, you can leave Teradata fields empty
- Metadata sync will only work with valid Teradata connection

### Frontend Issues

#### "Cannot GET /" Error

- Make sure backend API is running on correct port
- Check `REACT_APP_API_BASE_URL` in `.env`
- Backend should be on `http://localhost:8000`

#### "Failed to fetch" or CORS Errors

- Backend must be running before frontend starts
- Backend may need CORS configuration if on different origin
- Check browser console for detailed error messages

#### Dependencies Not Installing

```bash
# Clear node_modules and cache
rm -rf node_modules
npm cache clean --force

# Reinstall
npm install
```

#### Hot Reload Not Working

```bash
# Stop dev server (Ctrl+C)
# Clear cache and restart
rm -rf node_modules/.cache
npm start
```

### Integration Issues

#### Frontend Can't Connect to Backend

1. **Check URLs match**:
   - Frontend: `http://localhost:3000`
   - Backend API: `http://localhost:8000/api/v1`
   - In frontend `.env`: `REACT_APP_API_BASE_URL=http://localhost:8000/api/v1`

2. **Test API directly**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status": "healthy"}
   ```

3. **Check browser console** for detailed errors (F12 or Cmd+Option+I)

#### Data Not Loading

- First, check if backend has any data
- Check Teradata connection if you haven't synced data yet
- Use backend CLI to manually sync: `python -m src.cli sync`
- Wait a moment for API responses to load

---

## Development Workflow

### Daily Development

```bash
# Terminal 1: Start Backend
source venv/bin/activate
python main.py
# Backend running at http://localhost:8000

# Terminal 2: Start Frontend  
cd frontend
npm start
# Frontend running at http://localhost:3000

# Terminal 3: (Optional) Run tests
pytest -v tests/
```

### Making Changes

1. **Backend changes**:
   ```bash
   # Make edits to src/ files
   # API reloads automatically
   # Write tests: tests/test_*.py
   # Run: pytest
   ```

2. **Frontend changes**:
   ```bash
   # Make edits to frontend/src/ files
   # Browser reloads automatically via hot reload
   # Run: npm test
   ```

### Before Committing

```bash
# Backend
ruff format . && ruff check . && mypy src/ && pytest

# Frontend
npm run format && npm run lint

# Then commit
git add .
git commit -m "Descriptive message"
git push
```

---

## Production Deployment

### Backend Deployment

1. **Build Docker image**:
   ```bash
   docker build -t metadata-catalog:latest .
   ```

2. **Push to registry**:
   ```bash
   docker tag metadata-catalog:latest your-registry/metadata-catalog:latest
   docker push your-registry/metadata-catalog:latest
   ```

3. **Deploy**:
   ```bash
   # Using docker-compose or Kubernetes
   # Ensure CATALOG_DB_* variables point to production database
   # Ensure TERADATA_* variables have production credentials
   ```

### Frontend Deployment

1. **Build production bundle**:
   ```bash
   cd frontend
   npm run build
   ```

2. **Deploy to CDN or web server**:
   ```bash
   # Upload build/ directory contents to web server
   # Configure REACT_APP_API_BASE_URL for production API
   ```

3. **Serve via nginx or similar**:
   ```nginx
   server {
       listen 80;
       root /var/www/catalog;
       index index.html;
       
       location / {
           try_files $uri $uri/ /index.html;
       }
       
       location /api {
           proxy_pass http://api-backend:8000;
       }
   }
   ```

---

## Documentation

For detailed information, see:

- [Backend API Documentation](./docs/API.md) - All API endpoints
- [Data Lineage Guide](./docs/LINEAGE.md) - Lineage concepts and usage
- [Search Guide](./docs/SEARCH.md) - Search capabilities
- [CLI Reference](./docs/CLI.md) - Command-line tools
- [Frontend README](./frontend/README.md) - Frontend setup and components

---

## Support

### Getting Help

1. Check the documentation files listed above
2. Review backend code in `src/`
3. Review frontend code in `frontend/src/`
4. Check error logs:
   ```bash
   # Backend logs
   docker-compose logs api
   
   # Frontend console
   # Browser DevTools (F12)
   ```

### Reporting Issues

When reporting issues, include:
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs or error messages
- Your environment (OS, Python/Node version)

---

## Next Steps

After successful setup:

1. **Explore the API**:
   - Open http://localhost:8000/docs
   - Try different endpoints
   - Check database models

2. **Populate with Data**:
   ```bash
   # Sync from Teradata (if configured)
   python -m src.cli sync
   
   # Or check API for sample queries
   curl http://localhost:8000/api/v1/databases
   ```

3. **Use the Frontend**:
   - Explore Dashboard
   - Try Search functionality
   - Check Asset Details
   - View Reports

4. **Run Tests**:
   ```bash
   # Backend tests
   pytest -v
   
   # Frontend tests
   npm test
   ```

5. **Read Documentation**:
   - Data Lineage Guide
   - Search Guide
   - API Documentation
   - CLI Reference

---

## License

Mozilla Public License 2.0 - See [LICENSE](./LICENSE)
