import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { FiChevronRight, FiRefreshCw, FiSearch } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getLineagePlatforms,
  getPlatformJobs,
  syncJobLineage,
  PlatformInfo,
  PlatformJob,
} from '../services/api';
import PlatformTabs from '../components/PlatformTabs';
import { RunStatusBadge, relative } from '../components/lineageBadges';

type RunFilter = 'ALL' | 'FAILED' | 'RUNNING' | 'SUCCESS';

const FILTERS: { key: RunFilter; label: string }[] = [
  { key: 'ALL', label: 'All' },
  { key: 'FAILED', label: 'Failed' },
  { key: 'RUNNING', label: 'Running' },
  { key: 'SUCCESS', label: 'Succeeded' },
];

/** Every platform's jobs: pick a platform, filter by run status or name, open a job. */
const JobsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const [platforms, setPlatforms] = useState<PlatformInfo[] | null>(null);
  const [jobs, setJobs] = useState<PlatformJob[] | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [query, setQuery] = useState('');
  const [runFilter, setRunFilter] = useState<RunFilter>('ALL');

  // ?platform=<folder key>, e.g. ?platform=airflow; defaults to the first platform.
  const platformKey = searchParams.get('platform');
  const platform = platforms?.find((p) => p.key === platformKey) || platforms?.[0] || null;

  const loadPlatforms = useCallback(async () => {
    try {
      setPlatforms(await getLineagePlatforms());
    } catch (error) {
      toast.error('Failed to load platforms');
      console.error(error);
      setPlatforms([]);
    }
  }, []);

  const loadJobs = useCallback(async () => {
    if (!platform) return;
    try {
      setJobs(null);
      setJobs(await getPlatformJobs(platform.id));
    } catch (error) {
      toast.error(`Failed to load ${platform.name} jobs`);
      console.error(error);
      setJobs([]);
    }
  }, [platform?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    loadPlatforms();
  }, [loadPlatforms]);

  useEffect(() => {
    loadJobs();
  }, [loadJobs]);

  const handleSync = async () => {
    try {
      setSyncing(true);
      const stats = await syncJobLineage();
      toast.success(`Synced ${stats.jobs_synced} jobs across ${Object.keys(stats.platforms || {}).length} platforms`);
      await Promise.all([loadPlatforms(), loadJobs()]);
    } catch (error: any) {
      toast.error(error?.response?.data?.detail || 'Sync failed', { duration: 10000 });
      console.error(error);
    } finally {
      setSyncing(false);
    }
  };

  const counts = useMemo(() => {
    const c: Record<RunFilter, number> = { ALL: 0, FAILED: 0, RUNNING: 0, SUCCESS: 0 };
    (jobs || []).forEach((j) => {
      c.ALL += 1;
      if (j.last_run_status && j.last_run_status in c) c[j.last_run_status as RunFilter] += 1;
    });
    return c;
  }, [jobs]);

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase();
    return (jobs || []).filter(
      (j) =>
        (runFilter === 'ALL' || j.last_run_status === runFilter) &&
        (!q ||
          [j.job_name, j.owner, j.schedule_name, j.description].some((v) => v?.toLowerCase().includes(q)))
    );
  }, [jobs, query, runFilter]);

  if (!platforms) {
    return <div className="p-12 text-center text-gray-600">Loading platforms…</div>;
  }
  if (!platform) {
    return (
      <div className="p-12 text-center text-gray-600">
        No platforms are configured. Add them to platforms.csv in the lineage data folder.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <PlatformTabs
          platforms={platforms}
          activeId={platform.id}
          onChange={(p) => {
            setRunFilter('ALL');
            setSearchParams({ platform: p.key });
          }}
        />
        <button
          onClick={handleSync}
          disabled={syncing}
          className="ml-auto flex h-9 items-center gap-2 rounded-lg bg-blue-700 px-3.5 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
        >
          <FiRefreshCw className={syncing ? 'animate-spin' : ''} size={15} />
          {syncing ? 'Syncing…' : 'Sync metadata'}
        </button>
      </div>

      <section className="overflow-hidden rounded-lg bg-white shadow" aria-label={`${platform.name} jobs`}>
        <div className="flex flex-wrap items-center gap-3 border-b border-gray-200 px-4 py-3">
          <h1 className="text-[15px] font-semibold text-gray-900">{platform.job_label}s</h1>
          <span className="text-xs text-gray-600">{platform.description}</span>
          <div className="flex overflow-hidden rounded-lg border border-gray-300 text-[13px] lg:ml-auto" role="group" aria-label="Last run">
            {FILTERS.map((f, i) => (
              <button
                key={f.key}
                onClick={() => setRunFilter(f.key)}
                aria-pressed={runFilter === f.key}
                className={`h-[34px] px-3 font-medium ${i ? 'border-l border-gray-200 ' : ''}${
                  runFilter === f.key ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'
                }`}
              >
                {f.label} <span className="tabular-nums opacity-75">{counts[f.key]}</span>
              </button>
            ))}
          </div>
          <label className="relative w-full sm:w-64">
            <span className="sr-only">Filter jobs</span>
            <FiSearch className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={15} />
            <input
              type="search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by name, owner, schedule"
              className="h-[34px] w-full rounded-lg border border-gray-300 pl-9 pr-3 text-[13px] focus:border-blue-500 focus:outline-none focus:ring-2 focus:ring-blue-200"
            />
          </label>
        </div>

        {jobs === null ? (
          <div className="p-12 text-center text-gray-600">Loading jobs…</div>
        ) : jobs.length === 0 ? (
          <div className="p-12 text-center text-gray-600">
            No {platform.job_label}s in the catalog yet. Click "Sync metadata" to load them.
          </div>
        ) : shown.length === 0 ? (
          <div className="p-12 text-center text-gray-600">No jobs match these filters.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                <tr>
                  <th className="px-4 py-2.5">{platform.job_label}</th>
                  <th className="px-4 py-2.5">Last run</th>
                  <th className="px-4 py-2.5">Owner</th>
                  <th className="px-4 py-2.5">Schedule</th>
                  <th className="px-4 py-2.5">Next run</th>
                  <th className="px-4 py-2.5 text-right">Datasets</th>
                  <th className="px-4 py-2.5"><span className="sr-only">Open</span></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {shown.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="max-w-[320px] px-4 py-3">
                      <Link
                        to={`/jobs/${platform.key}/${job.id}`}
                        className="font-mono text-[13px] font-semibold text-gray-900 hover:text-blue-700"
                      >
                        {job.job_name}
                      </Link>
                      {job.description && <div className="truncate text-xs text-gray-600">{job.description}</div>}
                    </td>
                    <td className="whitespace-nowrap px-4 py-3">
                      {job.last_run_status ? (
                        <span className="flex items-center gap-2">
                          <RunStatusBadge status={job.last_run_status} />
                          <span className="text-xs text-gray-600">{relative(job.last_run)}</span>
                        </span>
                      ) : (
                        <span className="text-xs text-gray-600">Not run</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-700">{job.owner || '—'}</td>
                    <td className="px-4 py-3">
                      <div className="whitespace-nowrap text-gray-900">{job.schedule_name || '—'}</div>
                      <div className="text-xs text-gray-600">
                        {[job.scheduler_system, job.frequency].filter(Boolean).join(' · ')}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-4 py-3 text-xs text-gray-600">{relative(job.next_run)}</td>
                    <td className="px-4 py-3 text-right tabular-nums text-gray-700">{job.file_count ?? 0}</td>
                    <td className="px-4 py-3 text-right">
                      <Link
                        to={`/jobs/${platform.key}/${job.id}`}
                        aria-label={`Open ${job.job_name}`}
                        className="inline-flex items-center gap-1 text-[13px] font-medium"
                      >
                        Details <FiChevronRight size={14} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default JobsPage;
