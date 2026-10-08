import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FiAlertOctagon,
  FiClock,
  FiColumns,
  FiDatabase,
  FiGitBranch,
  FiGrid,
  FiLayers,
  FiPlayCircle,
  FiRefreshCw,
  FiServer,
  FiX,
  FiZap,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getColumnLineage,
  getJobLineageGraph,
  getJobLineageImpact,
  searchJobLineageColumns,
  syncJobLineage,
  ColumnLineageGraph,
  ColumnSearchResult,
  JobLineageGraph,
  JobLineageImpact,
  LineageDirection,
  LineagePlatform,
  LineageTableResult,
} from '../services/api';
import { StatCard } from '../components/StatCard';
import LineageGraph from '../components/LineageGraph';
import LineageDetailsPanel from '../components/LineageDetailsPanel';
import TableSearch from '../components/TableSearch';
import ColumnSearch from '../components/ColumnSearch';
import ColumnSearchResults from '../components/ColumnSearchResults';
import ColumnDetailsPanel from '../components/ColumnDetailsPanel';
import DatabaseDetailsPanel from '../components/DatabaseDetailsPanel';
import SlaPanel from '../components/SlaPanel';
import {
  collapseToDatabases,
  collapseToJobs,
  collapseToTables,
  columnLineageToGraph,
  LineageView,
} from '../utils/lineageViews';

/** The two independent platforms; the user picks one and sees only its lineage. */
const PLATFORMS: Record<
  LineagePlatform,
  {
    param: string;
    title: string;
    subtitle: string;
    icon: React.ComponentType<{ size?: number; className?: string }>;
    jobsLabel: string;
    tablesLabel: string;
    legend: { label: string; className: string }[];
  }
> = {
  MAINFRAME: {
    param: 'mainframe',
    title: 'Mainframe → Teradata',
    subtitle: 'Mainframe jobs loading Teradata tables',
    icon: FiServer,
    jobsLabel: 'Mainframe jobs',
    tablesLabel: 'Teradata tables loaded',
    legend: [
      { label: 'Mainframe JCL job', className: 'bg-indigo-800' },
      { label: 'Teradata load job', className: 'bg-orange-700' },
      { label: 'Mainframe dataset', className: 'bg-indigo-50 border-2 border-indigo-500' },
      { label: 'Teradata table', className: 'bg-orange-50 border-2 border-orange-500' },
    ],
  },
  HADOOP_ABINITIO: {
    param: 'abinitio',
    title: 'Ab Initio → Hadoop',
    subtitle: 'Ab Initio graphs loading Hadoop tables',
    icon: FiDatabase,
    jobsLabel: 'Ab Initio graphs',
    tablesLabel: 'Hadoop tables loaded',
    legend: [
      { label: 'Ab Initio graph', className: 'bg-teal-700' },
      { label: 'HDFS / Hive table', className: 'bg-teal-50 border-2 border-teal-500' },
    ],
  },
};

const statusLegend = [
  { label: 'Failed run', className: 'bg-white border-4 border-red-600' },
  { label: 'Running', className: 'bg-white border-4 border-dashed border-blue-400' },
  { label: 'Impacted by failure', className: 'bg-amber-300' },
  { label: '⏰ SLA late', className: 'hidden' },
];

const VIEWS: { mode: LineageView; label: string; hint: string }[] = [
  { mode: 'jobs', label: 'Jobs', hint: 'Job-to-job dependencies' },
  { mode: 'tables', label: 'Tables', hint: 'Table-level lineage; arrows show the loading job' },
  { mode: 'datasets', label: 'Jobs + tables', hint: 'Jobs and the tables/files they read and write' },
  { mode: 'databases', label: 'Databases', hint: 'Database-level lineage' },
];

const platformFromParam = (value: string | null): LineagePlatform =>
  value === PLATFORMS.HADOOP_ABINITIO.param ? 'HADOOP_ABINITIO' : 'MAINFRAME';

const selectClass =
  'px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:opacity-50';

const segment = (active: boolean) =>
  `px-3 py-2 ${active ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`;

interface ColumnSearchState {
  query: string;
  exact: boolean;
  results: ColumnSearchResult[];
  loading: boolean;
}

const JobLineagePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const platform = platformFromParam(searchParams.get('platform'));
  const platformInfo = PLATFORMS[platform];

  const [tab, setTab] = useState<'lineage' | 'sla'>('lineage');
  const [graph, setGraph] = useState<JobLineageGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [slaRefresh, setSlaRefresh] = useState(0);
  const [focus, setFocus] = useState<string | null>(null);
  const [direction, setDirection] = useState<LineageDirection>('both');
  const [depth, setDepth] = useState<number | ''>('');
  const [viewMode, setViewMode] = useState<LineageView>('jobs');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [impact, setImpact] = useState<JobLineageImpact | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);
  const [searchMode, setSearchMode] = useState<'table' | 'column'>('table');
  const [columnSearch, setColumnSearch] = useState<ColumnSearchState | null>(null);
  const [columnFocus, setColumnFocus] = useState<string | null>(null);
  const [columnDirection, setColumnDirection] = useState<LineageDirection>('both');
  const [columnLineage, setColumnLineage] = useState<ColumnLineageGraph | null>(null);

  const loadGraph = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getJobLineageGraph({
        platform,
        focus: focus || undefined,
        direction,
        depth: focus && depth ? depth : undefined,
      });
      setGraph(data);
    } catch (error) {
      toast.error('Failed to load job lineage');
      console.error(error);
    } finally {
      setLoading(false);
    }
  }, [platform, focus, direction, depth]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  useEffect(() => {
    if (!columnFocus) {
      setColumnLineage(null);
      return;
    }
    let cancelled = false;
    getColumnLineage(platform, columnFocus, columnDirection)
      .then((data) => !cancelled && setColumnLineage(data))
      .catch((error) => {
        toast.error('Failed to load column lineage');
        console.error(error);
      });
    return () => {
      cancelled = true;
    };
  }, [platform, columnFocus, columnDirection]);

  const nodesById = useMemo(() => new Map((graph?.nodes || []).map((n) => [n.id, n])), [graph]);
  const dbView = useMemo(
    () => (graph && viewMode === 'databases' ? collapseToDatabases(graph.nodes, graph.edges) : null),
    [graph, viewMode]
  );
  const shown = useMemo(() => {
    if (columnFocus) return columnLineage ? columnLineageToGraph(columnLineage) : null;
    if (!graph) return null;
    if (viewMode === 'jobs') return collapseToJobs(graph.nodes, graph.edges);
    if (viewMode === 'tables') return collapseToTables(graph.nodes, graph.edges);
    if (viewMode === 'databases') return dbView;
    return graph;
  }, [graph, viewMode, dbView, columnFocus, columnLineage]);

  const highlightIds = useMemo(() => {
    if (!impact || columnFocus) return null;
    const ids = [impact.node.id, ...impact.impacted_jobs.map((j) => j.id), ...impact.impacted_datasets.map((d) => d.id)];
    // In the database view, highlight the databases holding the impacted tables.
    return new Set(dbView ? ids.map((id) => dbView.databaseOf.get(id) || id) : ids);
  }, [impact, dbView, columnFocus]);

  const resetSelection = () => {
    setSelectedId(null);
    setImpact(null);
    setColumnFocus(null);
  };

  const handleSync = async () => {
    try {
      setSyncing(true);
      const stats = await syncJobLineage();
      const from = stats.source?.startsWith('files:') ? 'input files' : 'sample data';
      toast.success(
        `Synced ${stats.mainframe.jobs_created + stats.mainframe.jobs_updated} mainframe jobs, ` +
          `${stats.abinitio.jobs_created + stats.abinitio.jobs_updated} Ab Initio graphs from ${from}`
      );
      await loadGraph();
      setSlaRefresh((n) => n + 1);
    } catch (error: any) {
      // A bad input file comes back as a 400 naming the file, line and problem.
      toast.error(error?.response?.data?.detail || 'Lineage sync failed', { duration: 10000 });
      console.error(error);
    } finally {
      setSyncing(false);
    }
  };

  const handleSelect = (id: string | null) => {
    setSelectedId(id);
    if (!id || impact?.node.id !== id) setImpact(null);
  };

  const handleFocus = (id: string) => {
    setColumnFocus(null);
    setImpact(null);
    setSelectedId(id);
    setFocus(id);
    setTab('lineage');
  };

  const handleShowImpact = async (id: string) => {
    setTab('lineage');
    setColumnFocus(null);
    try {
      setImpactLoading(true);
      setSelectedId(id);
      setImpact(await getJobLineageImpact(platform, id));
    } catch (error) {
      toast.error('Failed to calculate blast radius');
      console.error(error);
    } finally {
      setImpactLoading(false);
    }
  };

  /** Table-level lineage of one table: the Tables view focused on it. */
  const showTableLineage = (datasetId: string) => {
    setViewMode('tables');
    handleFocus(datasetId);
  };

  const openColumnLineage = (columnId: string) => {
    setTab('lineage');
    setImpact(null);
    setColumnFocus(columnId);
    setSelectedId(columnId);
  };

  const runColumnSearch = async (query: string, exact: boolean) => {
    setColumnSearch({ query, exact, results: [], loading: true });
    try {
      const results = await searchJobLineageColumns(platform, query, exact);
      setColumnSearch({ query, exact, results, loading: false });
    } catch (error) {
      toast.error('Column search failed');
      console.error(error);
      setColumnSearch(null);
    }
  };

  const handlePlatformChange = (next: LineagePlatform) => {
    if (next === platform) return;
    setFocus(null);
    resetSelection();
    setColumnSearch(null);
    setSearchParams({ platform: PLATFORMS[next].param });
  };

  const handleViewChange = (mode: LineageView) => {
    setColumnFocus(null);
    setSelectedId(null);
    setViewMode(mode);
  };

  const summary = graph?.summary;
  const failedJobs = (graph?.nodes || []).filter((n) => n.type === 'job' && n.run_status === 'FAILED');
  const isEmpty = !loading && graph && graph.nodes.length === 0 && !focus;

  // Which details drawer (if any) goes next to the graph.
  let drawer: React.ReactNode = null;
  if (columnFocus && columnLineage && selectedId) {
    drawer = (
      <ColumnDetailsPanel
        lineage={columnLineage}
        columnId={selectedId}
        onTrace={openColumnLineage}
        onTableLineage={showTableLineage}
        onClose={() => setSelectedId(null)}
      />
    );
  } else if (!columnFocus && dbView && selectedId?.startsWith('db:')) {
    drawer = (
      <DatabaseDetailsPanel
        databaseId={selectedId}
        view={dbView}
        onTableSelect={showTableLineage}
        onDatabaseSelect={setSelectedId}
        onClose={() => setSelectedId(null)}
      />
    );
  } else if (!columnFocus && selectedId && nodesById.get(selectedId)) {
    drawer = (
      <LineageDetailsPanel
        node={nodesById.get(selectedId)!}
        nodesById={nodesById}
        edges={graph?.edges || []}
        impact={impact}
        impactLoading={impactLoading}
        onFocus={handleFocus}
        onShowImpact={handleShowImpact}
        onSelect={(id) => handleSelect(id)}
        onClose={() => handleSelect(null)}
        platform={platform}
        onColumnSelect={openColumnLineage}
      />
    );
  }

  const centerId = columnFocus
    ? columnFocus
    : dbView && focus
      ? dbView.databaseOf.get(focus) || null
      : focus;
  const focusedColumn = columnLineage?.focus;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <FiLayers className="text-indigo-600" size={32} />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Job Lineage</h1>
            <p className="text-gray-600">Choose a platform to see how its tables are loaded</p>
          </div>
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
        >
          <FiRefreshCw className={syncing ? 'animate-spin' : ''} size={18} />
          {syncing ? 'Syncing...' : 'Sync job metadata'}
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4" role="tablist" aria-label="Platform">
        {(Object.keys(PLATFORMS) as LineagePlatform[]).map((p) => {
          const info = PLATFORMS[p];
          const Icon = info.icon;
          const active = p === platform;
          return (
            <button
              key={p}
              role="tab"
              aria-selected={active}
              onClick={() => handlePlatformChange(p)}
              className={`flex items-center gap-4 p-5 rounded-lg border-2 text-left transition ${
                active ? 'border-indigo-600 bg-indigo-50 shadow' : 'border-gray-200 bg-white hover:border-indigo-300'
              }`}
            >
              <Icon size={28} className={active ? 'text-indigo-600' : 'text-gray-400'} />
              <div>
                <p className={`text-lg font-bold ${active ? 'text-indigo-900' : 'text-gray-800'}`}>{info.title}</p>
                <p className="text-sm text-gray-600">{info.subtitle}</p>
              </div>
            </button>
          );
        })}
      </div>

      {summary && (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard title={platformInfo.jobsLabel} value={summary.jobs} icon={platformInfo.icon} color="indigo" />
          <StatCard title={platformInfo.tablesLabel} value={summary.tables_loaded} icon={FiGrid} color="green" />
          <StatCard title="Failed jobs" value={summary.failed_jobs.length} icon={FiAlertOctagon} color="red" />
          <StatCard title="Running" value={summary.running_jobs.length} icon={FiPlayCircle} color="blue" />
          <StatCard title="Impacted downstream" value={summary.impacted_jobs} icon={FiZap} color="orange" />
          <StatCard title="Late vs SLA" value={summary.sla_late} icon={FiClock} color="red" />
        </div>
      )}

      <div className="flex gap-1 border-b border-gray-200" role="tablist" aria-label="View">
        {[
          { key: 'lineage' as const, label: 'Lineage', icon: FiGitBranch, badge: null },
          {
            key: 'sla' as const,
            label: 'SLA tracking',
            icon: FiClock,
            badge: summary ? { late: summary.sla_late, risk: summary.sla_at_risk } : null,
          },
        ].map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 -mb-px border-b-2 text-sm font-medium ${
              tab === t.key ? 'border-indigo-600 text-indigo-700' : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <t.icon /> {t.label}
            {t.badge && t.badge.late > 0 && (
              <span className="px-1.5 rounded-full bg-red-600 text-white text-xs">{t.badge.late} late</span>
            )}
            {t.badge && t.badge.risk > 0 && (
              <span className="px-1.5 rounded-full bg-amber-100 text-amber-900 text-xs">{t.badge.risk} at risk</span>
            )}
          </button>
        ))}
      </div>

      {tab === 'sla' ? (
        <SlaPanel
          platform={platform}
          refreshKey={slaRefresh}
          onShowLineage={(jobId) => {
            setViewMode('jobs');
            handleFocus(jobId);
          }}
          onShowImpact={(jobId) => {
            setViewMode('jobs');
            setFocus(null);
            handleShowImpact(jobId);
          }}
        />
      ) : (
        <>
          {failedJobs.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 p-4 bg-red-50 border border-red-200 rounded-lg">
              <FiAlertOctagon className="text-red-600" size={20} />
              <span className="text-sm font-semibold text-red-900 mr-2">Failed jobs:</span>
              {failedJobs.map((j) => (
                <button
                  key={j.id}
                  onClick={() => handleShowImpact(j.id)}
                  className="px-3 py-1 text-sm rounded-full bg-white border border-red-300 text-red-800 hover:bg-red-100"
                >
                  {j.name} — show blast radius
                </button>
              ))}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-3 bg-white rounded-lg shadow p-4">
            <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm" role="group" aria-label="Search by">
              <button onClick={() => setSearchMode('table')} className={segment(searchMode === 'table')}>Table</button>
              <button onClick={() => setSearchMode('column')} className={segment(searchMode === 'column')}>Column</button>
            </div>
            {searchMode === 'table' ? (
              <TableSearch platform={platform} onSelect={(t: LineageTableResult) => showTableLineage(t.id)} />
            ) : (
              <ColumnSearch platform={platform} onSearch={runColumnSearch} />
            )}
            <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm" role="group" aria-label="Lineage level">
              {VIEWS.map((v) => (
                <button
                  key={v.mode}
                  title={v.hint}
                  onClick={() => handleViewChange(v.mode)}
                  className={segment(!columnFocus && viewMode === v.mode)}
                >
                  {v.label}
                </button>
              ))}
            </div>
            <select value={direction} onChange={(e) => setDirection(e.target.value as LineageDirection)} disabled={!focus || !!columnFocus} className={selectClass}>
              <option value="both">Upstream + downstream</option>
              <option value="upstream">Upstream only</option>
              <option value="downstream">Downstream only</option>
            </select>
            <select value={depth} onChange={(e) => setDepth(e.target.value ? Number(e.target.value) : '')} disabled={!focus || !!columnFocus} className={selectClass}>
              <option value="">All levels</option>
              {[1, 2, 3, 5].map((d) => (
                <option key={d} value={d}>{d} level{d > 1 ? 's' : ''}</option>
              ))}
            </select>
            {focus && !columnFocus && (
              <button onClick={() => { setFocus(null); setImpact(null); }} className="flex items-center gap-1 px-3 py-2 text-sm rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100">
                Focused: {nodesById.get(focus)?.name || focus} <FiX />
              </button>
            )}
          </div>

          {columnSearch && (
            <ColumnSearchResults
              {...columnSearch}
              onColumnLineage={openColumnLineage}
              onTableLineage={showTableLineage}
              onClose={() => setColumnSearch(null)}
            />
          )}

          {isEmpty ? (
            <div className="bg-white rounded-lg shadow p-12 text-center text-gray-600">
              No {platformInfo.jobsLabel.toLowerCase()} in the catalog yet. Click "Sync job metadata" to load them.
            </div>
          ) : (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              {columnFocus && (
                <div className="flex flex-wrap items-center gap-3 px-4 py-3 bg-indigo-50 border-b border-indigo-100">
                  <FiColumns className="text-indigo-600" />
                  <p className="text-sm text-indigo-900">
                    Column lineage:{' '}
                    <span className="font-semibold break-all">
                      {focusedColumn ? `${focusedColumn.dataset_name}.${focusedColumn.column}` : '…'}
                    </span>
                  </p>
                  <select value={columnDirection} onChange={(e) => setColumnDirection(e.target.value as LineageDirection)} className={selectClass}>
                    <option value="both">Sources + targets</option>
                    <option value="upstream">Where it comes from</option>
                    <option value="downstream">Where it goes</option>
                  </select>
                  <button
                    onClick={() => { setColumnFocus(null); setSelectedId(null); }}
                    className="ml-auto flex items-center gap-1 px-3 py-1.5 text-sm rounded-lg border border-indigo-200 bg-white text-indigo-700 hover:bg-indigo-100"
                  >
                    Back to {VIEWS.find((v) => v.mode === viewMode)?.label.toLowerCase()} view <FiX />
                  </button>
                </div>
              )}
              <div className="relative h-[640px] bg-slate-50">
                {/* The graph shrinks while the details drawer is open so nothing hides under it. */}
                <div className={`absolute inset-y-0 left-0 ${drawer ? 'right-0 md:right-[384px]' : 'right-0'}`}>
                  {loading || !shown ? (
                    <div className="h-full flex items-center justify-center text-gray-500">Loading lineage…</div>
                  ) : shown.nodes.length === 0 ? (
                    <div className="h-full flex items-center justify-center text-gray-500">Nothing to show in this view.</div>
                  ) : (
                    <LineageGraph
                      nodes={shown.nodes}
                      edges={shown.edges}
                      selectedId={selectedId}
                      highlightIds={highlightIds}
                      centerId={centerId}
                      onSelect={handleSelect}
                    />
                  )}
                </div>
                {drawer && (
                  <div className="absolute top-3 right-3 bottom-3 w-[360px] max-w-[calc(100%-24px)] overflow-y-auto">
                    {drawer}
                  </div>
                )}
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 border-t border-gray-200">
                {[...platformInfo.legend, ...statusLegend].map((l) => (
                  <span key={l.label} className="flex items-center gap-2 text-xs text-gray-600">
                    <span className={`inline-block w-4 h-3 rounded-sm ${l.className}`} />
                    {l.label}
                  </span>
                ))}
                {(columnFocus || viewMode === 'tables' || viewMode === 'databases') && (
                  <span className="text-xs text-gray-600">Arrow label = job · red arrow = job failed</span>
                )}
                <span className="text-xs text-gray-400 ml-auto">Click a node for details · scroll to zoom · drag to pan</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default JobLineagePage;
