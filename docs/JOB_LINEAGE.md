# Job Lineage: Mainframe → Teradata and Ab Initio → Hadoop

The **Job Lineage** page (`/job-lineage` in the UI) covers two **independent platforms**.
The user picks one at the top of the page and sees only that platform's lineage:

| Platform | Jobs | Tables they load | URL |
|---|---|---|---|
| **Mainframe → Teradata** | Mainframe JCL jobs, including BTEQ / FastLoad / MultiLoad / TPT load jobs | Teradata tables, loaded from mainframe datasets | `/job-lineage?platform=mainframe` |
| **Ab Initio → Hadoop** | Ab Initio graphs | Hadoop tables (Hive / HDFS) | `/job-lineage?platform=abinitio` |

The selected platform is kept in the URL, so you can share a link to one platform's view.

## SRE features (scoped to the selected platform)

- Summary cards: number of jobs or graphs, tables loaded, failed and running jobs, and how many jobs are impacted downstream
- **Failed jobs banner**: one click shows a failure's *blast radius*, meaning every downstream job and table, with how many levels down it is, its owner and its next scheduled run
- **Upstream issues**: for any job, the failed or still-running jobs upstream of it (answers "why is my job / table late?")
- **Jobs only** view (job-to-job dependencies) or **Jobs + datasets** view (shows the tables and files)
- Click a table to see which job loads it ("Loaded by") and which jobs read it
- Focus on any job or table, follow it upstream, downstream or both, and limit the depth
- Search box, and a link to mainframe job details

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/v1/job-lineage/graph?platform=&focus=&direction=&depth=` | One platform's nodes, edges and summary. `platform` is required: `MAINFRAME` or `HADOOP_ABINITIO`. `focus` is a node id such as `job:12` or `dataset:FINANCE_DB.GL_POSTINGS`. `direction` is `upstream`, `downstream` or `both`. `depth` counts job levels. |
| GET | `/api/v1/job-lineage/impact?platform=&node=job:12` | Downstream blast radius and upstream failing or running jobs, within the platform |
| POST | `/api/v1/job-lineage/sync` | Syncs mainframe jobs and Ab Initio graphs into the catalog |

Both platforms are stored in the shared `jobs` / `job_files` tables, keyed by
`source_system` (`MAINFRAME`, `HADOOP_ABINITIO`). Each job's latest run is stored
in `job_executions`.

## Connecting real sources

The sync uses mock connectors with sample data until you connect real ones:

- `src/connectors/mainframe.py` → implement `BaseMainframeConnector`, for example with z/OSMF REST, JCL DD parsing, or CA-7/Control-M/OPC exports. Teradata targets are files with `dataset_type="TERADATA"`.
- `src/connectors/abinitio.py` → implement `BaseAbInitioConnector`, for example with Metadata Hub, `air` output, or Control>Center exports. Hadoop targets are datasets with `dataset_type` `HIVE` or `HDFS`.

Then swap the connectors in `src/api/routes/job_lineage.py` (`sync_job_lineage`).

## Try it locally

```bash
DATABASE_URL=sqlite:///./catalog_dev.db uvicorn src.api.main:app --port 8000
curl -X POST localhost:8000/api/v1/job-lineage/sync
cd frontend && npm start   # open http://localhost:3000/job-lineage?platform=mainframe
```
