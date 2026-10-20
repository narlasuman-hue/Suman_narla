import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { FiClock, FiColumns, FiGitBranch, FiRefreshCw, FiX } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getColumnLineage,
  getJobLineageGraph,
  getLineagePlatforms,
  getJobLineageImpact,
  searchJobLineageColumns,
  syncJobLineage,
  ColumnLineageGraph,
  ColumnSearchResult,
  JobLineageGraph,
  JobLineageImpact,
  LineageDirection,
  LineageTableResult,
  PlatformInfo,
} from '../services/api';
import LineageGraph from '../components/LineageGraph';
import LineageDetailsPanel from '../components/LineageDetailsPanel';
import AttentionPanel from '../components/AttentionPanel';
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

interface LegendItem {
  label: string;
  style: React.CSSProperties;
}

/** Legend in the graph's own colors: status first, then what each shape is. */
const legend = (p: PlatformInfo): LegendItem[] => [
  { label: 'Failed', style: { background: '#fef2f2', border: '2px solid #dc2626' } },
  { label: 'Running', style: { background: '#eff6ff', border: '2px solid #2563eb' } },
  { label: 'Blocked by a failure', style: { background: '#fff7ed', border: '2px dashed #ea580c' } },
  { label: p.job_label, style: { background: '#fff', border: '1.5px solid #cbd5e1' } },
  { label: `Loads ${p.table_label}s`, style: { background: '#f1f5f9', border: '1.5px solid #64748b' } },
  { label: p.table_label, style: { background: '#fff', border: '2px solid #475569', borderRadius: 6 } },
  { label: 'Source dataset / file', style: { background: '#f8fafc', border: '1.5px solid #94a3b8', borderRadius: 6 } },
];

const VIEWS: { mode: LineageView; label: string; hint: string }[] = [
  { mode: 'jobs', label: 'Jobs', hint: 'Job-to-job dependencies' },
  { mode: 'tables', label: 'Tables', hint: 'Table-level lineage; arrows show the loading job' },
  { mode: 'datasets', label: 'Jobs + tables', hint: 'Jobs and the tables/files they read and write' },
  { mode: 'databases', label: 'Databases', hint: 'Database-level lineage' },
];

const selectClass =
  'h-[34px] px-2 text-[13px] border border-gray-300 rounded-lg bg-white text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-200 disabled:opacity-50';

const segment = (active: boolean) =>
  `h-[34px] px-3 font-medium ${active ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`;

interface ColumnSearchState {
  query: string;
  exact: boolean;
  results: ColumnSearchResult[];
  loading: boolean;
}

const JobLineagePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [platforms, setPlatforms] = useState<PlatformInfo[] | null>(null);
  // ?platform=<folder key>, e.g. ?platform=mainframe; defaults to the first platform.
  const platformKey = searchParams.get('platform');
  const platformInfo = platforms?.find((p) => p.key === platformKey) || platforms?.[0] || null;
  const platform = platformInfo?.id || '';

  const tab: 'lineage' | 'sla' = searchParams.get('tab') === 'sla' ? 'sla' : 'lineage';
  const setTab = (next: 'lineage' | 'sla') => {
    const params = new URLSearchParams(searchParams);
    if (next === 'sla') params.set('tab', 'sla');
    else params.delete('tab');
    setSearchParams(params);
  };
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

  const loadPlatforms = useCallback(async () => {
    try {
      setPlatforms(await getLineagePlatforms());
    } catch (error) {
      toast.error('Failed to load platforms');
      console.error(error);
      setPlatforms([]);
    }
  }, []);

  useEffect(() => {
    loadPlatforms();
  }, [loadPlatforms]);

  const loadGraph = useCallback(async () => {
    if (!platform) return;
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
    if (!columnFocus || !platform) {
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
      const count = Object.keys(stats.platforms || {}).length;
      toast.success(`Synced ${stats.jobs_synced} jobs across ${count} platforms from ${from}`);
      await Promise.all([loadGraph(), loadPlatforms()]);
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

  const handlePlatformChange = (next: PlatformInfo) => {
    if (next.id === platform) return;
    setFocus(null);
    resetSelection();
    setColumnSearch(null);
    setSearchParams(tab === 'sla' ? { platform: next.key, tab: 'sla' } : { platform: next.key });
  };

  const handleViewChange = (mode: LineageView) => {
    setColumnFocus(null);
    setSelectedId(null);
    setViewMode(mode);
  };

  const summary = graph?.summary;
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
        platform={platformInfo!}
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

  if (!platforms) {
    return <div className="p-12 text-center text-gray-500">Loading platforms…</div>;
  }
  if (!platformInfo) {
    return (
      <div className="p-12 text-center text-gray-600">
        No platforms are configured. Add them to platforms.csv in the lineage data folder.
      </div>
    );
  }

  const health = summary
    ? [
        { label: `${platformInfo.job_label}s`, value: summary.jobs },
        { label: `${platformInfo.table_label}s loaded`, value: summary.tables_loaded },
        { label: 'Failed', value: summary.failed_jobs.length, tone: 'red' as const },
        { label: 'Running', value: summary.running_jobs.length, tone: 'blue' as const },
        { label: 'Blocked downstream', value: summary.impacted_jobs, tone: 'orange' as const },
        { label: 'Late vs SLA', value: summary.sla_late, tone: 'red' as const, extra: `${summary.sla_at_risk} at risk` },
      ]
    : [];
  const toneClass = { red: 'text-red-700', blue: 'text-blue-700', orange: 'text-orange-700' };

  return (
    <div className="space-y-4">
      {/* Platforms + sync */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Platform">
          {platforms.map((p) => {
            const active = p.id === platform;
            return (
              <button
                key={p.id}
                role="tab"
                aria-selected={active}
                onClick={() => handlePlatformChange(p)}
                className={`flex min-h-[44px] flex-col gap-0.5 rounded-lg border-2 px-3.5 py-2 text-left ${
                  active ? 'border-gray-900 bg-white shadow-sm' : 'border-transparent hover:bg-white'
                }`}
              >
                <span className="flex items-center gap-2 text-[13px] font-semibold text-gray-900">
                  <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
                  {p.name}
                </span>
                <span className="flex gap-2.5 pl-4 text-xs text-gray-600">
                  <span>{p.summary.jobs} jobs</span>
                  {p.summary.failed > 0 && <span className="font-semibold text-red-700">{p.summary.failed} failed</span>}
                  {p.summary.sla_late > 0 && <span className="font-semibold text-orange-800">{p.summary.sla_late} late</span>}
                </span>
              </button>
            );
          })}
        </div>
        <button
          onClick={handleSync}
          disabled={syncing}
          className="ml-auto flex h-9 items-center gap-2 rounded-lg bg-blue-700 px-3.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          <FiRefreshCw className={syncing ? 'animate-spin' : ''} size={15} />
          {syncing ? 'Syncing…' : 'Sync metadata'}
        </button>
      </div>

      {/* Health strip */}
      {summary && (
        <section
          aria-label="Platform health"
          className="grid overflow-hidden rounded-lg bg-white shadow"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))' }}
        >
          {health.map((h) => {
            const alert = h.tone === 'red' && h.value > 0;
            return (
              <div key={h.label} className={`border-r border-gray-100 px-4 py-3 last:border-r-0 ${alert ? 'bg-red-50' : ''}`}>
                <div className={`text-xs ${alert ? 'font-semibold text-red-800' : 'text-gray-600'}`}>{h.label}</div>
                <div className={`mt-0.5 text-2xl font-bold tabular-nums ${h.tone && h.value > 0 ? toneClass[h.tone] : 'text-gray-900'}`}>
                  {h.value}
                  {h.extra && <span className="ml-1.5 text-[13px] font-medium text-gray-600">· {h.extra}</span>}
                </div>
              </div>
            );
          })}
        </section>
      )}

      {/* Lineage | SLA */}
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
            className={`-mb-px flex items-center gap-2 border-b-2 px-3 py-2 text-sm font-medium ${
              tab === t.key ? 'border-gray-900 text-gray-900' : 'border-transparent text-gray-600 hover:text-gray-900'
            }`}
          >
            <t.icon size={15} /> {t.label}
            {t.badge && t.badge.late > 0 && (
              <span className="rounded bg-red-700 px-1.5 text-[11px] font-semibold text-white">{t.badge.late} late</span>
            )}
            {t.badge && t.badge.risk > 0 && (
              <span className="rounded bg-orange-100 px-1.5 text-[11px] font-semibold text-orange-900">{t.badge.risk} at risk</span>
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
          {columnSearch && (
            <ColumnSearchResults
              {...columnSearch}
              onColumnLineage={openColumnLineage}
              onTableLineage={showTableLineage}
              onClose={() => setColumnSearch(null)}
            />
          )}

          {isEmpty ? (
            <div className="rounded-lg bg-white p-12 text-center text-gray-600 shadow">
              No {platformInfo.job_label}s in the catalog yet. Click "Sync metadata" to load them.
            </div>
          ) : (
            <div className="flex flex-col gap-4 xl:flex-row">
              {/* Graph */}
              <section aria-label="Lineage graph" className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-lg bg-white shadow">
                <div className="flex flex-wrap items-center gap-2.5 border-b border-gray-200 px-3.5 py-3">
                  <div className="flex overflow-hidden rounded-lg border border-gray-300 text-[13px]" role="group" aria-label="Search by">
                    <button onClick={() => setSearchMode('table')} className={segment(searchMode === 'table')}>Table</button>
                    <button onClick={() => setSearchMode('column')} className={`border-l border-gray-200 ${segment(searchMode === 'column')}`}>Column</button>
                  </div>
                  {searchMode === 'table' ? (
                    <TableSearch platform={platform} tableLabel={platformInfo.table_label} onSelect={(t: LineageTableResult) => showTableLineage(t.id)} />
                  ) : (
                    <ColumnSearch platform={platform} onSearch={runColumnSearch} />
                  )}
                  <div className="flex overflow-hidden rounded-lg border border-gray-300 text-[13px] xl:ml-auto" role="group" aria-label="Lineage level">
                    {VIEWS.map((v, i) => (
                      <button
                        key={v.mode}
                        title={v.hint}
                        onClick={() => handleViewChange(v.mode)}
                        className={`${i ? 'border-l border-gray-200 ' : ''}${segment(!columnFocus && viewMode === v.mode)}`}
                      >
                        {v.label}
                      </button>
                    ))}
                  </div>
                  <label className="flex items-center gap-1.5 text-xs text-gray-600">
                    Direction
                    <select value={direction} onChange={(e) => setDirection(e.target.value as LineageDirection)} disabled={!focus || !!columnFocus} className={selectClass}>
                      <option value="both">Both</option>
                      <option value="upstream">Upstream</option>
                      <option value="downstream">Downstream</option>
                    </select>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-gray-600">
                    Depth
                    <select value={depth} onChange={(e) => setDepth(e.target.value ? Number(e.target.value) : '')} disabled={!focus || !!columnFocus} className={selectClass}>
                      <option value="">All</option>
                      {[1, 2, 3, 5].map((d) => (
                        <option key={d} value={d}>{d}</option>
                      ))}
                    </select>
                  </label>
                </div>

                {focus && !columnFocus && (
                  <div className="flex flex-wrap items-center gap-2 border-b border-blue-100 bg-blue-50 px-3.5 py-2 text-[13px] text-blue-900">
                    Focused on <span className="font-mono font-semibold">{nodesById.get(focus)?.name || focus}</span>
                    <button
                      onClick={() => { setFocus(null); setImpact(null); }}
                      className="ml-auto flex h-[30px] items-center gap-1 rounded-lg border border-blue-200 bg-white px-2.5 text-xs font-medium text-blue-800 hover:bg-blue-100"
                    >
                      Show everything <FiX />
                    </button>
                  </div>
                )}
                {impact && !columnFocus && (
                  <div className="flex flex-wrap items-center gap-2 border-b border-red-200 bg-red-50 px-3.5 py-2 text-[13px] text-red-900">
                    Blast radius of <span className="font-mono font-semibold">{impact.node.name}</span>: what it blocks is highlighted, the rest is faded.
                    <button
                      onClick={() => setImpact(null)}
                      className="ml-auto flex h-[30px] items-center gap-1 rounded-lg border border-red-200 bg-white px-2.5 text-xs font-medium text-red-800 hover:bg-red-100"
                    >
                      Clear <FiX />
                    </button>
                  </div>
                )}
                {columnFocus && (
                  <div className="flex flex-wrap items-center gap-3 border-b border-blue-100 bg-blue-50 px-3.5 py-2">
                    <FiColumns className="text-blue-700" />
                    <p className="text-[13px] text-blue-900">
                      Column lineage:{' '}
                      <span className="break-all font-mono font-semibold">
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
                      className="ml-auto flex h-[30px] items-center gap-1 rounded-lg border border-blue-200 bg-white px-2.5 text-xs font-medium text-blue-800 hover:bg-blue-100"
                    >
                      Back to {VIEWS.find((v) => v.mode === viewMode)?.label.toLowerCase()} view <FiX />
                    </button>
                  </div>
                )}

                <div
                  className="relative h-[620px]"
                  style={{ background: '#f8fafc radial-gradient(#e2e8f0 1px, transparent 1px) 0 0 / 18px 18px' }}
                >
                  {loading || !shown ? (
                    <div className="flex h-full items-center justify-center text-gray-600">Loading lineage…</div>
                  ) : shown.nodes.length === 0 ? (
                    <div className="flex h-full items-center justify-center text-gray-600">Nothing to show in this view.</div>
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
                <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-gray-200 px-3.5 py-2.5">
                  {legend(platformInfo).map((l) => (
                    <span key={l.label} className="flex items-center gap-1.5 text-xs text-gray-700">
                      <span className="inline-block h-2.5 w-3.5 rounded-sm" style={l.style} aria-hidden="true" />
                      {l.label}
                    </span>
                  ))}
                  {(columnFocus || viewMode === 'tables' || viewMode === 'databases') && (
                    <span className="text-xs text-gray-600">Arrow label = job · red arrow = job failed</span>
                  )}
                  <span className="ml-auto text-xs text-gray-600">Click a node for details · scroll to zoom · drag to pan</span>
                </div>
              </section>

              {/* Details, or what needs attention */}
              <aside className="w-full flex-shrink-0 xl:w-[360px]">
                <div className="xl:sticky xl:top-0 xl:max-h-[760px] xl:overflow-y-auto">
                  {drawer || (
                    <AttentionPanel
                      nodes={graph?.nodes || []}
                      onShowImpact={handleShowImpact}
                      onSelect={(id) => handleSelect(id)}
                    />
                  )}
                </div>
              </aside>
            </div>
          )}
        </>
      )}
    </div>
  );
};

export default JobLineagePage;
