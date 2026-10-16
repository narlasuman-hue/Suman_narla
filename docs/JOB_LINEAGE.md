# Job Lineage: one UI for any job platform

The **Job Lineage** page (`/job-lineage` in the UI) covers **independent platforms**: one
world of jobs and the tables they load. The user picks one at the top of the page and sees
only that platform's lineage. Platforms are **configured, not coded** (see
[Adding a platform](#adding-a-platform)). The demo ships five:

| Platform | Jobs | Tables they load | URL |
|---|---|---|---|
| **Mainframe → Teradata** | Mainframe JCL jobs, including BTEQ / FastLoad / MultiLoad / TPT load jobs | Teradata tables, loaded from mainframe datasets | `/job-lineage?platform=mainframe` |
| **Ab Initio → Hadoop** | Ab Initio graphs | Hadoop tables (Hive / HDFS) | `/job-lineage?platform=abinitio` |
| **Informatica → Oracle** | Informatica workflows | Oracle tables | `/job-lineage?platform=informatica` |
| **Airflow → Snowflake** | Airflow / dbt tasks | Snowflake tables | `/job-lineage?platform=airflow` |
| **DataStage → DB2** | DataStage jobs | DB2 tables | `/job-lineage?platform=datastage` |

The selected platform is kept in the URL, so you can share a link to one platform's view.
Each platform card shows its job count, failed jobs and late SLAs.

## Adding a platform

A platform needs **one row in `platforms.csv` and one folder of CSV files**. No code changes.

```
demo_data/lineage/
├── platforms.csv
└── ssis/                  ← the row's `folder`
    ├── jobs.csv
    ├── job_datasets.csv
    ├── table_columns.csv  (optional)
    └── column_lineage.csv (optional)
```

```csv
platform_id,folder,name,description,job_label,table_label,table_types,color
SSIS_SQLSERVER,ssis,SSIS → SQL Server,SSIS packages loading SQL Server tables,SSIS package,SQL Server table,SQLSERVER,#b45309
```

| Column | Required | Meaning |
|---|---|---|
| `platform_id` | yes | Upper-case id (`A-Z`, `0-9`, `_`), stored on every job and used by the API |
| `folder` | yes | Lower-case sub-folder with the platform's CSVs; also the `?platform=` URL key |
| `name` | yes | Shown on the platform card |
| `table_types` | yes | `dataset_type` values that are this platform's **tables**, `;`-separated (`HIVE;HDFS`). Every other dataset is a source file or input. A job that writes one of these tables is a **load** job |
| `description` | no | Card subtitle |
| `job_label` / `table_label` | no | Words the UI uses, e.g. "Airflow task", "Snowflake table" (default "Job", "Table") |
| `color` | no | Hex color for the platform's load jobs and tables (default `#4338ca`) |

Then click **Sync job metadata**. The sync validates `platforms.csv` (unique ids and folders, valid
colors, non-empty `table_types`) and reports the file, line and problem if something is wrong.
Without a `platforms.csv`, the two original platforms (Mainframe, Ab Initio) are used.

## Search table

Each platform view has one **Search table** box:

- It searches the platform's tables (the `table_types` in `platforms.csv`): Teradata on Mainframe, Hive tables and HDFS paths on Ab Initio, Snowflake on Airflow, and so on.
- Matches appear as you type (any part of the name, case-insensitive; exact and prefix matches are listed first). Each match shows the job that **loads** the table and that job's last-run status, plus a warning if the table is impacted by an upstream failure.
- Picking a table shows its lineage: upstream (the load job, its source files/tables and the jobs before them) and downstream (jobs that read it). It also opens the table's details.
- Use the arrow keys and Enter to pick a match, or Esc to close the list.

## Lineage levels

The **Lineage** tab has four views (toolbar buttons):

| View | Shows |
|---|---|
| **Jobs** | Job-to-job dependencies |
| **Tables** | Table-level lineage: table → table, with the loading job on each arrow (a red arrow means that job failed) |
| **Jobs + tables** | Jobs and every table or file they read and write |
| **Databases** | Database-level lineage: table schemas (`FINANCE_DB`, `ANALYTICS.FINANCE`), HDFS/landing zones (`/data/raw`), mainframe qualifiers (`PROD.CARDS`) and URL sources (`s3://acme-lake`, `salesforce`), connected by the jobs between them. Click a database to see its tables and flows |

**Column-level lineage:** click a table, then one of its columns, or use **Column search**. The graph traces
the column through every job that maps it, upstream and downstream, with each job's transformation. Click any
column to trace it in turn.

**Column search:** switch the search box to **Column** and type a column name, for example `CUSTOMER_ID`. The results list every table
that has the column, with its database, data type, the job that loads it (last run and SLA status) and the jobs
that read it, plus a button for its column lineage.

## SLA tracking

The **SLA tracking** tab lists every job with an expected completion time, worst first:
Late, Completed late, At risk, On track and Met. For each job it shows how late it is, why, and which
failed or running upstream jobs are blocking it. SLA status also appears in job details, on the graph
(⏰ marks late jobs) and in the summary cards. The rules are in [`JOB_LINEAGE_DEMO_DATA.md`](JOB_LINEAGE_DEMO_DATA.md#sla-tracking).

## SRE features (scoped to the selected platform)

- Summary cards: number of jobs or graphs, tables loaded, failed and running jobs, and how many jobs are impacted downstream
- **Failed jobs banner**: one click shows a failure's *blast radius*, meaning every downstream job and table, with how many levels down it is, its owner and its next scheduled run
- **Upstream issues**: for any job, the failed or still-running jobs upstream of it (answers "why is my job / table late?")
- **Jobs only** view (job-to-job dependencies) or **Jobs + datasets** view (shows the tables and files)
- Click a table to see which job loads it ("Loaded by") and which jobs read it
- Focus on any job or table, follow it upstream, downstream or both, and limit the depth
- Link to mainframe job details (Mainframe platform)

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/job-lineage/platforms` | The configured platforms (id, URL key, name, labels, table types, color) with a summary: jobs, failed, running, SLA late |
| GET | `/api/v1/job-lineage/graph?platform=&focus=&direction=&depth=` | One platform's nodes, edges and summary. `platform` is required: a `platform_id` such as `MAINFRAME` or `AIRFLOW_SNOWFLAKE`. `focus` is a node id such as `job:12` or `dataset:FINANCE_DB.GL_POSTINGS`. `direction` is `upstream`, `downstream` or `both`. `depth` counts job levels. |
| GET | `/api/v1/job-lineage/tables?platform=&q=&limit=` | Search the platform's tables (its `table_types`) by part of the name. Each result includes `loaded_by` and `read_by` jobs with their run status. |
| GET | `/api/v1/job-lineage/sla?platform=` | SLA status of every job with an expected completion time, worst first, with `blocked_by` |
| GET | `/api/v1/job-lineage/columns?platform=&q=&exact=` | Column search: every table with a matching column, its database, type, `loaded_by` / `read_by` jobs (run and SLA status) |
| GET | `/api/v1/job-lineage/table-columns?platform=&dataset=` | Columns of one table, with counts of source and target columns |
| GET | `/api/v1/job-lineage/column-lineage?platform=&column=&direction=&depth=` | Column-level lineage; `column` is `<dataset id>::<COLUMN>`, for example `dataset:CARDS_DB.CARD_TRANSACTIONS::CUSTOMER_ID` |
| GET | `/api/v1/job-lineage/impact?platform=&node=job:12` | Downstream blast radius and upstream failing or running jobs, within the platform |
| POST | `/api/v1/job-lineage/sync` | Syncs every configured platform into the catalog. Returns `{source, platforms: {<platform_id>: stats}, jobs_synced}` |

All platforms are stored in the shared `jobs` / `job_files` tables, keyed by
`source_system` (the `platform_id`). Each job's latest run is stored
in `job_executions`. SLAs are in `job_sla`, table columns in `dataset_columns`, and
column mappings in `column_lineage`. The database creates these new tables on startup.

## Demo / no production access: CSV input files

`POST /job-lineage/sync` reads `platforms.csv` and each platform's folder of CSV files from `demo_data/lineage/` (or `LINEAGE_DATA_DIR`) when they exist.
A ready-made demo set is included. Columns and rules are in [`JOB_LINEAGE_DEMO_DATA.md`](JOB_LINEAGE_DEMO_DATA.md).
Without the files, the sync uses the built-in sample data.

## Connecting real sources

For production, write a connector per platform:

1. Implement `BaseLineageConnector` (`src/connectors/base_lineage.py`): `get_jobs()`,
   `get_job_details(name)` (owner, schedule, last run and status, `expected_completion`, ...)
   and `get_job_datasets(name)` (`dataset_name`, `direction`, `dataset_type`, `port`).
   `get_table_columns()` and `get_job_column_lineage(name)` are optional.
   `CsvLineageConnector` (`src/connectors/lineage_files.py`) is the reference implementation.
2. Sync it with `LineageSyncService(db, "<platform_id>", connector).sync_all()`
   (`src/catalog/services/lineage_sync.py`), for example from `sync_job_lineage` in
   `src/api/routes/job_lineage.py`.

Typical sources: z/OSMF, JCL DD parsing or CA-7/Control-M exports (Mainframe); Metadata Hub or
Control>Center (Ab Initio); the Informatica repository; the Airflow REST API and dbt `manifest.json`;
DataStage `istool` exports. The rest of the UI (lineage, SLA, columns, impact) works unchanged.

## Try it locally

```bash
DATABASE_URL=sqlite:///./catalog_dev.db uvicorn src.api.main:app --port 8000
curl -X POST localhost:8000/api/v1/job-lineage/sync
cd frontend && npm start   # open http://localhost:3000/job-lineage
```
