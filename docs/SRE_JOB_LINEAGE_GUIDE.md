# SRE Job Lineage: Project Guide

One page where an SRE can see how tables get loaded, spot failed and late jobs, and trace the
impact from a job down to a single column, for **any** job platform.

- **App:** the Job Lineage page (`/job-lineage`) in the Database Catalog app (FastAPI backend, React frontend)
- **Repository:** `narlasuman-hue/Suman_narla`
- **Demo data:** CSV files in `demo_data/lineage/` (no production access needed)
- **Detailed docs:** [`JOB_LINEAGE.md`](JOB_LINEAGE.md), [`JOB_LINEAGE_DEMO_DATA.md`](JOB_LINEAGE_DEMO_DATA.md)

---

## Contents

1. [What it does](#1-what-it-does)
2. [Platforms](#2-platforms)
3. [Features](#3-features)
4. [How lineage is built](#4-how-lineage-is-built)
5. [Input CSV files](#5-input-csv-files)
6. [Adding a new platform](#6-adding-a-new-platform)
7. [Run it on your computer](#7-run-it-on-your-computer)
8. [Demo script](#8-demo-script)
9. [Troubleshooting](#9-troubleshooting)
10. [API reference](#10-api-reference)
11. [Code map](#11-code-map)
12. [What we did, in order](#12-what-we-did-in-order)
13. [Status and next steps](#13-status-and-next-steps)

---

## 1. What it does

During an incident, the questions are always the same:

- **Which job loads this table, and did it run?**
- **A job failed. What else breaks downstream?** (the blast radius)
- **Why is my job or table late?** (which upstream job is failed or still running)
- **Which jobs will miss their SLA?**
- **Where does this column come from, and where is it used?**

The Job Lineage page answers these for each platform from one screen.

---

## 2. Platforms

A platform is one independent world of jobs and the tables they load. The user picks one
at the top of the page and sees only its lineage. Platforms are **configured, not coded**:
each one is a row in `platforms.csv`.

| Platform | Jobs | Tables they load | Demo jobs | Demo scenario |
|---|---|---|---|---|
| **Mainframe → Teradata** | Mainframe JCL jobs (BTEQ, FastLoad, MultiLoad, TPT) | Teradata tables | 13 | Banking: cards, payroll, loans |
| **Ab Initio → Hadoop** | Ab Initio graphs | Hive tables and HDFS paths | 11 | Banking: cards, fraud |
| **Informatica → Oracle** | Informatica workflows | Oracle tables | 8 | Retail sales |
| **Airflow → Snowflake** | Airflow and dbt tasks | Snowflake tables | 9 | SaaS analytics |
| **DataStage → DB2** | DataStage jobs | DB2 tables | 8 | Health claims |

The selected platform is kept in the URL (`/job-lineage?platform=airflow`), so a view can be shared.

---

## 3. Features

### SRE triage
- **Summary cards:** jobs, tables loaded, failed, running, impacted downstream and late vs SLA.
- **Failed-jobs banner:** one click shows a failure's **blast radius**. That is every downstream job and table, how many levels down each is, its owner and its next scheduled run.
- **Upstream issues:** for any job, the failed or still-running jobs upstream of it.
- **Job details:** owner, scheduler, schedule, last run, duration, error code or message, SLA.

### Search table
Type part of a table name. Each match shows the job that loads it, that job's last run status
and a warning if the table is impacted by an upstream failure. Picking a table shows its lineage.

### 1. SLA tracking
Each job can have an `expected_completion` time. Every job gets one status, worst first:

| Status | Meaning |
|---|---|
| **Late** | Past expected time and not finished (or failed) |
| **Completed late** | Finished, but after the expected time |
| **At risk** | Due within 30 minutes and not done, or blocked by a failed upstream job |
| **On track** | Not due yet |
| **Met** | Finished on time |

The SLA tab shows how late each job is, why, and which upstream job is blocking it.
A run only counts if it falls in the current schedule period, so yesterday's success does
not meet today's SLA.

### 2. Column-level lineage
Click a table, then a column, or use column search. The graph traces the column through every
job that maps it, upstream and downstream, with each job's transformation.

### 3. Database-level lineage
Database to database flows. Examples: `PROD.CARDS → CARDS_STG → CARDS_DB → RISK_DB` and
`s3://acme-lake → RAW.EVENTS → ANALYTICS.FINANCE → salesforce`. Click a database to see its tables.

### 4. Table-level lineage
Table to table, with the loading job on each arrow. A red arrow means that job failed.

### 5. Column search
Type a column name such as `CUSTOMER_ID`. The results list every table that has that column, with:
- its database and data type
- the job that loads the table, with its last run and SLA
- the jobs that read the table
- a button that opens the column's lineage

### Lineage views (toolbar)
| View | Shows |
|---|---|
| **Jobs** | Job to job dependencies |
| **Tables** | Table-level lineage |
| **Jobs + tables** | Jobs and every table or file they read and write |
| **Databases** | Database-level lineage |

---

## 4. How lineage is built

Lineage comes from **matching dataset names**. If one job writes (`OUTPUT`) a dataset and
another job reads (`INPUT`) the same name, the two jobs are linked.

```
PROD.PAYROLL.GL.EXTRACT ──▶ TDPAYLD1 ──▶ FIN_STG.PAYROLL_GL_STG ──▶ TDGLPST1 ──▶ FINANCE_DB.GL_POSTINGS
   (written by PAYEXT01)    (FastLoad)        (Teradata)              (BTEQ)          (Teradata)
```

- Names match case-insensitively. HDFS paths (starting with `/`) must match exactly.
- A dataset whose `dataset_type` is in the platform's `table_types` counts as a **table**. Anything else is a source file or input.
- A job that writes a table is a **load job**.
- If a job fails, everything downstream of it is marked **impacted**.

**Database of a dataset:**

| Dataset | Database |
|---|---|
| `CARDS_DB.CARD_TRANSACTIONS` (a table) | `CARDS_DB` |
| `ANALYTICS.FINANCE.FCT_REVENUE` | `ANALYTICS.FINANCE` |
| `PROD.CARDS.TXN.DAILY` (a mainframe file) | `PROD.CARDS` |
| `/data/raw/cards/auth` | `/data/raw` |
| `s3://acme-lake/events/app/` | `s3://acme-lake` |
| `salesforce://Account` | `salesforce` |

---

## 5. Input CSV files

```
demo_data/lineage/
├── platforms.csv              one row per platform
├── mainframe/
│   ├── jobs.csv               one row per job (incl. SLA expected completion)
│   ├── job_datasets.csv       one row per file/table a job reads or writes
│   ├── table_columns.csv      optional: columns of each table
│   └── column_lineage.csv     optional: source column → target column, per job
├── abinitio/
│   ├── graphs.csv             same as jobs.csv, with graph_name
│   ├── graph_datasets.csv     same as job_datasets.csv, with graph_name
│   ├── table_columns.csv
│   └── column_lineage.csv
├── informatica/               same four files as mainframe/
├── airflow/
└── datastage/
```

You can edit the files in Excel. Each file is checked as it loads, and an error shows the
file, the line and the problem.

### Times
- **Relative to sync time (recommended):** `-9h` (9 hours ago), `+15h`, `-2d`, `+30m`. The demo always looks current.
- **Absolute:** ISO format, e.g. `2026-10-07T01:00`.
- **Clock time** (`expected_completion` only): `06:00` means today at 06:00 UTC.

### `platforms.csv`
| Column | Required | Example | Notes |
|---|---|---|---|
| `platform_id` | yes | `AIRFLOW_SNOWFLAKE` | Upper-case letters, digits, `_`. Unique |
| `folder` | yes | `airflow` | Lower-case sub-folder with the CSVs; also the URL key. Unique |
| `name` | yes | `Airflow → Snowflake` | Shown on the platform card |
| `description` | no | `Airflow tasks loading Snowflake tables` | Card subtitle |
| `job_label` | no | `Airflow task` | What the UI calls a job (default `Job`) |
| `table_label` | no | `Snowflake table` | What the UI calls a table (default `Table`) |
| `table_types` | yes | `SNOWFLAKE` or `HIVE;HDFS` | `dataset_type` values that are this platform's tables, `;`-separated |
| `color` | no | `#0369a1` | Hex color for load jobs and tables (default `#4338ca`) |

```csv
platform_id,folder,name,description,job_label,table_label,table_types,color
MAINFRAME,mainframe,Mainframe → Teradata,Mainframe jobs loading Teradata tables,Mainframe job,Teradata table,TERADATA,#c2410c
HADOOP_ABINITIO,abinitio,Ab Initio → Hadoop,Ab Initio graphs loading Hadoop tables,Ab Initio graph,Hadoop table,HIVE;HDFS,#0f766e
```

### `jobs.csv` (one row per job)
| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` | yes | `TDPAYLD1` | Unique within the platform (`graph_name` in Ab Initio's `graphs.csv`) |
| `owner` | no | `FINANCE_DW_TEAM` | Team or person |
| `description` | no | `FastLoad payroll GL extract` | |
| `job_class` | no | `T` | Mainframe job class |
| `scheduler_system` | no | `CA-7`, `Control-M`, `Airflow` | |
| `schedule_name` | no | `PAYROLL-DAILY` | |
| `frequency` | no | `DAILY`, `HOURLY` | Defines the SLA period |
| `last_run` | no | `-9h` | Start of the last run |
| `last_run_status` | no | `SUCCESS`, `FAILED`, `RUNNING` | |
| `duration_seconds` | no | `420` | |
| `error_message` or `return_code` | no | `ORA-01652 …` / `CC 0008` | Shown when the job failed |
| `expected_completion` | no | `-8h`, `06:00` | SLA deadline |
| `next_run` | no | `+15h` | |

```csv
job_name,owner,description,job_class,scheduler_system,schedule_name,frequency,last_run,last_run_status,return_code,duration_seconds,expected_completion,next_run
PAYEXT01,PAYROLL_TEAM,Daily payroll extract for GL posting,A,CA-7,PAYROLL-DAILY,DAILY,-10h,SUCCESS,CC 0000,840,-9h,+14h
TDPAYLD1,FINANCE_DW_TEAM,FastLoad payroll GL extract into Teradata staging,T,CA-7,PAYROLL-DAILY,DAILY,-9h,SUCCESS,CC 0000,420,-8h,+15h
```

### `job_datasets.csv` (one row per dataset a job reads or writes)
| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` | yes | `PAYEXT01` | Must exist in `jobs.csv` |
| `step` / `port` / `dd_name` | no | `EMPIN`, `in0`, `extract` | Step, port or DD name |
| `dataset_name` | yes | `PROD.PAYROLL.EMPLOYEE.MASTER` | File, table, path or URL |
| `direction` | yes | `INPUT` or `OUTPUT` | |
| `dataset_type` | yes | `PS`, `VSAM`, `TERADATA`, `HIVE`, `HDFS`, `ORACLE`, `SNOWFLAKE`, `DB2`, `FILE`, `S3`, `API` | Compared with `table_types` |
| `disposition` | no | `SHR`, `NEW` | Mainframe only |

```csv
job_name,dd_name,dataset_name,direction,dataset_type,disposition
PAYEXT01,EMPIN,PROD.PAYROLL.EMPLOYEE.MASTER,INPUT,VSAM,SHR
PAYEXT01,TIMEIN,PROD.PAYROLL.TIMECARDS.DAILY,INPUT,PS,SHR
```
```csv
job_name,step,dataset_name,direction,dataset_type
crm_ingest.sync_accounts,extract,salesforce://Account,INPUT,API
crm_ingest.sync_accounts,load,RAW.CRM.ACCOUNTS,OUTPUT,SNOWFLAKE
```

### `table_columns.csv` (optional; one row per column)
| Column | Required | Example |
|---|---|---|
| `dataset_name` | yes | `PROD.PAYROLL.EMPLOYEE.MASTER` |
| `column_name` | yes | `EMP_ID` |
| `data_type` | no | `PIC X(10)`, `VARCHAR(20)` |
| `description` | no | `Employee number` |

```csv
dataset_name,column_name,data_type,description
PROD.PAYROLL.EMPLOYEE.MASTER,EMP_ID,PIC X(10),Employee number
PROD.PAYROLL.EMPLOYEE.MASTER,EMP_NAME,PIC X(40),
```

### `column_lineage.csv` (optional; one row per column mapping)
| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` | yes | `PAYEXT01` | The job must read the source and write the target |
| `source_dataset` | yes | `PROD.PAYROLL.EMPLOYEE.MASTER` | |
| `source_column` | yes | `EMP_ID` | |
| `target_dataset` | yes | `PROD.PAYROLL.GL.EXTRACT` | |
| `target_column` | yes | `EMP_ID` | |
| `transformation` | no | `SUM(AMOUNT)` | Shown on the arrow |

```csv
job_name,source_dataset,source_column,target_dataset,target_column,transformation
PAYEXT01,PROD.PAYROLL.EMPLOYEE.MASTER,EMP_ID,PROD.PAYROLL.GL.EXTRACT,EMP_ID,
PAYEXT01,PROD.PAYROLL.EMPLOYEE.MASTER,COST_CENTER,PROD.PAYROLL.GL.EXTRACT,COST_CENTER,
```

### Demo story

| Platform | Failed job | Blast radius | Running |
|---|---|---|---|
| Mainframe → Teradata | `CRDTXN01` (ABEND S0C7) | `TDCRDLD1` → `TDCRDPST` → `TDFRAUD1` | `TDCUSLD1` |
| Mainframe → Teradata | `TDLNSLD1` (CC 0008) | `TDLNSRPT` | |
| Ab Initio → Hadoop | `bld_cards_txn_enriched.mp` (out of memory) | `bld_fraud_features.mp` → `score_fraud_model.mp` → `exp_fraud_alerts.mp`, `bld_spend_insights.mp` | `ing_web_clickstream.mp` |
| Ab Initio → Hadoop | `bld_loan_funnel.mp` (record format changed) | none (final table) | |
| Informatica → Oracle | `wf_fact_sales` (ORA-01652) | `wf_agg_daily_sales` → `wf_exp_finance_feed` | `wf_stg_returns` |
| Airflow → Snowflake | `dbt_finance.fct_revenue` (numeric value 'N/A') | `bi_refresh.revenue_daily`, `reverse_etl.push_revenue_to_crm` | `dbt_core.fct_sessions` |
| DataStage → DB2 | `dsj_load_provider_dim` (SQL0803N duplicate key) | `dsj_load_claim_fact` → `dsj_build_claims_mart` → `dsj_exp_regulatory` | `dsj_ext_pharmacy` |

**Good searches:**

| Search | Platform | Terms to try |
|---|---|---|
| Tables | Mainframe | `CARD_TRANSACTIONS`, `GL_POSTINGS`, `COLLECTIONS_QUEUE` |
| Tables | Ab Initio | `fraud_scores`, `txn_enriched` |
| Tables | Informatica | `FACT_SALES` |
| Tables | Airflow | `FCT_REVENUE` |
| Tables | DataStage | `CLAIM_FACT` |
| Columns | Mainframe | `CUSTOMER_ID` (8 tables) |
| Columns | DataStage | `MEMBER_ID` (4 tables) |
| Columns | Airflow | `REVENUE_USD`, `ACCOUNT_ID` |
| Columns | Informatica | `ORDER_ID`, `CUSTOMER_NO` |

---

## 6. Adding a new platform

No code changes are needed. For example, to add SSIS packages loading SQL Server tables:

**1. Add a row to `demo_data/lineage/platforms.csv`:**
```csv
SSIS_SQLSERVER,ssis,SSIS → SQL Server,SSIS packages loading SQL Server tables,SSIS package,SQL Server table,SQLSERVER,#b45309
```

**2. Create the folder `demo_data/lineage/ssis/`.** Put in it:
- `jobs.csv` and `job_datasets.csv`
- optionally, `table_columns.csv` and `column_lineage.csv`

Copying `informatica/` and editing it is the fastest start.

**3. Click Sync job metadata.** A new card appears, with lineage, SLA tracking, column search
and blast radius.

**For production sources:** implement `BaseLineageConnector` (`src/connectors/base_lineage.py`)
for the platform. Possible sources:
- scheduler exports
- Ab Initio Metadata Hub
- the Informatica repository
- the Airflow REST API and dbt `manifest.json`
- DataStage exports

Then sync it with
`LineageSyncService(db, "<platform_id>", connector).sync_all()`. The rest of the app stays the same.

---

## 7. Run it on your computer

### Prerequisites
| Tool | Version | Install on Windows |
|---|---|---|
| Python | **3.11 or 3.12** (not 3.13 or newer) | `winget install -e --id Python.Python.3.12`, or python.org (tick **Add python.exe to PATH**) |
| Node.js | **18, 20 or 22 LTS** | `winget install -e --id OpenJS.NodeJS.LTS`, or nodejs.org |
| Git | any | `winget install -e --id Git.Git` |

After installing, **close and reopen** the terminal, then check:
```cmd
py -3.12 --version
node --version
git --version
```

### Step 1: Get the code
```cmd
git clone https://github.com/narlasuman-hue/Suman_narla.git
cd Suman_narla
```

### Easiest on Windows: `run_demo.bat`
After Step 1, open the `Suman_narla` folder in File Explorer and **double-click `run_demo.bat`**.
If Windows shows "Windows protected your PC", click **More info → Run anyway**. The script:
- checks that Python 3.12 and Node.js are installed, and says how to install either one if it's missing
- installs the backend and frontend packages (first run only, 5–10 minutes)
- opens two windows, **Lineage BACKEND** and **Lineage FRONTEND**. Keep both open during the demo
- loads the demo data and opens **http://localhost:3000/job-lineage** in your browser

To stop the demo, close the two "Lineage" windows. To start it again, double-click `run_demo.bat`.
Later runs take about a minute.

To start it by hand instead (any OS), follow Steps 2–4.

### Step 2: Backend (Terminal 1, keep it open)

**Command Prompt (`C:\...>`):**
```cmd
py -3.12 -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
set DATABASE_URL=sqlite:///./lineage_demo.db
uvicorn src.api.main:app --port 8000
```

**PowerShell (`PS C:\...>`):**
```powershell
py -3.12 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:DATABASE_URL="sqlite:///./lineage_demo.db"
uvicorn src.api.main:app --port 8000
```

**Mac / Linux:**
```bash
python3.12 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
DATABASE_URL=sqlite:///./lineage_demo.db uvicorn src.api.main:app --port 8000
```

Wait for `Application startup complete.` `DATABASE_URL` must be set **in the same window**.
Without it, the app tries PostgreSQL.

### Step 3: Frontend (Terminal 2, keep it open)

**Command Prompt:**
```cmd
cd Suman_narla\frontend
npm install --legacy-peer-deps
set DANGEROUSLY_DISABLE_HOST_CHECK=true
set TSC_COMPILE_ON_ERROR=true
npm start
```

**PowerShell:**
```powershell
cd Suman_narla\frontend
npm install --legacy-peer-deps
$env:DANGEROUSLY_DISABLE_HOST_CHECK="true"
$env:TSC_COMPILE_ON_ERROR="true"
npm start
```

**Mac / Linux:**
```bash
cd Suman_narla/frontend
npm install --legacy-peer-deps
DANGEROUSLY_DISABLE_HOST_CHECK=true TSC_COMPILE_ON_ERROR=true npm start
```

Wait for `Compiled successfully!` or `Compiled with warnings`. Warnings are fine.

### Step 4: Load the demo data
1. Open **http://localhost:3000/job-lineage**.
2. Click **Sync job metadata** (top right).
3. You should see **"Synced 49 jobs across 5 platforms"**.

### Fresh start (e.g. on event day)
1. Stop the backend: press Ctrl+C, or close the "Lineage BACKEND" window.
2. Delete `lineage_demo.db`.
3. Start it again (or double-click `run_demo.bat`) and click **Sync** if the cards show 0 jobs.

---

## 8. Demo script

About 10 minutes, the same order as the demo video (`Job_Lineage_Demo.mp4`).

| # | Do this | Say this |
|---|---|---|
| 1 | Open `/job-lineage` | "One page for every job platform. Five are configured from a CSV file." |
| 2 | Mainframe card → summary cards → scroll to the graph | "13 jobs, 2 failed, 4 late. Red border = failed, dotted = running, ⏰ = late." |
| 3 | Click **CRDTXN01 — show blast radius** | "This abend affects three downstream Teradata jobs and their tables, with owners and next runs." |
| 4 | **SLA tracking** tab | "What is late, how late, and why. TDCRDLD1 is late because CRDTXN01 failed." |
| 5 | **Lineage** tab → search table `CARD_TRANS` → **Tables** | "Table-level lineage, with the load job on each arrow. Red = failed." |
| 6 | **Column** → `CUSTOMER_ID` → **Column lineage** | "Every table with this column, and the column traced through every job." |
| 7 | **Databases** view | "Database-level flow: PROD.CARDS → CARDS_STG → CARDS_DB → RISK_DB." |
| 8 | Ab Initio card → **bld_cards_txn_enriched.mp — show blast radius** | "Same features on Hadoop." |
| 9 | Informatica, Airflow, DataStage cards | "New platforms from config only: ORA-01652, dbt failure out to Salesforce, DB2 duplicate key." |
| 10 | Show `platforms.csv` | "Adding a platform takes one row and a folder of CSVs." |

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| `Python was not found; run without arguments to install from the Microsoft Store` | Python isn't installed. Install 3.12 (section 7), reopen the terminal and use `py -3.12`. |
| `'node' is not recognized` | Node isn't installed. Install the LTS version and reopen the terminal. |
| `pip install` fails building `pydantic-core` or `sqlalchemy` | You are on Python 3.13+. Use 3.12 and recreate the venv. |
| `psycopg2.OperationalError … port 5432 … Connection refused` | `DATABASE_URL` isn't set in the backend window. Set it (Step 2) in the **same** window, check with `echo %DATABASE_URL%` / `echo $env:DATABASE_URL`, and make sure there is no `.env` file. |
| `npm install` fails with `ERESOLVE` | Add `--legacy-peer-deps`. |
| `options.allowedHosts[0] should be a non-empty string` | Set `DANGEROUSLY_DISABLE_HOST_CHECK=true`. |
| Red overlay: `TS6133 … is declared but its value is never read` | Old type errors in other pages. Set `TSC_COMPILE_ON_ERROR=true`. |
| `[eslint] 'FiSearch' is not defined` or runtime `FiSearch is not defined` | Your copy is older than PR #28. Run `git pull` on `main`, or add `FiSearch,` after `FiChevronRight,` in the `react-icons/fi` import in `frontend/src/pages/Dashboard.tsx`. |
| PowerShell: `running scripts is disabled on this system` | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then answer **Y**. |
| Page loads but shows no platforms | The backend isn't running. Check Terminal 1. |
| `run_demo.bat` says the backend or frontend did not start | Read the error in the "Lineage BACKEND" or "Lineage FRONTEND" window. If the pip step failed, delete the `venv` folder, make sure Python 3.12 is installed, and run it again. |
| `localhost:3000` / `localhost:8000` "can't be reached" | The servers aren't running (windows closed or PC restarted). Double-click `run_demo.bat`. |
| Sync shows `Invalid lineage input file: … line N: …` | Fix that line in that CSV file and sync again. |
| A removed or renamed job still shows | Start with a fresh database: delete `lineage_demo.db` and re-sync. |

---

## 10. API reference

All endpoints are under `/api/v1`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/job-lineage/platforms` | Configured platforms with a summary: jobs, failed, running, SLA late |
| GET | `/job-lineage/graph?platform=&focus=&direction=&depth=` | Nodes, edges and summary for one platform |
| GET | `/job-lineage/tables?platform=&q=` | Table search, with the `loaded_by` / `read_by` jobs |
| GET | `/job-lineage/sla?platform=` | SLA status of every job, worst first, with `blocked_by` |
| GET | `/job-lineage/columns?platform=&q=&exact=` | Column search |
| GET | `/job-lineage/table-columns?platform=&dataset=` | Columns of one table |
| GET | `/job-lineage/column-lineage?platform=&column=&direction=&depth=` | Column-level lineage; `column` = `dataset:<TABLE>::<COLUMN>` |
| GET | `/job-lineage/impact?platform=&node=job:12` | Blast radius and upstream failing/running jobs |
| POST | `/job-lineage/sync` | Sync all platforms. Returns `{source, platforms: {id: stats}, jobs_synced}` |

Storage:
- **Jobs:** `jobs` and `job_files`, keyed by `source_system` = `platform_id`
- **Runs:** `job_executions`
- **SLAs:** `job_sla`
- **Columns:** `dataset_columns`
- **Column mappings:** `column_lineage`

---

## 11. Code map

| Area | Path |
|---|---|
| Platform registry (`platforms.csv`) | `src/catalog/platforms.py` |
| Connector interface | `src/connectors/base_lineage.py` |
| CSV connector | `src/connectors/lineage_files.py` |
| Generic sync | `src/catalog/services/lineage_sync.py` |
| Lineage graph, impact, table search | `src/catalog/services/job_lineage.py` |
| SLA rules | `src/catalog/services/sla.py` |
| Column lineage and search | `src/catalog/services/column_lineage.py` |
| API routes | `src/api/routes/job_lineage.py` |
| Page | `frontend/src/pages/JobLineagePage.tsx` |
| Graph (cytoscape) | `frontend/src/components/LineageGraph.tsx` |
| Details panel | `frontend/src/components/LineageDetailsPanel.tsx` |
| View builders (tables, databases, columns) | `frontend/src/utils/lineageViews.ts` |
| Tests | `tests/test_platforms.py`, `tests/test_sla_and_columns.py`, `tests/test_lineage_files.py`, `tests/test_job_lineage.py` |
| Docs | `docs/JOB_LINEAGE.md`, `docs/JOB_LINEAGE_DEMO_DATA.md`, `docs/SRE_JOB_LINEAGE_GUIDE.md` |

Run the lineage tests:
```bash
pytest tests/test_platforms.py tests/test_sla_and_columns.py tests/test_lineage_files.py tests/test_job_lineage.py
```

---

## 12. What we did, in order

1. **Added a Job Lineage page** to the Database Catalog. It shows jobs and the files and tables they read and write as a graph.
2. **Split it into platforms.** We started with Mainframe → Teradata and Ab Initio → Hadoop, chosen at the top of the page.
3. **Added SRE triage:** summary cards, the failed-jobs banner with blast radius, upstream issues and job details.
4. **Added table search** that shows the load job and its last run.
5. **Made it run without production access** from editable CSV files, with validation errors that name the file and line. *(PR #26, merged.)*
6. **Added five features:** SLA tracking, column-level lineage, database-level lineage, table-level lineage and column search.
7. **Made it generic.** Platforms come from `platforms.csv`, one connector and sync work for every platform, and we added three demo platforms: Informatica, Airflow and DataStage. *(PR #27, merged.)*
8. **Tested and documented it.** 113 lineage tests pass, including one that adds a new platform from files alone, and each platform was checked in the running app.
9. **Fixed a Dashboard bug** found during local setup: the missing `FiSearch` import. *(PR #28, merged.)*
10. **Wrote this guide** (`docs/SRE_JOB_LINEAGE_GUIDE.md`).
11. **Added `run_demo.bat`**, a double-click starter for Windows.

---

## 13. Status and next steps

| Item | Status |
|---|---|
| PR #26: Job Lineage page, platforms, table search | Merged |
| PR #27: demo CSVs, five features, generic platforms | Merged |
| PR #28: `FiSearch` import fix in Dashboard | Merged |

**Known issues (already on `main`, not caused by this work):**
- **TypeScript errors in older pages** (`Header`, `Layout`, `AssetDetail`, `QueryAnalysisPage`). Work around them with `TSC_COMPILE_ON_ERROR=true`.
- **CI checks red on `main`** (lint, tests, build). These need a separate cleanup.
- **An open CodeQL note** on the sync route's error message. It returns our own validation text (file, line, problem); no stack trace is exposed.

**After the event:**
- **Connect real sources** with one `BaseLineageConnector` per platform.
- **Schedule the sync** instead of running it on click.
- **Add alerting**, e.g. on SLA "At risk", to page the owner.
