import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { FiServer, FiAlertCircle, FiArrowLeft, FiCalendar, FiFile } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getMainframeJob,
  getMainframeJobFiles,
  MainframeJob,
  MainframeJobFile,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

const directionBadge = (direction?: string) => {
  const isInput = direction?.toUpperCase() === 'INPUT';
  const isOutput = direction?.toUpperCase() === 'OUTPUT';
  const style = isInput
    ? 'bg-blue-100 text-blue-800'
    : isOutput
    ? 'bg-purple-100 text-purple-800'
    : 'bg-gray-100 text-gray-800';
  return (
    <span className={`px-2 py-1 rounded text-xs font-medium ${style}`}>
      {direction?.toUpperCase() || 'N/A'}
    </span>
  );
};

const MainframeJobDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<MainframeJob | null>(null);
  const [files, setFiles] = useState<MainframeJobFile[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;
      try {
        setLoading(true);
        const jobData = await getMainframeJob(parseInt(id));
        setJob(jobData);

        const filesData = await getMainframeJobFiles(parseInt(id));
        setFiles(filesData);
      } catch (error) {
        toast.error('Failed to load mainframe job details');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!job) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <FiAlertCircle className="mx-auto text-gray-400 mb-4" size={48} />
        <p className="text-gray-600">Mainframe job not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Link
        to="/mainframe"
        className="inline-flex items-center gap-1 text-gray-600 hover:text-gray-900 text-sm"
      >
        <FiArrowLeft size={16} /> Back to Mainframe Jobs
      </Link>

      <div className="flex items-center gap-3">
        <FiServer className="text-indigo-600" size={32} />
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{job.job_name}</h1>
          <p className="text-gray-600">{job.description || 'Mainframe batch job'}</p>
        </div>
      </div>

      {/* Job Details */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Job Details</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Status</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">
              <span
                className={`px-2 py-1 rounded text-sm font-medium ${
                  job.status?.toLowerCase() === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-orange-100 text-orange-800'
                }`}
              >
                {job.status?.toUpperCase() || 'UNKNOWN'}
              </span>
            </p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Owner</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{job.owner || 'Unknown'}</p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Job Class</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{job.job_class || '-'}</p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Files Used</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{files.length}</p>
          </div>
        </div>
      </div>

      {/* Schedule */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center gap-2 mb-4">
          <FiCalendar className="text-indigo-600" size={20} />
          <h2 className="text-lg font-bold text-gray-900">Schedule</h2>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Scheduler System</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{job.scheduler_system || '-'}</p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Schedule Name</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{job.schedule_name || '-'}</p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Frequency</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">{job.frequency || '-'}</p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Next Run</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">
              {job.next_run ? new Date(job.next_run).toLocaleString() : 'Unknown'}
            </p>
          </div>
        </div>

        <div className="mt-4 pt-4 border-t">
          <p className="text-gray-600 text-sm">Last Run</p>
          <p className="text-gray-900 font-semibold mt-1">
            {job.last_run ? new Date(job.last_run).toLocaleString() : 'Never'}
          </p>
        </div>
      </div>

      {/* Files Used */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="border-b border-gray-200 p-6 flex items-center gap-2">
          <FiFile className="text-indigo-600" size={20} />
          <h2 className="text-lg font-bold text-gray-900">Files Used ({files.length})</h2>
        </div>

        {files.length === 0 ? (
          <div className="p-6 text-center text-gray-600">No files recorded for this job.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">DD Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Dataset Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Direction</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Disposition</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Type</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Volume</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {files.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">{file.dd_name || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-600 font-mono">{file.dataset_name}</td>
                    <td className="px-6 py-4 text-sm">{directionBadge(file.direction)}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{file.disposition || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{file.dataset_type || '-'}</td>
                    <td className="px-6 py-4 text-sm text-gray-600">{file.volume_serial || '-'}</td>
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

export default MainframeJobDetail;
