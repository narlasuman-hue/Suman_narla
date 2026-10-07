# Job Lineage: Mainframe/Teradata and Hadoop Ab Initio

The **Job Lineage** page (`/job-lineage` in the UI) shows end-to-end lineage across:

- **Mainframe JCL jobs**, including Teradata load jobs (BTEQ / FastLoad / MultiLoad / TPT)
- **Ab Initio graphs** that run on the Hadoop cluster
- the **datasets** between them: mainframe DSNs, Teradata tables, HDFS paths, Hive tables

Jobs on different platforms are linked through datasets that share a name. For
example, a mainframe FastLoad job writes `FINANCE_DB.GL_POSTINGS` and an Ab Initio
graph reads it. Dataset names are matched case-insensitively, except HDFS paths,
which are case-sensitive.

## SRE features

- Summary cards: job counts per platform, failed and running jobs, and how many jobs are impacted downstream
- **Failed jobs banner**: one click shows a failure's *blast radius*, meaning every downstream job and dataset on any platform, with how many levels down it is, its owner and its next scheduled run
- **Upstream issues**: for any job, the failed or still-running jobs upstream of it (answers "why is my job late?")
- **Jobs only** view (job-to-job dependencies) or **Jobs + datasets** view
- Focus on any job or dataset, follow it upstream, downstream or both, and limit the depth
- Platform filter, search box, and a link to mainframe job details

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/job-lineage/graph?platform=&focus=&direction=&depth=` | Nodes, edges and summary. `platform` is `MAINFRAME` or `HADOOP_ABINITIO`. `focus` is a node id such as `job:12` or `dataset:FINANCE_DB.GL_POSTINGS`. `direction` is `upstream`, `downstream` or `both`. `depth` counts job levels. |
| GET | `/api/v1/job-lineage/impact?node=job:12` | Downstream blast radius and upstream failing or running jobs |
| POST | `/api/v1/job-lineage/sync` | Syncs mainframe jobs and Ab Initio graphs into the catalog |

Both platforms are stored in the shared `jobs` / `job_files` tables, keyed by
`source_system` (`MAINFRAME`, `HADOOP_ABINITIO`). Each job's latest run is stored
in `job_executions`.

## Connecting real sources

The sync uses mock connectors with sample data until you connect real ones:

- `src/connectors/mainframe.py` → implement `BaseMainframeConnector`, for example with z/OSMF REST, JCL DD parsing, or CA-7/Control-M/OPC exports. Teradata targets are files with `dataset_type="TERADATA"`.
- `src/connectors/abinitio.py` → implement `BaseAbInitioConnector`, for example with Metadata Hub, `air` output, or Control>Center exports.

Then swap the connectors in `src/api/routes/job_lineage.py` (`sync_job_lineage`).

## Try it locally

```bash
DATABASE_URL=sqlite:///./catalog_dev.db uvicorn src.api.main:app --port 8000
curl -X POST localhost:8000/api/v1/job-lineage/sync
cd frontend && npm start   # open http://localhost:3000/job-lineage
```
