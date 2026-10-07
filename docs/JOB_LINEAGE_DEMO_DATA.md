# Job Lineage demo input files

Without production access, the Job Lineage UI can run from **four CSV files** that
describe your jobs and the tables they load. You can edit them in Excel or any text
editor.

```
demo_data/lineage/
├── mainframe/
│   ├── jobs.csv             one row per mainframe job
│   └── job_datasets.csv     one row per file/table a mainframe job reads or writes
└── abinitio/
    ├── graphs.csv           one row per Ab Initio graph
    └── graph_datasets.csv   one row per file/table a graph reads or writes
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
| `duration_seconds` | no | `420` | Whole number |

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

## 4. `abinitio/graph_datasets.csv`: what each graph reads and writes

| Column | Required | Example | Notes |
|---|---|---|---|
| `graph_name` | **yes** | `bld_fraud_features.mp` | Must exist in `abinitio/graphs.csv` |
| `dataset_name` | **yes** | `risk_feat.fraud_features` | Hive `db.table` or HDFS path |
| `direction` | **yes** | `INPUT` | `INPUT`, `OUTPUT` or `INOUT` |
| `dataset_type` | **yes** | `HIVE` | `HIVE` or `HDFS` |
| `port` | no | `in0` | Graph port name |

## Times

Set `last_run` and `next_run` either way:

- **Relative to sync time (recommended for demos):** `-9h` (9 hours ago), `+15h`, `-2d`, `+30m`. With these, the demo always looks current on event day.
- **Absolute:** ISO format, for example `2026-10-07T01:00`.

## Loading the files

1. Edit the files in `demo_data/lineage/`. To keep the files somewhere else, set `LINEAGE_DATA_DIR=/path/to/folder` in `.env` or the environment.
2. Start the API and open the UI (see `docs/JOB_LINEAGE.md` → *Try it locally*).
3. Click **Sync job metadata** on the Job Lineage page, or run `curl -X POST localhost:8000/api/v1/job-lineage/sync`.

All four files are needed. If the folder has no input files, the sync falls back to the built-in sample data.

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

Good tables to search during the demo:

- Mainframe → Teradata: `CARD_TRANSACTIONS`, `GL_POSTINGS`, `COLLECTIONS_QUEUE`
- Ab Initio → Hadoop: `fraud_scores`, `txn_enriched`, `loan_funnel`
