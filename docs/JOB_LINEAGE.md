# Job Lineage: Mainframe → Teradata and Ab Initio → Hadoop

The **Job Lineage** page (`/job-lineage` in the UI) covers two **independent platforms**.
The user picks one at the top of the page and sees only that platform's lineage:

| Platform | Jobs | Tables they load | URL |
|---|---|---|---|
| **Mainframe → Teradata** | Mainframe JCL jobs, including BTEQ / FastLoad / MultiLoad / TPT load jobs | Teradata tables, loaded from mainframe datasets | `/job-lineage?platform=mainframe` |
| **Ab Initio → Hadoop** | Ab Initio graphs | Hadoop tables (Hive / HDFS) | `/job-lineage?platform=abinitio` |

The selected platform is kept in the URL, so you can share a link to one platform's view.

## Search table

Each platform view has one **Search table** box:

- **Mainframe → Teradata** searches Teradata tables. **Ab Initio → Hadoop** searches Hive tables and HDFS paths.
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
| **Databases** | Database-level lineage: Teradata/Hive databases, HDFS zones (`/data/raw`) and mainframe qualifiers (`PROD.CARDS`), connected by the jobs between them. Click a database to see its tables and flows |

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
- Link to mainframe job details

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/job-lineage/graph?platform=&focus=&direction=&depth=` | One platform's nodes, edges and summary. `platform` is required: `MAINFRAME` or `HADOOP_ABINITIO`. `focus` is a node id such as `job:12` or `dataset:FINANCE_DB.GL_POSTINGS`. `direction` is `upstream`, `downstream` or `both`. `depth` counts job levels. |
| GET | `/api/v1/job-lineage/tables?platform=&q=&limit=` | Search the platform's tables (Teradata for `MAINFRAME`, Hive/HDFS for `HADOOP_ABINITIO`) by part of the name. Each result includes `loaded_by` and `read_by` jobs with their run status. |
| GET | `/api/v1/job-lineage/sla?platform=` | SLA status of every job with an expected completion time, worst first, with `blocked_by` |
| GET | `/api/v1/job-lineage/columns?platform=&q=&exact=` | Column search: every table with a matching column, its database, type, `loaded_by` / `read_by` jobs (run and SLA status) |
| GET | `/api/v1/job-lineage/table-columns?platform=&dataset=` | Columns of one table, with counts of source and target columns |
| GET | `/api/v1/job-lineage/column-lineage?platform=&column=&direction=&depth=` | Column-level lineage; `column` is `<dataset id>::<COLUMN>`, for example `dataset:CARDS_DB.CARD_TRANSACTIONS::CUSTOMER_ID` |
| GET | `/api/v1/job-lineage/impact?platform=&node=job:12` | Downstream blast radius and upstream failing or running jobs, within the platform |
| POST | `/api/v1/job-lineage/sync` | Syncs mainframe jobs and Ab Initio graphs into the catalog |

Both platforms are stored in the shared `jobs` / `job_files` tables, keyed by
`source_system` (`MAINFRAME`, `HADOOP_ABINITIO`). Each job's latest run is stored
in `job_executions`. SLAs are in `job_sla`, table columns in `dataset_columns`, and
column mappings in `column_lineage`. The database creates these new tables on startup.

## Demo / no production access: CSV input files

`POST /job-lineage/sync` reads four CSV files from `demo_data/lineage/` (or `LINEAGE_DATA_DIR`) when they exist.
A ready-made demo set is included. Columns and rules are in [`JOB_LINEAGE_DEMO_DATA.md`](JOB_LINEAGE_DEMO_DATA.md).
Without the files, the sync uses the built-in sample data.

## Connecting real sources

For production, implement the connectors:

Connectors can also provide `expected_completion` in the job details, plus the optional
`get_table_columns()` and `get_job_column_lineage()` / `get_graph_column_lineage()` methods.

- `src/connectors/mainframe.py` → implement `BaseMainframeConnector`, for example with z/OSMF REST, JCL DD parsing, or CA-7/Control-M/OPC exports. Teradata targets are files with `dataset_type="TERADATA"`.
- `src/connectors/abinitio.py` → implement `BaseAbInitioConnector`, for example with Metadata Hub, `air` output, or Control>Center exports. Hadoop targets are datasets with `dataset_type` `HIVE` or `HDFS`.

Then swap the connectors in `src/api/routes/job_lineage.py` (`sync_job_lineage`).

## Try it locally

```bash
DATABASE_URL=sqlite:///./catalog_dev.db uvicorn src.api.main:app --port 8000
curl -X POST localhost:8000/api/v1/job-lineage/sync
cd frontend && npm start   # open http://localhost:3000/job-lineage?platform=mainframe
```
