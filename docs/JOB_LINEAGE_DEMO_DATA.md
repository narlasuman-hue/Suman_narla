# Job Lineage demo input files

Without production access, the Job Lineage UI can run from **CSV files** that
describe your jobs and the tables they load. You can edit them in Excel or any text
editor. There are four required files and four optional ones, which add column-level
lineage and column search.

```
demo_data/lineage/
├── mainframe/
│   ├── jobs.csv             one row per mainframe job (incl. SLA expected completion)
│   ├── job_datasets.csv     one row per file/table a mainframe job reads or writes
│   ├── table_columns.csv    optional: the columns of each file/table
│   └── column_lineage.csv   optional: source column → target column, per job
└── abinitio/
    ├── graphs.csv           one row per Ab Initio graph (incl. SLA expected completion)
    ├── graph_datasets.csv   one row per file/table a graph reads or writes
    ├── table_columns.csv    optional: the columns of each table/path
    └── column_lineage.csv   optional: source column → target column, per graph
```

The repo already contains a filled-in demo set: 13 mainframe jobs and 11 Ab Initio
graphs for a banking scenario, with failures, a running job and downstream impact
on each platform. You can use the files as they are, or edit them to match your
own jobs.

## How the lineage is built

Lineage comes from **matching dataset names**:

- If one job **writes** (`OUTPUT`) a dataset or table and another job **reads** (`INPUT`) the same name, the two jobs are linked.
- Names match case-insensitively (`FINANCE_DB.GL_POSTINGS` = `finance_db.gl_postings`).
- HDFS paths (starting with `/`) must match exactly.

```
PROD.PAYROLL.GL.EXTRACT ──▶ TDPAYLD1 ──▶ FIN_STG.PAYROLL_GL_STG ──▶ TDGLPST1 ──▶ FINANCE_DB.GL_POSTINGS
   (written by PAYEXT01)    (FastLoad)        (Teradata)              (BTEQ)          (Teradata)
```

If a job fails, everything downstream of it through these links is marked as
**impacted**.

## 1. `mainframe/jobs.csv`: Mainframe → Teradata jobs

| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` | **yes** | `TDPAYLD1` | JCL job name; must be unique |
| `scheduler_system` | **yes** (may be blank) | `CA-7` | CA-7, Control-M, OPC/TWS… |
| `schedule_name` | **yes** (may be blank) | `PAYROLL-DAILY` | Scheduler schedule or application name |
| `last_run_status` | **yes** | `FAILED` | `SUCCESS`, `FAILED` or `RUNNING` (blank = SUCCESS) |
| `owner` | no | `FINANCE_DW_TEAM` | Shown in the details and blast-radius lists |
| `description` | no | `FastLoad payroll GL extract…` | |
| `job_class` | no | `T` | JES job class |
| `frequency` | no | `DAILY` | |
| `last_run` | no | `-9h` | When the last run started (see **Times** below) |
| `next_run` | no | `+15h` | Next scheduled run |
| `return_code` | no | `ABEND S0C7` / `CC 0008` | Shown as the error when the job failed |
| `duration_seconds` | no | `420` | Whole number; used to work out when the run completed for SLA |
| `expected_completion` | no | `06:00` / `-8h` | **SLA**: when the job's current run should be complete. Blank = SLA not tracked |

A job counts as a **Teradata load job** when it writes a dataset whose
`dataset_type` is `TERADATA`.

## 2. `mainframe/job_datasets.csv`: what each mainframe job reads and writes

| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` | **yes** | `TDPAYLD1` | Must exist in `mainframe/jobs.csv` |
| `dataset_name` | **yes** | `FIN_STG.PAYROLL_GL_STG` | Mainframe DSN or Teradata `DATABASE.TABLE` |
| `direction` | **yes** | `OUTPUT` | `INPUT`, `OUTPUT` or `INOUT` |
| `dataset_type` | **yes** | `TERADATA` | `TERADATA` for Teradata tables; `PS`, `VSAM`, `GDG`, `PDS`… for mainframe files |
| `dd_name` | no | `TDTGT` | DD statement name |
| `disposition` | no | `SHR` | |

## 3. `abinitio/graphs.csv`: Ab Initio → Hadoop graphs

| Column | Required | Example | Notes |
|---|---|---|---|
| `graph_name` | **yes** | `bld_cards_txn_enriched.mp` | Must be unique |
| `scheduler_system` | **yes** (may be blank) | `Control-M` | Control-M, Autosys… |
| `schedule_name` | **yes** (may be blank) | `HDP-CARDS-HOURLY` | |
| `last_run_status` | **yes** | `FAILED` | `SUCCESS`, `FAILED` or `RUNNING` |
| `owner` | no | `HADOOP_CARDS_TEAM` | |
| `project` | no | `cards_curated` | Ab Initio project/sandbox |
| `description` | no | | |
| `frequency` | no | `HOURLY` | |
| `last_run` | no | `-2h` | |
| `next_run` | no | `+10m` | |
| `duration_seconds` | no | `1340` | |
| `error_message` | no | `Phase 3: Join 'join_cust' ran out of memory…` | Shown when the graph failed |
| `expected_completion` | no | `06:00` / `-1h` | **SLA**: when the graph's current run should be complete |

## 4. `abinitio/graph_datasets.csv`: what each graph reads and writes

| Column | Required | Example | Notes |
|---|---|---|---|
| `graph_name` | **yes** | `bld_fraud_features.mp` | Must exist in `abinitio/graphs.csv` |
| `dataset_name` | **yes** | `risk_feat.fraud_features` | Hive `db.table` or HDFS path |
| `direction` | **yes** | `INPUT` | `INPUT`, `OUTPUT` or `INOUT` |
| `dataset_type` | **yes** | `HIVE` | `HIVE` or `HDFS` |
| `port` | no | `in0` | Graph port name |

## 5. `table_columns.csv` (optional, in `mainframe/` and `abinitio/`): columns of each table

| Column | Required | Example | Notes |
|---|---|---|---|
| `dataset_name` | **yes** | `CARDS_DB.CARD_TRANSACTIONS` | Same name as in the datasets file |
| `column_name` | **yes** | `CUSTOMER_ID` | Unique per table (case-insensitive) |
| `data_type` | no | `VARCHAR(12)` / `PIC X(12)` / `string` | |
| `description` | no | `Customer key` | |

Rows are shown in file order in the table's **Columns** list. **Column search** uses
this file and the column lineage file.

## 6. `column_lineage.csv` (optional, in `mainframe/` and `abinitio/`): column-level lineage

One row per source column → target column a job maps. For mainframe, use `job_name`; for
Ab Initio, use `graph_name`.

| Column | Required | Example | Notes |
|---|---|---|---|
| `job_name` / `graph_name` | **yes** | `TDCRDPST` | Must exist in the jobs/graphs file |
| `source_dataset` | **yes** | `CUSTOMER_DB.CUSTOMER_MASTER` | Must be an `INPUT` of that job in the datasets file |
| `source_column` | **yes** | `CUSTOMER_ID` | |
| `target_dataset` | **yes** | `CARDS_DB.CARD_TRANSACTIONS` | Must be an `OUTPUT` of that job in the datasets file |
| `target_column` | **yes** | `CUSTOMER_ID` | |
| `transformation` | no | `Lookup on CARD_NUMBER` / `SUM(AMOUNT)` | Shown in column lineage |

A target column derived from several sources gets one row per source, for example
`PAY_AMOUNT` from both `HOURS_WORKED` and `PAY_GRADE`.

## SLA tracking

`expected_completion` is the time the job's **current run** should be complete. Each job gets one of these statuses:

| Status | Meaning |
|---|---|
| **Late** | Past the expected time and the run has not completed (failed, still running, or not started because an upstream job failed) |
| **Completed late** | Completed, but after the expected time (needs `duration_seconds`) |
| **At risk** | Not yet due, but the job failed, is blocked by an upstream failure, or is due within 30 minutes and not completed |
| **On track** | Not yet due and nothing is blocking it |
| **Met** | Completed by the expected time |

A completed run counts only if it finished within one schedule period (by `frequency`:
HOURLY = 1 hour, DAILY = 1 day, WEEKLY, MONTHLY) before the expected time. An older
success belongs to the previous cycle. The SLA tab also shows **blocked by**: the
failed or still-running jobs upstream, which is usually the root cause.

## Times

Set `last_run` and `next_run` either way:

- **Relative to sync time (recommended for demos):** `-9h` (9 hours ago), `+15h`, `-2d`, `+30m`. With these, the demo always looks current on event day.
- **Absolute:** ISO format, for example `2026-10-07T01:00`.
- **Clock time** (`expected_completion` only): `06:00` means today at 06:00 UTC.

## Loading the files

1. Edit the files in `demo_data/lineage/`. To keep the files somewhere else, set `LINEAGE_DATA_DIR=/path/to/folder` in `.env` or the environment.
2. Start the API and open the UI (see `docs/JOB_LINEAGE.md` → *Try it locally*).
3. Click **Sync job metadata** on the Job Lineage page, or run `curl -X POST localhost:8000/api/v1/job-lineage/sync`.

The four jobs/datasets files are required. `table_columns.csv` and `column_lineage.csv` are optional; without them, column search and column lineage are empty. If the folder has no input files, the sync falls back to the built-in sample data.

If a file has a mistake, the sync stops and shows the file, line and problem, for example:

```
Invalid lineage input file: demo_data/lineage/mainframe/job_datasets.csv line 7:
job_name 'TDPAYLD2' is not in mainframe/jobs.csv
```

**Re-syncing:** a job you remove or rename in the files stays in the catalog. For a
clean demo, start with a fresh database, for example by deleting the SQLite file
used by `DATABASE_URL`.

## Story in the shipped demo data

| Platform | Failed job | What it affects downstream (blast radius) | Running |
|---|---|---|---|
| Mainframe → Teradata | `CRDTXN01` (ABEND S0C7) | `TDCRDLD1` → `TDCRDPST` → `TDFRAUD1` (`CARDS_DB.CARD_TRANSACTIONS`, `RISK_DB.FRAUD_ALERTS_DAILY`) | `TDCUSLD1` (TPT load of `CUSTOMER_DB.CUSTOMER_MASTER`) |
| Mainframe → Teradata | `TDLNSLD1` (CC 0008) | `TDLNSRPT` (`RISK_DB.COLLECTIONS_QUEUE`) | |
| Ab Initio → Hadoop | `bld_cards_txn_enriched.mp` (out of memory) | `bld_fraud_features.mp` → `score_fraud_model.mp` → `exp_fraud_alerts.mp`, and `bld_spend_insights.mp` | `ing_web_clickstream.mp` |
| Ab Initio → Hadoop | `bld_loan_funnel.mp` (input record format changed) | Nothing downstream (`analytics.loan_funnel_daily` is a final table) | |

SLA story: on Mainframe → Teradata, `CRDTXN01` and `TDLNSLD1` are **late** (failed); `TDCRDLD1` is **late** because
it is blocked by `CRDTXN01`; `TDGLPST1` **completed 10 minutes late**; four jobs are **at risk**. On Ab Initio →
Hadoop, `bld_cards_txn_enriched.mp` failing makes `bld_fraud_features.mp` late and the fraud scoring graphs at risk.

Good columns to search: `CUSTOMER_ID` (8 Teradata/mainframe tables), `customer_id` (Hive), `amount`, `fraud_score`.

Good tables to search during the demo:

- Mainframe → Teradata: `CARD_TRANSACTIONS`, `GL_POSTINGS`, `COLLECTIONS_QUEUE`
- Ab Initio → Hadoop: `fraud_scores`, `txn_enriched`, `loan_funnel`
