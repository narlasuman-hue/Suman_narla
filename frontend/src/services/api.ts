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

export default apiClient;
