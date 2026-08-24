import React, { useEffect, useState } from 'react';
import {
  FiClock,
  FiAlertCircle,
  FiCheckCircle,
  FiTrash2,
  FiChevronRight,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getLifecycleSummary,
  getUnusedAssets,
  getDecommissioningCandidates,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Link } from 'react-router-dom';

const LifecyclePage: React.FC = () => {
  const [summary, setSummary] = useState<any>(null);
  const [unusedAssets, setUnusedAssets] = useState<any[]>([]);
  const [decommissioningCandidates, setDecommissioningCandidates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedTab, setSelectedTab] = useState<'summary' | 'unused' | 'candidates'>(
    'summary'
  );

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);

        const [summaryData, unusedData, candidatesData] = await Promise.all([
          getLifecycleSummary().catch(() => ({})),
          getUnusedAssets(90).catch(() => []),
          getDecommissioningCandidates(180).catch(() => []),
        ]);

        setSummary(summaryData);
        setUnusedAssets(unusedData);
        setDecommissioningCandidates(candidatesData);
      } catch (error) {
        toast.error('Failed to load lifecycle data');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Asset Lifecycle Management</h1>
        <p className="mt-1 text-gray-600">
          Track and manage the lifecycle of your database assets
        </p>
      </div>

      {/* Status Cards */}
      {summary && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-green-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Active Assets</p>
                <p className="text-3xl font-bold text-green-600 mt-1">
                  {summary.active || 0}
                </p>
              </div>
              <FiCheckCircle className="text-green-500" size={32} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-yellow-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Inactive Assets</p>
                <p className="text-3xl font-bold text-yellow-600 mt-1">
                  {summary.inactive || 0}
                </p>
              </div>
              <FiClock className="text-yellow-500" size={32} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-orange-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Deprecated Assets</p>
                <p className="text-3xl font-bold text-orange-600 mt-1">
                  {summary.deprecated || 0}
                </p>
              </div>
              <FiAlertCircle className="text-orange-500" size={32} />
            </div>
          </div>

          <div className="bg-white rounded-lg shadow p-6 border-l-4 border-red-500">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-600 text-sm">Decommissioned</p>
                <p className="text-3xl font-bold text-red-600 mt-1">
                  {summary.decommissioned || 0}
                </p>
              </div>
              <FiTrash2 className="text-red-500" size={32} />
            </div>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="bg-white rounded-lg shadow border-b border-gray-200">
        <div className="flex">
          {['summary', 'unused', 'candidates'].map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab as any)}
              className={`flex-1 px-6 py-4 font-medium text-center transition ${
                selectedTab === tab
                  ? 'border-b-2 border-blue-600 text-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              {tab === 'summary' && 'Summary'}
              {tab === 'unused' && `Unused Assets (${unusedAssets.length})`}
              {tab === 'candidates' && `Decommissioning Candidates (${decommissioningCandidates.length})`}
            </button>
          ))}
        </div>
      </div>

      {/* Tab Content */}
      {selectedTab === 'summary' && (
        <div className="space-y-6">
          {/* Lifecycle Information */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Asset Lifecycle States</h2>

            <div className="space-y-4">
              <div className="flex items-start gap-4 p-4 bg-green-50 rounded-lg border border-green-200">
                <FiCheckCircle className="text-green-600 mt-1 flex-shrink-0" size={24} />
                <div>
                  <h3 className="font-semibold text-gray-900">Active</h3>
                  <p className="text-gray-600 text-sm mt-1">
                    Assets that are currently in use and actively maintained
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                <FiClock className="text-yellow-600 mt-1 flex-shrink-0" size={24} />
                <div>
                  <h3 className="font-semibold text-gray-900">Inactive</h3>
                  <p className="text-gray-600 text-sm mt-1">
                    Assets that haven't been used recently but are still available
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 bg-orange-50 rounded-lg border border-orange-200">
                <FiAlertCircle className="text-orange-600 mt-1 flex-shrink-0" size={24} />
                <div>
                  <h3 className="font-semibold text-gray-900">Deprecated</h3>
                  <p className="text-gray-600 text-sm mt-1">
                    Assets marked for future removal with a deprecation warning
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-4 p-4 bg-red-50 rounded-lg border border-red-200">
                <FiTrash2 className="text-red-600 mt-1 flex-shrink-0" size={24} />
                <div>
                  <h3 className="font-semibold text-gray-900">Decommissioned</h3>
                  <p className="text-gray-600 text-sm mt-1">
                    Assets that have been fully removed from service
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* Lifecycle Management Tips */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Best Practices</h2>

            <ul className="space-y-3 text-gray-700">
              <li className="flex gap-2">
                <span className="font-bold text-blue-600">1.</span>
                <span>Regularly review unused assets to identify deprecation candidates</span>
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-blue-600">2.</span>
                <span>Deprecate assets before decommissioning to allow dependent systems to adapt</span>
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-blue-600">3.</span>
                <span>Check impact analysis before decommissioning critical assets</span>
              </li>
              <li className="flex gap-2">
                <span className="font-bold text-blue-600">4.</span>
                <span>Document deprecation reasons for compliance and tracking</span>
              </li>
            </ul>
          </div>
        </div>
      )}

      {selectedTab === 'unused' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">
              Unused Assets (No access in 90+ days)
            </h2>
          </div>

          {unusedAssets.length > 0 ? (
            <div className="divide-y">
              {unusedAssets.map((asset: any) => (
                <div key={asset.id} className="p-6 hover:bg-gray-50 transition">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-bold text-gray-900 text-lg">{asset.name}</p>
                      <div className="flex gap-4 text-sm text-gray-600 mt-2">
                        <span>Database: {asset.database}</span>
                        <span>
                          Last Accessed:{' '}
                          {asset.last_accessed
                            ? new Date(asset.last_accessed).toLocaleDateString()
                            : 'Never'}
                        </span>
                        <span>Type: {asset.type || 'TABLE'}</span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Link
                        to={`/tables/${asset.id}`}
                        className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition text-sm font-medium flex items-center gap-2"
                      >
                        View Details
                        <FiChevronRight size={16} />
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center text-gray-600">
              <p>No unused assets found</p>
            </div>
          )}
        </div>
      )}

      {selectedTab === 'candidates' && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="p-6 border-b border-gray-200">
            <h2 className="text-lg font-bold text-gray-900">
              Decommissioning Candidates (No access in 180+ days)
            </h2>
          </div>

          {decommissioningCandidates.length > 0 ? (
            <div className="divide-y">
              {decommissioningCandidates.map((asset: any) => (
                <div key={asset.id} className="p-6 hover:bg-gray-50 transition border-l-4 border-red-500">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-bold text-gray-900 text-lg">{asset.name}</p>
                      <div className="flex gap-4 text-sm text-gray-600 mt-2">
                        <span>Database: {asset.database}</span>
                        <span>
                          Last Accessed:{' '}
                          {asset.last_accessed
                            ? new Date(asset.last_accessed).toLocaleDateString()
                            : 'Never'}
                        </span>
                        <span>Size: {asset.size_mb || 0}MB</span>
                      </div>
                      {asset.row_count && (
                        <div className="text-sm text-gray-500 mt-2">
                          Rows: {asset.row_count.toLocaleString()}
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <Link
                        to={`/tables/${asset.id}`}
                        className="px-4 py-2 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition text-sm font-medium flex items-center gap-2"
                      >
                        Review for Decommission
                        <FiChevronRight size={16} />
                      </Link>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="p-12 text-center text-gray-600">
              <p>No decommissioning candidates found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default LifecyclePage;
