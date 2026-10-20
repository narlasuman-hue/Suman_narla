import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { FiAlertCircle, FiArrowLeft, FiLayers } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getLineagePlatforms,
  getPlatformJob,
  getPlatformJobFiles,
  PlatformInfo,
  PlatformJob,
  PlatformJobFile,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { formatTime, relative, RunStatusBadge } from '../components/lineageBadges';

const DIRECTION_STYLE: Record<string, string> = {
  INPUT: 'bg-blue-50 text-blue-800',
  OUTPUT: 'bg-purple-50 text-purple-800',
  INOUT: 'bg-amber-50 text-amber-900',
};

/** One job of any platform: what it is, how it last ran, and the datasets it reads and writes. */
const JobDetail: React.FC = () => {
  const { platformKey, id } = useParams<{ platformKey: string; id: string }>();
  const [platform, setPlatform] = useState<PlatformInfo | null>(null);
  const [job, setJob] = useState<PlatformJob | null>(null);
  const [files, setFiles] = useState<PlatformJobFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const found = (await getLineagePlatforms()).find((p) => p.key === platformKey) || null;
        setPlatform(found);
        if (!found || !id) return;
        const [jobData, filesData] = await Promise.all([
          getPlatformJob(found.id, Number(id)),
          getPlatformJobFiles(found.id, Number(id)),
        ]);
        setJob(jobData);
        setFiles(filesData);
      } catch (error) {
        toast.error('Failed to load job details');
        console.error(error);
        setJob(null);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [platformKey, id]);

  if (loading) return <LoadingSpinner />;

  const backTo = platform ? `/jobs?platform=${platform.key}` : '/jobs';
  const backLink = (
    <Link to={backTo} className="inline-flex items-center gap-1 text-sm text-gray-600 hover:text-gray-900">
      <FiArrowLeft size={15} /> {platform ? `${platform.name} jobs` : 'Jobs'}
    </Link>
  );

  if (!platform || !job) {
    return (
      <div className="space-y-4">
        {backLink}
        <div className="rounded-lg bg-white p-12 text-center shadow">
          <FiAlertCircle className="mx-auto mb-3 text-gray-400" size={36} />
          <p className="text-gray-600">Job not found</p>
        </div>
      </div>
    );
  }

  const facts: [string, React.ReactNode][] = [
    ['Owner', job.owner],
    ['Scheduler', job.scheduler_system],
    ['Schedule', job.schedule_name],
    ['Frequency', job.frequency],
    ['Job class', job.job_class],
    ['Last run', job.last_run ? `${formatTime(job.last_run)} (${relative(job.last_run)})` : null],
    ['Next run', job.next_run ? `${formatTime(job.next_run)} (${relative(job.next_run)})` : null],
    ['Last synced', job.last_synced ? relative(job.last_synced) : null],
  ];

  return (
    <div className="space-y-4">
      {backLink}

      <div className="flex flex-wrap items-start gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2.5">
            <h1 className="break-all font-mono text-2xl font-semibold tracking-tight text-gray-900">{job.job_name}</h1>
            {job.last_run_status && <RunStatusBadge status={job.last_run_status} />}
          </div>
          <p className="mt-1 flex items-center gap-2 text-sm text-gray-600">
            <span className="h-2 w-2 rounded-full" style={{ background: platform.color }} aria-hidden="true" />
            {platform.job_label} · {platform.name}
            {job.description && <span>· {job.description}</span>}
          </p>
        </div>
        <Link
          to={`/job-lineage?platform=${platform.key}`}
          className="ml-auto flex h-9 items-center gap-2 rounded-lg border border-gray-300 bg-white px-3.5 text-sm font-medium text-gray-800 hover:bg-gray-50"
        >
          <FiLayers size={15} /> Open lineage
        </Link>
      </div>

      {job.last_run_status === 'FAILED' && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <span className="font-semibold">Last run failed</span>
          {job.last_run_error && <span className="ml-2 break-words font-mono">{job.last_run_error}</span>}
        </div>
      )}

      <section className="rounded-lg bg-white p-4 shadow" aria-label="Job details">
        <dl className="grid gap-x-6 gap-y-3 text-sm" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          {facts.map(([label, value]) => (
            <div key={label}>
              <dt className="text-xs text-gray-600">{label}</dt>
              <dd className="mt-0.5 text-gray-900">{value || '—'}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="overflow-hidden rounded-lg bg-white shadow" aria-label="Datasets">
        <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3">
          <h2 className="text-[15px] font-semibold text-gray-900">Datasets</h2>
          <span className="text-xs text-gray-600">what this {platform.job_label.toLowerCase()} reads and writes</span>
        </div>
        {files.length === 0 ? (
          <p className="p-8 text-center text-sm text-gray-600">No datasets recorded for this job.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-600">
                <tr>
                  <th className="px-4 py-2.5">Direction</th>
                  <th className="px-4 py-2.5">Dataset</th>
                  <th className="px-4 py-2.5">Type</th>
                  <th className="px-4 py-2.5">Step / DD / port</th>
                  <th className="px-4 py-2.5">Disposition</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {files.map((f) => {
                  const direction = f.direction?.toUpperCase() || '';
                  return (
                    <tr key={f.id}>
                      <td className="px-4 py-3">
                        <span className={`rounded px-2 py-0.5 text-xs font-semibold ${DIRECTION_STYLE[direction] || 'bg-gray-100 text-gray-800'}`}>
                          {direction || 'N/A'}
                        </span>
                      </td>
                      <td className="break-all px-4 py-3 font-mono text-[13px] text-gray-900">{f.dataset_name}</td>
                      <td className="px-4 py-3 text-gray-700">{f.dataset_type || '—'}</td>
                      <td className="px-4 py-3 font-mono text-[13px] text-gray-700">{f.dd_name || '—'}</td>
                      <td className="px-4 py-3 text-gray-700">{f.disposition || '—'}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default JobDetail;
