/**
 * Turn the job/dataset lineage graph from the API into the different views:
 * jobs only, tables only, databases, and column lineage.
 */
import {
  ColumnLineageGraph,
  LineageDatasetNode,
  LineageEdge,
  LineageJobNode,
  LineageNode,
} from '../services/api';

export type LineageView = 'jobs' | 'tables' | 'datasets' | 'databases';

export interface GraphView {
  nodes: LineageNode[];
  edges: LineageEdge[];
}

const isJob = (n: LineageNode): n is LineageJobNode => n.type === 'job';

/** Text for an arrow that stands for one or more jobs. */
const jobsLabel = (names: string[]) =>
  names.length <= 2 ? names.join(', ') : `${names[0]} +${names.length - 1} jobs`;

/** Job-to-job view: connect each job that writes a dataset to each job that reads it. */
export const collapseToJobs = (nodes: LineageNode[], edges: LineageEdge[]): GraphView => {
  const jobIds = new Set(nodes.filter(isJob).map((n) => n.id));
  const writers = new Map<string, string[]>();
  edges.forEach((e) => {
    if (jobIds.has(e.source)) writers.set(e.target, [...(writers.get(e.target) || []), e.source]);
  });
  const jobEdges = new Map<string, LineageEdge>();
  edges.forEach((e) => {
    if (!jobIds.has(e.target)) return;
    (writers.get(e.source) || []).forEach((writer) => {
      const id = `${writer}=>${e.target}`;
      if (writer !== e.target && !jobEdges.has(id)) {
        jobEdges.set(id, { id, source: writer, target: e.target });
      }
    });
  });
  return { nodes: nodes.filter((n) => jobIds.has(n.id)), edges: Array.from(jobEdges.values()) };
};

/** Table-to-table view: each job becomes arrows from its input to its output tables. */
export const collapseToTables = (nodes: LineageNode[], edges: LineageEdge[]): GraphView => {
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const jobs = nodes.filter(isJob);
  const tableEdges = new Map<string, { source: string; target: string; jobs: LineageJobNode[] }>();
  jobs.forEach((job) => {
    const inputs = edges.filter((e) => e.target === job.id).map((e) => e.source);
    const outputs = edges.filter((e) => e.source === job.id).map((e) => e.target);
    inputs.forEach((source) =>
      outputs.forEach((target) => {
        if (source === target) return;
        const id = `${source}=>${target}`;
        const entry = tableEdges.get(id) || { source, target, jobs: [] };
        entry.jobs.push(job);
        tableEdges.set(id, entry);
      })
    );
  });
  return {
    nodes: nodes.filter((n) => n.type === 'dataset' && byId.has(n.id)),
    edges: Array.from(tableEdges.entries()).map(([id, e]) => ({
      id,
      source: e.source,
      target: e.target,
      label: jobsLabel(e.jobs.map((j) => j.name)),
      status: e.jobs.some((j) => j.run_status === 'FAILED') ? 'FAILED' : undefined,
    })),
  };
};

export const databaseNodeId = (database: string) => `db:${database}`;

export interface DatabaseView extends GraphView {
  /** database node id -> the tables in it */
  members: Map<string, LineageDatasetNode[]>;
  /** dataset node id -> database node id */
  databaseOf: Map<string, string>;
}

/** Database-to-database view, built from the table view. */
export const collapseToDatabases = (nodes: LineageNode[], edges: LineageEdge[]): DatabaseView => {
  const tables = collapseToTables(nodes, edges);
  const members = new Map<string, LineageDatasetNode[]>();
  const databaseOf = new Map<string, string>();
  tables.nodes.forEach((n) => {
    if (n.type !== 'dataset') return;
    const id = databaseNodeId(n.database);
    members.set(id, [...(members.get(id) || []), n]);
    databaseOf.set(n.id, id);
  });

  const dbNodes: LineageDatasetNode[] = Array.from(members.entries()).map(([id, list]) => ({
    id,
    type: 'dataset',
    name: list[0].database,
    subtitle: `${list.length} table${list.length > 1 ? 's' : ''}`,
    dataset_type: 'DATABASE',
    platform: list[0].platform,
    database: list[0].database,
    impacted: list.some((t) => t.impacted),
    impacted_by: Array.from(new Set(list.flatMap((t) => t.impacted_by))),
  }));

  const dbEdges = new Map<string, { source: string; target: string; jobs: Set<string>; failed: boolean }>();
  tables.edges.forEach((e) => {
    const source = databaseOf.get(e.source)!;
    const target = databaseOf.get(e.target)!;
    if (source === target) return;
    const id = `${source}=>${target}`;
    const entry = dbEdges.get(id) || { source, target, jobs: new Set<string>(), failed: false };
    (e.label || '').split(', ').forEach((name) => name && entry.jobs.add(name));
    entry.failed = entry.failed || e.status === 'FAILED';
    dbEdges.set(id, entry);
  });

  return {
    nodes: dbNodes,
    edges: Array.from(dbEdges.entries()).map(([id, e]) => ({
      id,
      source: e.source,
      target: e.target,
      label: e.jobs.size === 1 ? Array.from(e.jobs)[0] : `${e.jobs.size} jobs`,
      status: e.failed ? 'FAILED' : undefined,
    })),
    members,
    databaseOf,
  };
};

/** Column lineage as graph nodes (column name over table name) and job-labelled arrows. */
export const columnLineageToGraph = (lineage: ColumnLineageGraph): GraphView => ({
  nodes: lineage.nodes.map(
    (c): LineageDatasetNode => ({
      id: c.id,
      type: 'dataset',
      name: c.column,
      subtitle: c.dataset_name,
      dataset_type: c.dataset_type,
      platform: c.platform || 'MAINFRAME',
      database: c.database,
      impacted: c.impacted,
      impacted_by: c.impacted_by,
    })
  ),
  edges: Array.from(
    lineage.edges
      .reduce((merged, e) => {
        // Two jobs can map the same pair of columns; show one arrow with both names.
        const id = `${e.source}=>${e.target}`;
        const prev = merged.get(id);
        merged.set(id, {
          id,
          source: e.source,
          target: e.target,
          label: prev ? `${prev.label}, ${e.job_name}` : e.job_name,
          status: prev?.status === 'FAILED' || e.run_status === 'FAILED' ? 'FAILED' : undefined,
        });
        return merged;
      }, new Map<string, LineageEdge>())
      .values()
  ),
});
