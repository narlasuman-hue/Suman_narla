import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import {
  FiAlertOctagon,
  FiDatabase,
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
  getJobLineageGraph,
  getJobLineageImpact,
  syncJobLineage,
  JobLineageGraph,
  JobLineageImpact,
  LineageDirection,
  LineagePlatform,
  LineageTableResult,
} from '../services/api';
import { StatCard } from '../components/StatCard';
import LineageGraph, { collapseToJobs } from '../components/LineageGraph';
import LineageDetailsPanel from '../components/LineageDetailsPanel';
import TableSearch from '../components/TableSearch';

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
];

const platformFromParam = (value: string | null): LineagePlatform =>
  value === PLATFORMS.HADOOP_ABINITIO.param ? 'HADOOP_ABINITIO' : 'MAINFRAME';

const selectClass =
  'px-3 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500';

const JobLineagePage: React.FC = () => {
  const [graph, setGraph] = useState<JobLineageGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const platform = platformFromParam(searchParams.get('platform'));
  const platformInfo = PLATFORMS[platform];
  const [focus, setFocus] = useState<string | null>(null);
  const [direction, setDirection] = useState<LineageDirection>('both');
  const [depth, setDepth] = useState<number | ''>('');
  const [viewMode, setViewMode] = useState<'jobs' | 'datasets'>('jobs');
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [impact, setImpact] = useState<JobLineageImpact | null>(null);
  const [impactLoading, setImpactLoading] = useState(false);

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

  const nodesById = useMemo(
    () => new Map((graph?.nodes || []).map((n) => [n.id, n])),
    [graph]
  );
  const shown = useMemo(() => {
    if (!graph) return null;
    return viewMode === 'jobs' ? collapseToJobs(graph.nodes, graph.edges) : graph;
  }, [graph, viewMode]);
  const selected = selectedId ? nodesById.get(selectedId) || null : null;

  const highlightIds = useMemo(() => {
    if (!impact) return null;
    return new Set([
      impact.node.id,
      ...impact.impacted_jobs.map((j) => j.id),
      ...impact.impacted_datasets.map((d) => d.id),
    ]);
  }, [impact]);

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
    setImpact(null);
    setSelectedId(id);
    setFocus(id);
  };

  const handleShowImpact = async (id: string) => {
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

  // Tables only appear as nodes in the datasets view, so switch to it.
  const handleTableSelect = (table: LineageTableResult) => {
    setViewMode('datasets');
    handleFocus(table.id);
  };

  const handlePlatformChange = (next: LineagePlatform) => {
    if (next === platform) return;
    setFocus(null);
    setSelectedId(null);
    setImpact(null);
    setSearchParams({ platform: PLATFORMS[next].param });
  };

  const clearFocus = () => {
    setFocus(null);
    setImpact(null);
  };

  const summary = graph?.summary;
  const failedJobs = (graph?.nodes || []).filter(
    (n) => n.type === 'job' && n.run_status === 'FAILED'
  );
  const isEmpty = !loading && graph && graph.nodes.length === 0 && !focus;

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
                active
                  ? 'border-indigo-600 bg-indigo-50 shadow'
                  : 'border-gray-200 bg-white hover:border-indigo-300'
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
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard title={platformInfo.jobsLabel} value={summary.jobs} icon={platformInfo.icon} color="indigo" />
          <StatCard title={platformInfo.tablesLabel} value={summary.tables_loaded} icon={FiGrid} color="green" />
          <StatCard title="Failed jobs" value={summary.failed_jobs.length} icon={FiAlertOctagon} color="red" />
          <StatCard title="Running" value={summary.running_jobs.length} icon={FiPlayCircle} color="blue" />
          <StatCard title="Impacted downstream" value={summary.impacted_jobs} icon={FiZap} color="orange" />
        </div>
      )}

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
        <TableSearch platform={platform} onSelect={handleTableSelect} />
        <div className="flex rounded-lg border border-gray-300 overflow-hidden text-sm">
          {(['jobs', 'datasets'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => setViewMode(mode)}
              className={`px-3 py-2 ${viewMode === mode ? 'bg-indigo-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}
            >
              {mode === 'jobs' ? 'Jobs only' : 'Jobs + datasets'}
            </button>
          ))}
        </div>
        <select value={direction} onChange={(e) => setDirection(e.target.value as LineageDirection)} disabled={!focus} className={selectClass}>
          <option value="both">Upstream + downstream</option>
          <option value="upstream">Upstream only</option>
          <option value="downstream">Downstream only</option>
        </select>
        <select value={depth} onChange={(e) => setDepth(e.target.value ? Number(e.target.value) : '')} disabled={!focus} className={selectClass}>
          <option value="">All levels</option>
          {[1, 2, 3, 5].map((d) => (
            <option key={d} value={d}>{d} level{d > 1 ? 's' : ''}</option>
          ))}
        </select>
        {focus && (
          <button onClick={clearFocus} className="flex items-center gap-1 px-3 py-2 text-sm rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100">
            Focused: {nodesById.get(focus)?.name || focus} <FiX />
          </button>
        )}
      </div>

      {isEmpty ? (
        <div className="bg-white rounded-lg shadow p-12 text-center text-gray-600">
          No {platformInfo.jobsLabel.toLowerCase()} in the catalog yet. Click "Sync job metadata" to load them.
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="relative h-[640px] bg-slate-50">
            {/* The graph shrinks while the details drawer is open so nothing hides under it. */}
            <div className={`absolute inset-y-0 left-0 ${selected ? 'right-0 md:right-[384px]' : 'right-0'}`}>
              {loading || !shown ? (
                <div className="h-full flex items-center justify-center text-gray-500">Loading lineage…</div>
              ) : (
                <LineageGraph
                  nodes={shown.nodes}
                  edges={shown.edges}
                  selectedId={selectedId}
                  highlightIds={highlightIds}
                  centerId={focus}
                  onSelect={handleSelect}
                />
              )}
            </div>
            {selected && (
              <div className="absolute top-3 right-3 bottom-3 w-[360px] max-w-[calc(100%-24px)] overflow-y-auto">
                <LineageDetailsPanel
                  node={selected}
                  nodesById={nodesById}
                  edges={graph?.edges || []}
                  impact={impact}
                  impactLoading={impactLoading}
                  onFocus={handleFocus}
                  onShowImpact={handleShowImpact}
                  onSelect={(id) => handleSelect(id)}
                  onClose={() => handleSelect(null)}
                />
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
            <span className="text-xs text-gray-400 ml-auto">Click a node for details · scroll to zoom · drag to pan</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default JobLineagePage;
