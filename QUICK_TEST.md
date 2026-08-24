# Quick Start Testing Guide

**Get the entire application running with sample data in 5 minutes.**

## Step 1: Load Sample Data (30 seconds)

### Linux/Mac:
```bash
chmod +x scripts/load_sample_data.sh
./scripts/load_sample_data.sh
```

### Windows:
```bash
scripts\load_sample_data.bat
```

**Output:**
```
✅ Sample data populated successfully!
  - 4 databases
  - 8 tables
  - 4 jobs
```

## Step 2: Start Backend API (1 minute)

```bash
# Activate virtual environment (if needed)
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Start API server
python main.py
```

**Wait for:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

📌 API available at: **http://localhost:8000**
📌 API Docs at: **http://localhost:8000/docs**

## Step 3: Start Frontend (2 minutes)

In a new terminal:

```bash
cd frontend
npm install  # Only needed first time
npm start
```

**Wait for:**
```
Compiled successfully!
You can now view metadata-catalog-ui in the browser.
  Local:            http://localhost:3000
```

📌 Frontend available at: **http://localhost:3000**

---

## Test the Application (2 minutes)

### ✅ 1. Dashboard
- Open **http://localhost:3000**
- Verify statistics display (4 databases, 8 tables, 48 columns)
- Click "Recent Databases" to see sample data

### ✅ 2. Search
- Click **Search** in sidebar
- Type: `customer` → Should find 3 tables
- Type: `email` (filter to Columns) → Should find 2 columns
- Autocomplete should suggest table names

### ✅ 3. Asset Details
- From search results, click on **customers_table**
- Verify shows 7 columns with data types
- Verify row count: 5,000,000
- Verify status: ACTIVE

### ✅ 4. Lineage
- Click **Lineage** in sidebar
- View **Upstream** tab → See data sources
- View **Downstream** tab → See data targets
- View **Full** tab → Complete data flow

### ✅ 5. Lifecycle
- Click **Lifecycle** in sidebar
- See active/deprecated/decommissioned counts
- View "Decommissioning Candidates" → old_customer_data
- View "Unused Assets" → inactive tables

### ✅ 6. Reports
- Click **Reports** in sidebar
- See storage usage pie chart
- See most used tables chart
- See data quality metrics

### ✅ 7. Query Analysis
- Click **Query Analysis** in sidebar
- See list of heavy users
- See query statistics
- Button to parse query logs

---

## API Testing (No Frontend)

If you only want to test the API, skip Step 3 and use curl:

### Health Check
```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### List Databases
```bash
curl http://localhost:8000/api/v1/databases | jq
```

### Search
```bash
curl "http://localhost:8000/api/v1/search?q=customer" | jq
```

### Get Table Details
```bash
curl http://localhost:8000/api/v1/tables/1 | jq
```

### Full API Documentation
Open: **http://localhost:8000/docs**

---

## What's in the Sample Data?

| Item | Count | Details |
|------|-------|---------|
| Databases | 4 | analytics, raw_data, customer, legacy |
| Tables | 8 | From 1K to 100M rows |
| Columns | 48 | Various types, some marked sensitive |
| Jobs | 4 | Daily, hourly, weekly schedules |
| Lineage | 4 | Complete data flow examples |

### Notable Tables
- **customers_table** - 5M rows, PII data (email, phone)
- **orders_table** - 50M rows, critical tier
- **raw_events** - 100M rows, high tier
- **analytics_summary** - Aggregated metrics
- **old_customer_data** - DEPRECATED table

---

## Quick Commands Reference

| Goal | Command |
|------|---------|
| Load sample data | `./scripts/load_sample_data.sh` |
| Reset all data | Delete database & run sample data loader again |
| Start backend | `python main.py` |
| Start frontend | `cd frontend && npm start` |
| Stop backend | `Ctrl+C` in terminal |
| Stop frontend | `Ctrl+C` in terminal |
| View API docs | Open http://localhost:8000/docs |
| View frontend | Open http://localhost:3000 |
| Test with curl | `curl http://localhost:8000/health` |

---

## Troubleshooting

### Backend won't start
```bash
# Check if port 8000 is in use
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# If in use, change port in .env
API_PORT=8001
```

### Frontend won't load data
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check API_BASE_URL
cat frontend/.env | grep API_BASE_URL

# 3. Open browser console (F12) for errors
# 4. Hard refresh: Ctrl+Shift+R (Linux/Mac) or Cmd+Shift+R (Mac)
```

### Database connection error
```bash
# Check PostgreSQL is running (if using Docker)
docker-compose ps

# Restart services
docker-compose down
docker-compose up -d
```

---

## What to Test

### ✅ Backend API
- [x] Health endpoints respond
- [x] Database listing works
- [x] Table/column retrieval works
- [x] Search functionality works
- [x] Lineage extraction works
- [x] Lifecycle endpoints work
- [x] Reports generate data

### ✅ Frontend UI
- [x] Pages load without errors
- [x] Data displays on dashboard
- [x] Search finds results
- [x] Lineage visualization works
- [x] Lifecycle data shows
- [x] Reports render charts
- [x] Navigation between pages works

### ✅ Features
- [x] Statistics cards display correctly
- [x] Tables with many rows display pagination
- [x] Columns show data types and sensitivity
- [x] Lineage shows upstream/downstream
- [x] Unused assets identified
- [x] Charts render properly
- [x] Autocomplete suggests table names

---

## Next Steps

### To Connect Real Data
1. Configure Teradata in `.env`
2. Run: `python -m src.cli sync`
3. View synced data in frontend

### To Modify Sample Data
1. Edit `src/sample_data.py`
2. Reload: `./scripts/load_sample_data.sh`

### To Deploy
1. Build Docker image: `docker build -t catalog:latest .`
2. Set up production PostgreSQL
3. Configure environment variables
4. Deploy API and frontend to servers

---

## Success Criteria

You'll know everything is working when:

✅ **Backend**
- http://localhost:8000/health returns healthy status
- http://localhost:8000/docs shows API documentation
- API returns data for all endpoints

✅ **Frontend**
- http://localhost:3000 loads without errors
- Dashboard shows statistics
- Search finds sample tables
- Lineage displays relationships
- Reports show charts

✅ **Integration**
- Frontend successfully loads data from backend
- All page transitions work
- No console errors in DevTools

**Congratulations!** 🎉 Full stack is working!
