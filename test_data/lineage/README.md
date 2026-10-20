# Job Lineage test input files

Test inputs for the CSV lineage loader, next to the demo set in
[`demo_data/lineage/`](../../demo_data/lineage/). The format is described in
[`docs/JOB_LINEAGE_DEMO_DATA.md`](../../docs/JOB_LINEAGE_DEMO_DATA.md).
`tests/test_lineage_test_data.py` runs every file here: `pytest tests/test_lineage_test_data.py`.

## `valid/`: edge cases that must load

Load it in the UI with `LINEAGE_DATA_DIR=test_data/lineage/valid`, then **Sync job metadata**
(use a fresh database).

| Platform | Edge cases |
|---|---|
| Mainframe → Teradata | `INOUT` GDG; absolute ISO times; `23:59` clock SLA; lower-case `success` and blank status; lower-case dataset names that still link; lower-case `dataset_type`; quoted text with commas and `""`; job with no datasets; UTF-8 BOM and `€` in `table_columns.csv`; one target column from three sources |
| Ab Initio → Hadoop | `graphs.csv` naming; HDFS paths match exactly (`/DATA/RAW/EVENTS` is **not** `/data/raw/events`); Hive names case-insensitive; SLA `MET` and `COMPLETED_LATE`; `MONTHLY` |
| Informatica → Oracle | Only the two required files; `INOUT` upsert; ` failed ` with spaces; never-run job with blank scheduler; job that only reads |
| Airflow → Snowflake | `s3://` and `salesforce://` names match exactly; Unicode description; `WEEKLY`; job writing only to an API (not a load job) |
| DataStage → DB2 | Column lineage within one `INOUT` table; `00:00` clock SLA; `MONTHLY` success 20 days ago still meets the SLA; blank `duration_seconds` |
| SSIS → SQL Server | 6th platform from files only: lower-case `platform_id`, mixed-case folder, blank labels and color (defaults), two `table_types` with spaces and a trailing `;` |

## `invalid/`: one broken rule per folder

Each folder is a complete data set (`platforms.csv` + `test/`) with one mistake.
`expected_error.txt` holds the text the sync error must contain.

| Case | Expected error |
|---|---|
| `01_platforms_missing_column` | missing column(s) table_types |
| `02_platforms_no_rows` | no platforms defined |
| `03_platforms_bad_id` | line 2: platform_id '1-BAD' must be letters, digits or _ |
| `04_platforms_bad_folder` | line 2: folder 'my folder' must be lower-case letters, digits, - or _ |
| `05_platforms_duplicate_id` | line 3: duplicate platform_id 'TEST_PLATFORM' |
| `06_platforms_duplicate_folder` | line 3: duplicate folder 'test' |
| `07_platforms_empty_name` | line 2: name is empty |
| `08_platforms_empty_table_types` | line 2: table_types is empty |
| `09_platforms_bad_color` | line 2: color 'red' must be a hex color like #c2410c |
| `10_platforms_folder_not_found` | no jobs file (expected jobs.csv) |
| `11_jobs_missing_column` | missing column(s) last_run_status |
| `12_jobs_empty_name` | line 3: job_name is empty |
| `13_jobs_duplicate_name` | line 4: duplicate job_name 'JOB_A' |
| `14_jobs_bad_last_run` | line 2: invalid time 'yesterday' |
| `15_jobs_bad_next_run_unit` | line 2: invalid time '+3w' |
| `16_jobs_bad_clock_time` | line 2: invalid time '25:00' (HH:MM must be 00:00-23:59) |
| `17_jobs_bad_status` | line 3: last_run_status 'ABENDED' must be one of SUCCESS, FAILED, RUNNING |
| `18_jobs_bad_duration` | line 2: duration_seconds must be a number |
| `19_jobs_negative_duration` | line 2: duration_seconds must be a number |
| `20_jobs_file_missing` | no jobs file (expected jobs.csv) |
| `21_datasets_file_missing` | job_datasets.csv: file not found |
| `22_datasets_missing_column` | missing column(s) dataset_type |
| `23_datasets_unknown_job` | line 3: job_name 'JOB_C' is not in test/jobs.csv |
| `24_datasets_empty_name` | line 2: dataset_name is empty |
| `25_datasets_bad_direction` | line 2: direction 'WRITE' must be one of INPUT, OUTPUT, INOUT |
| `26_columns_missing_column` | missing column(s) column_name |
| `27_columns_empty_value` | line 3: dataset_name and column_name are required |
| `28_columns_duplicate_case_insensitive` | line 3: duplicate column 'stg.a.id' |
| `29_lineage_missing_column` | missing column(s) target_column |
| `30_lineage_unknown_job` | line 2: job_name 'JOB_Z' is unknown |
| `31_lineage_empty_values` | line 2: empty source_column, target_column |
| `32_lineage_source_not_read` | line 2: JOB_B does not read '/in/a.csv' |
| `33_lineage_target_not_written` | line 2: JOB_B does not write 'STG.A' |

To add a case, copy a folder, break one rule, and write the expected error text.
