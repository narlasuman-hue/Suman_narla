import React, { useEffect, useState } from 'react';
import { FiClock, FiGitBranch, FiRefreshCw, FiZap } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { getJobLineageSla, JobSlaReport, LineagePlatform, SlaStatus } from '../services/api';
import {
  formatLate,
  formatTime,
  RunStatusBadge,
  SLA_LABEL,
  SLA_STYLE,
  SlaBadge,
} from './lineageBadges';

const ORDER: SlaStatus[] = ['LATE', 'COMPLETED_LATE', 'AT_RISK', 'ON_TRACK', 'MET'];

interface SlaPanelProps {
  platform: LineagePlatform;
  /** Bumped by the page after a sync so the report reloads. */
  refreshKey: number;
  onShowLineage: (jobId: string) => void;
  onShowImpact: (jobId: string) => void;
}

/** SLA tracking: every job with an expected completion time, worst first. */
const SlaPanel: React.FC<SlaPanelProps> = ({ platform, refreshKey, onShowLineage, onShowImpact }) => {
  const [report, setReport] = useState<JobSlaReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<SlaStatus | 'PROBLEMS' | 'ALL'>('PROBLEMS');

  const load = async () => {
    try {
      setLoading(true);
      setReport(await getJobLineageSla(platform));
    } catch (error) {
      toast.error('Failed to load SLA status');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [platform, refreshKey]);

  if (loading && !report) {
    return <div className="bg-white rounded-lg shadow p-12 text-center text-gray-500">Loading SLA status…</div>;
  }
  if (!report) return null;

  const problems = new Set<SlaStatus>(['LATE', 'COMPLETED_LATE', 'AT_RISK']);
  const rows = report.jobs.filter((j) =>
    filter === 'ALL' ? true : filter === 'PROBLEMS' ? problems.has(j.sla.status) : j.sla.status === filter
  );
  const chip = (key: typeof filter, label: string, count: number, active: string) => (
    <button
      key={key}
      onClick={() => setFilter(key)}
      className={`px-3 py-1.5 rounded-full text-sm border transition ${
        filter === key ? `${active} border-transparent` : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
      }`}
    >
      {label} <span className="font-semibold">{count}</span>
    </button>
  );

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="flex flex-wrap items-center gap-2 p-4 border-b border-gray-200">
        <FiClock className="text-indigo-600 mr-1" size={20} />
        {chip('PROBLEMS', 'Needs attention', report.counts.LATE + report.counts.COMPLETED_LATE + report.counts.AT_RISK, 'bg-gray-900 text-white')}
        {ORDER.map((s) => chip(s, SLA_LABEL[s], report.counts[s], SLA_STYLE[s]))}
        {chip('ALL', 'All', report.jobs.length, 'bg-gray-900 text-white')}
        <button onClick={load} title="Refresh" className="ml-auto p-2 text-gray-500 hover:text-gray-800">
          <FiRefreshCw className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {report.jobs.length === 0 ? (
        <p className="p-12 text-center text-gray-600">
          No jobs have an expected completion time. Add an <code>expected_completion</code> column
          to the jobs input file (see docs/JOB_LINEAGE_DEMO_DATA.md).
        </p>
      ) : rows.length === 0 ? (
        <p className="p-12 text-center text-gray-600">No jobs in this status.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-gray-700">
              <tr>
                <th className="px-4 py-3 font-semibold">SLA</th>
                <th className="px-4 py-3 font-semibold">Job</th>
                <th className="px-4 py-3 font-semibold">Expected by</th>
                <th className="px-4 py-3 font-semibold">Late by</th>
                <th className="px-4 py-3 font-semibold">Last run</th>
                <th className="px-4 py-3 font-semibold">Why / blocked by</th>
                <th className="px-4 py-3 font-semibold">Owner</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {rows.map((j) => (
                <tr key={j.id} className={j.sla.status === 'LATE' ? 'bg-red-50/40' : ''}>
                  <td className="px-4 py-3"><SlaBadge status={j.sla.status} /></td>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{j.name}</p>
                    <p className="text-xs text-gray-500">{j.scheduler_system} · {j.schedule_name}</p>
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">{formatTime(j.sla.expected_completion)}</td>
                  <td className="px-4 py-3 whitespace-nowrap font-semibold text-red-700">
                    {j.sla.late_by_minutes ? formatLate(j.sla.late_by_minutes) : '-'}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    <RunStatusBadge status={j.run_status} />
                    <span className="ml-2 text-xs text-gray-500">{formatTime(j.last_run)}</span>
                  </td>
                  <td className="px-4 py-3">
                    <p className="text-gray-700">{j.sla.reason}</p>
                    {j.blocked_by.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {j.blocked_by.map((b) => (
                          <span key={b.id} className="inline-flex items-center gap-1 text-xs bg-gray-100 rounded px-1.5 py-0.5">
                            {b.name} <RunStatusBadge status={b.run_status} />
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">{j.owner || '-'}</td>
                  <td className="px-4 py-3">
                    <div className="flex gap-1 justify-end">
                      <button
                        onClick={() => onShowLineage(j.id)}
                        title="Show lineage"
                        className="p-2 rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
                      >
                        <FiGitBranch size={14} />
                      </button>
                      <button
                        onClick={() => onShowImpact(j.id)}
                        title="Blast radius"
                        className="p-2 rounded bg-amber-500 text-white hover:bg-amber-600"
                      >
                        <FiZap size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {report.jobs_without_sla > 0 && (
        <p className="px-4 py-2 text-xs text-gray-500 border-t border-gray-100">
          {report.jobs_without_sla} job(s) have no expected completion time and are not tracked.
        </p>
      )}
    </div>
  );
};

export default SlaPanel;
