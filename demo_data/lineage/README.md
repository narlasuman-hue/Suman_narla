# Job Lineage demo input files

These CSV files feed the Job Lineage UI when there is no production access.
**Sync job metadata** on the Job Lineage page loads them.

- `platforms.csv`: the platforms the UI offers (one row each: id, folder, name, labels, table types, color)
- `mainframe/`: Mainframe jobs → Teradata tables (`jobs.csv`, `job_datasets.csv`)
- `abinitio/`: Ab Initio graphs → Hadoop tables (`graphs.csv`, `graph_datasets.csv`)
- `informatica/`, `airflow/`, `datastage/`: Informatica → Oracle, Airflow → Snowflake, DataStage → DB2 (`jobs.csv`, `job_datasets.csv`)
- `*/table_columns.csv`, `*/column_lineage.csv` (optional): table columns and column-level lineage
- `expected_completion` column in the jobs file (optional): SLA tracking

**Add a platform:** add a row to `platforms.csv` and a folder with `jobs.csv` and
`job_datasets.csv`, then sync. No code changes.

Column reference, rules and the demo story: [`docs/JOB_LINEAGE_DEMO_DATA.md`](../../docs/JOB_LINEAGE_DEMO_DATA.md).
