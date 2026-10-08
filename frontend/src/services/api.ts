/**
 * API Service - Handles all backend API calls
 */

import axios from 'axios';

const API_BASE_URL = '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error.response?.data || error.message);
    throw error;
  }
);

// ============ Health Check ============

export const healthCheck = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const dbHealthCheck = async () => {
  const response = await apiClient.get('/health/db');
  return response.data;
};

// ============ Databases ============

export interface Database {
  id: number;
  name: string;
  owner?: string;
  description?: string;
  status: string;
  created_at: string;
  last_synced: string;
  table_count?: number;
  view_count?: number;
}

export const getDatabases = async (
  status?: string,
  skip: number = 0,
  limit: number = 50
) => {
  const params = { skip, limit };
  if (status) (params as any).status = status;
  const response = await apiClient.get<Database[]>('/databases', { params });
  return response.data;
};

export const getDatabase = async (id: number) => {
  const response = await apiClient.get<Database>(`/databases/${id}`);
  return response.data;
};

// ============ Tables ============

export interface Table {
  id: number;
  database_id: number;
  name: string;
  type: string;
  status: string;
  description?: string;
  created_at?: string;
  last_accessed?: string;
  row_count?: number;
  size_mb?: number;
  column_count?: number;
}

export interface Column {
  id: number;
  name: string;
  data_type: string;
  nullable: boolean;
  sensitive: boolean;
  description?: string;
  position: number;
}

export const getTables = async (
  database_id?: number,
  status?: string,
  skip: number = 0,
  limit: number = 50
) => {
  const params: any = { skip, limit };
  if (database_id) params.database_id = database_id;
  if (status) params.status = status;
  const response = await apiClient.get<Table[]>('/tables', { params });
  return response.data;
};

export const getTable = async (id: number) => {
  const response = await apiClient.get<Table>(`/tables/${id}`);
  return response.data;
};

export const getTableColumns = async (id: number) => {
  const response = await apiClient.get<Column[]>(`/tables/${id}/columns`);
  return response.data;
};

export const getTableUsage = async (id: number) => {
  const response = await apiClient.get(`/tables/${id}/usage`);
  return response.data;
};

// ============ Lineage ============

export const getUpstreamLineage = async (tableId: number, maxDepth: number = 5) => {
  const response = await apiClient.get(`/lineage/${tableId}/upstream`, {
    params: { max_depth: maxDepth },
  });
  return response.data;
};

export const getDownstreamLineage = async (tableId: number, maxDepth: number = 5) => {
  const response = await apiClient.get(`/lineage/${tableId}/downstream`, {
    params: { max_depth: maxDepth },
  });
  return response.data;
};

export const getFullLineage = async (tableId: number, maxDepth: number = 3) => {
  const response = await apiClient.get(`/lineage/${tableId}/full`, {
    params: { max_depth: maxDepth },
  });
  return response.data;
};

export const extractLineageFromSQL = async (sql: string) => {
  const response = await apiClient.post('/lineage/extract-from-sql', { sql });
  return response.data;
};

// ============ Impact Analysis ============

export const getImpact = async (tableId: number) => {
  const response = await apiClient.get(`/impact/${tableId}`);
  return response.data;
};

export const getDependencies = async (tableId: number) => {
  const response = await apiClient.get(`/dependencies/${tableId}`);
  return response.data;
};

export const checkDropSafety = async (tableId: number) => {
  const response = await apiClient.get(`/drop-safety/${tableId}`);
  return response.data;
};

// ============ Search ============

export const globalSearch = async (
  query: string,
  assetTypes?: string[],
  databaseId?: number,
  limit: number = 100
) => {
  const params: any = { q: query, limit };
  if (assetTypes) params.asset_types = assetTypes;
  if (databaseId) params.database_id = databaseId;
  const response = await apiClient.get('/search', { params });
  return response.data;
};

export const searchTables = async (
  query: string,
  databaseId?: number,
  limit: number = 50
) => {
  const params: any = { q: query, limit };
  if (databaseId) params.database_id = databaseId;
  const response = await apiClient.get('/search/tables', { params });
  return response.data;
};

export const searchColumns = async (
  query: string,
  tableId?: number,
  limit: number = 50
) => {
  const params: any = { q: query, limit };
  if (tableId) params.table_id = tableId;
  const response = await apiClient.get('/search/columns', { params });
  return response.data;
};

export const findSensitiveData = async () => {
  const response = await apiClient.get('/search/sensitive-data');
  return response.data;
};

export const findByOwner = async (owner: string) => {
  const response = await apiClient.get('/search/by-owner', {
    params: { owner },
  });
  return response.data;
};

export const autocomplete = async (
  query: string,
  assetType: string = 'table'
) => {
  const response = await apiClient.get('/search/autocomplete', {
    params: { q: query, asset_type: assetType },
  });
  return response.data;
};

// ============ Lifecycle ============

export const getLifecycleSummary = async () => {
  const response = await apiClient.get('/lifecycle/summary');
  return response.data;
};

export const getUnusedAssets = async (days: number = 90) => {
  const response = await apiClient.get('/lifecycle/unused-assets', {
    params: { days },
  });
  return response.data;
};

export const getDecommissioningCandidates = async (days: number = 180) => {
  const response = await apiClient.get('/lifecycle/decommissioning-candidates', {
    params: { days },
  });
  return response.data;
};

export const deprecateAsset = async (tableId: number, reason?: string) => {
  const response = await apiClient.post(`/lifecycle/assets/${tableId}/deprecate`, {
    reason,
  });
  return response.data;
};

// ============ Reports ============

export const getSummaryReport = async () => {
  const response = await apiClient.get('/reports/summary');
  return response.data;
};

export const getAssetAgeReport = async () => {
  const response = await apiClient.get('/reports/asset-age');
  return response.data;
};

export const getStorageUsageReport = async () => {
  const response = await apiClient.get('/reports/storage-usage');
  return response.data;
};

export const getTierDistributionReport = async () => {
  const response = await apiClient.get('/reports/tier-distribution');
  return response.data;
};

export const getMostUsedTables = async (
  limit: number = 10,
  period: string = '30d'
) => {
  const response = await apiClient.get('/reports/most-used-tables', {
    params: { limit, period },
  });
  return response.data;
};

export const getDataQualityScore = async () => {
  const response = await apiClient.get('/reports/data-quality-score');
  return response.data;
};

// ============ Query Analysis ============

export const parseQueryLogs = async (hours: number = 24) => {
  const response = await apiClient.post('/analysis/parse-logs', {}, {
    params: { hours },
  });
  return response.data;
};

export const getQueryPatterns = async (tableId: number, hours: number = 24) => {
  const response = await apiClient.get(`/analysis/table/${tableId}/patterns`, {
    params: { hours },
  });
  return response.data;
};

export const getHeavyUsers = async () => {
  const response = await apiClient.get('/analysis/heavy-users');
  return response.data;
};

export const getQueryPerformance = async (tableId: number, limit: number = 20) => {
  const response = await apiClient.get(`/analysis/table/${tableId}/performance`, {
    params: { limit },
  });
  return response.data;
};

// ============ Jobs ============

export const getJobs = async (
  status?: string,
  skip: number = 0,
  limit: number = 50
) => {
  const params: any = { skip, limit };
  if (status) params.status = status;
  const response = await apiClient.get('/jobs', { params });
  return response.data;
};

export const getJob = async (id: number) => {
  const response = await apiClient.get(`/jobs/${id}`);
  return response.data;
};

export const getJobExecutions = async (
  jobId: number,
  skip: number = 0,
  limit: number = 50
) => {
  const response = await apiClient.get(`/jobs/${jobId}/executions`, {
    params: { skip, limit },
  });
  return response.data;
};

// ============ Mainframe ============

export interface MainframeJob {
  id: number;
  job_name: string;
  owner?: string;
  status: string;
  description?: string;
  job_class?: string;
  scheduler_system?: string;
  schedule_name?: string;
  frequency?: string;
  last_run?: string;
  next_run?: string;
  last_synced?: string;
  file_count?: number;
}

export interface MainframeJobFile {
  id: number;
  dd_name?: string;
  dataset_name: string;
  disposition?: string;
  direction?: string;
  dataset_type?: string;
  volume_serial?: string;
}

export interface MainframeJobSchedule {
  job_id: number;
  job_name: string;
  scheduler_system?: string;
  schedule_name?: string;
  frequency?: string;
  last_run?: string;
  next_run?: string;
}

export const getMainframeJobs = async (
  status?: string,
  scheduleName?: string,
  skip: number = 0,
  limit: number = 50
) => {
  const params: any = { skip, limit };
  if (status) params.status = status;
  if (scheduleName) params.schedule_name = scheduleName;
  const response = await apiClient.get<MainframeJob[]>('/mainframe/jobs', { params });
  return response.data;
};

export const getMainframeJob = async (id: number) => {
  const response = await apiClient.get<MainframeJob>(`/mainframe/jobs/${id}`);
  return response.data;
};

export const getMainframeJobFiles = async (id: number) => {
  const response = await apiClient.get<MainframeJobFile[]>(`/mainframe/jobs/${id}/files`);
  return response.data;
};

export const getMainframeJobSchedule = async (id: number) => {
  const response = await apiClient.get<MainframeJobSchedule>(`/mainframe/jobs/${id}/schedule`);
  return response.data;
};

export const syncMainframeJobs = async () => {
  const response = await apiClient.post('/mainframe/sync');
  return response.data;
};

// ============ Job Lineage (Mainframe/Teradata or Hadoop/Ab Initio) ============

export type LineagePlatform = 'MAINFRAME' | 'HADOOP_ABINITIO';
export type LineageDirection = 'upstream' | 'downstream' | 'both';

interface LineageNodeBase {
  id: string;
  name: string;
  impacted: boolean;
  impacted_by: string[];
}

export type SlaStatus = 'LATE' | 'COMPLETED_LATE' | 'AT_RISK' | 'ON_TRACK' | 'MET';

export interface SlaInfo {
  status: SlaStatus;
  expected_completion: string;
  completed_at?: string | null;
  late_by_minutes: number;
  reason: string;
}

export interface LineageJobNode extends LineageNodeBase {
  type: 'job';
  catalog_id: number;
  platform: LineagePlatform;
  platform_label: string;
  job_type: 'JCL' | 'TERADATA_LOAD' | 'AB_INITIO_GRAPH';
  owner?: string;
  description?: string;
  scheduler_system?: string;
  schedule_name?: string;
  frequency?: string;
  last_run?: string;
  next_run?: string;
  run_status: string;
  run_duration_seconds?: number;
  run_error?: string;
  sla: SlaInfo | null;
}

export interface LineageDatasetNode extends LineageNodeBase {
  type: 'dataset';
  dataset_type?: string;
  platform: 'MAINFRAME' | 'TERADATA' | 'HADOOP';
  database: string;
  /** Second label line for derived views (database / column graphs). */
  subtitle?: string;
}

export type LineageNode = LineageJobNode | LineageDatasetNode;

export interface LineageEdge {
  id: string;
  source: string;
  target: string;
  port?: string;
  /** Text on the arrow, e.g. the job(s) that move data between two tables. */
  label?: string;
  /** Run status of the job behind the arrow, when there is one. */
  status?: string;
}

export interface JobLineageGraph {
  nodes: LineageNode[];
  edges: LineageEdge[];
  platform: LineagePlatform;
  focus: string | null;
  summary: {
    jobs: number;
    tables_loaded: number;
    datasets: number;
    failed_jobs: string[];
    running_jobs: string[];
    impacted_jobs: number;
    sla_late: number;
    sla_at_risk: number;
  };
}

export interface JobLineageImpact {
  node: LineageNode;
  impacted_jobs: (LineageJobNode & { distance: number })[];
  impacted_datasets: LineageDatasetNode[];
  upstream_issues: (LineageJobNode & { distance: number })[];
}

export const getJobLineageGraph = async (options: {
  platform: LineagePlatform;
  focus?: string;
  direction?: LineageDirection;
  depth?: number;
}) => {
  const response = await apiClient.get<JobLineageGraph>('/job-lineage/graph', {
    params: options,
  });
  return response.data;
};

export const getJobLineageImpact = async (platform: LineagePlatform, node: string) => {
  const response = await apiClient.get<JobLineageImpact>('/job-lineage/impact', {
    params: { platform, node },
  });
  return response.data;
};

export interface LineageJobRef {
  id: string;
  name: string;
  run_status: string;
  last_run?: string;
  sla_status?: SlaStatus | null;
}

export interface LineageTableResult extends LineageDatasetNode {
  loaded_by: LineageJobRef[];
  read_by: LineageJobRef[];
}

export const searchJobLineageTables = async (
  platform: LineagePlatform,
  q: string,
  limit: number = 50
) => {
  const response = await apiClient.get<LineageTableResult[]>('/job-lineage/tables', {
    params: { platform, q, limit },
  });
  return response.data;
};

// ---- SLA tracking ----

export interface SlaJobRow extends LineageJobNode {
  sla: SlaInfo;
  blocked_by: { id: string; name: string; run_status: string }[];
}

export interface JobSlaReport {
  platform: LineagePlatform;
  jobs: SlaJobRow[];
  counts: Record<SlaStatus, number>;
  jobs_without_sla: number;
}

export const getJobLineageSla = async (platform: LineagePlatform) => {
  const response = await apiClient.get<JobSlaReport>('/job-lineage/sla', { params: { platform } });
  return response.data;
};

// ---- Columns ----

export interface LineageColumn {
  id: string;
  type: 'column';
  column: string;
  dataset_id: string;
  dataset_name: string;
  dataset_type?: string;
  platform?: 'MAINFRAME' | 'TERADATA' | 'HADOOP' | null;
  database: string;
  data_type?: string;
  description?: string;
  impacted: boolean;
  impacted_by: string[];
  upstream_columns?: number;
  downstream_columns?: number;
}

export interface ColumnSearchResult extends LineageColumn {
  loaded_by: LineageJobRef[];
  read_by: LineageJobRef[];
}

export interface ColumnLineageEdge {
  id: string;
  source: string;
  target: string;
  job_id: string;
  job_name: string;
  run_status: string;
  transformation?: string | null;
}

export interface ColumnLineageGraph {
  focus: ColumnSearchResult;
  nodes: LineageColumn[];
  edges: ColumnLineageEdge[];
}

export const searchJobLineageColumns = async (
  platform: LineagePlatform,
  q: string,
  exact: boolean = false
) => {
  const response = await apiClient.get<ColumnSearchResult[]>('/job-lineage/columns', {
    params: { platform, q, exact },
  });
  return response.data;
};

export const getLineageTableColumns = async (platform: LineagePlatform, dataset: string) => {
  const response = await apiClient.get<LineageColumn[]>('/job-lineage/table-columns', {
    params: { platform, dataset },
  });
  return response.data;
};

export const getColumnLineage = async (
  platform: LineagePlatform,
  column: string,
  direction: LineageDirection = 'both'
) => {
  const response = await apiClient.get<ColumnLineageGraph>('/job-lineage/column-lineage', {
    params: { platform, column, direction },
  });
  return response.data;
};

export const syncJobLineage = async () => {
  const response = await apiClient.post('/job-lineage/sync');
  return response.data;
};

export default apiClient;
