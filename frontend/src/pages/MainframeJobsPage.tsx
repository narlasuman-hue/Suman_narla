import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { FiServer, FiRefreshCw, FiChevronRight } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { getMainframeJobs, syncMainframeJobs, MainframeJob } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

const statusBadge = (status: string) => {
  const active = status?.toLowerCase() === 'active';
  return (
    <span
      className={`px-2 py-1 rounded text-xs font-medium ${
        active ? 'bg-green-100 text-green-800' : 'bg-orange-100 text-orange-800'
      }`}
    >
      {status?.toUpperCase() || 'UNKNOWN'}
    </span>
  );
};

const MainframeJobsPage: React.FC = () => {
  const [jobs, setJobs] = useState<MainframeJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const loadJobs = async () => {
    try {
      setLoading(true);
      const data = await getMainframeJobs();
      setJobs(data);
    } catch (error) {
      toast.error('Failed to load mainframe jobs');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const handleSync = async () => {
    try {
      setSyncing(true);
      const stats = await syncMainframeJobs();
      toast.success(
        `Synced: ${stats.jobs_created} created, ${stats.jobs_updated} updated`
      );
      await loadJobs();
    } catch (error) {
      toast.error('Mainframe sync failed');
      console.error(error);
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <FiServer className="text-indigo-600" size={32} />
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Mainframe Jobs</h1>
            <p className="text-gray-600">Job details, files used, and schedule names</p>
          </div>
        </div>

        <button
          onClick={handleSync}
          disabled={syncing}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition disabled:opacity-50"
        >
          <FiRefreshCw className={syncing ? 'animate-spin' : ''} size={18} />
          {syncing ? 'Syncing...' : 'Sync from Mainframe'}
        </button>
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        {jobs.length === 0 ? (
          <div className="p-12 text-center text-gray-600">
            No mainframe jobs found. Click "Sync from Mainframe" to load jobs.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Job Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Owner</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Scheduler</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Schedule Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Files</th>
                  <th className="px-6 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y">
                {jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{job.job_name}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{job.owner || '-'}</td>
                    <td className="px-6 py-4 text-sm">{statusBadge(job.status)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{job.scheduler_system || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{job.schedule_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{job.file_count ?? 0}</td>
                    <td className="px-6 py-4 text-right">
                      <Link
                        to={`/mainframe/jobs/${job.id}`}
                        className="inline-flex items-center gap-1 text-indigo-600 hover:text-indigo-800 text-sm font-medium"
                      >
                        Details <FiChevronRight size={16} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default MainframeJobsPage;
