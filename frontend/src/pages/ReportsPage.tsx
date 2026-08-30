import React, { useEffect, useState } from 'react';
import {
  FiBarChart2,
  FiTrendingUp,
  FiDatabase,
  FiHardDrive,
  FiCheck,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getSummaryReport,
  getAssetAgeReport,
  getStorageUsageReport,
  getMostUsedTables,
  getDataQualityScore,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';

const ReportsPage: React.FC = () => {
  const [reports, setReports] = useState<any>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadReports = async () => {
      try {
        setLoading(true);

        const [summary, assetAge, storage, mostUsed, qualityScore] = await Promise.all([
          getSummaryReport().catch(() => ({})),
          getAssetAgeReport().catch(() => ({})),
          getStorageUsageReport().catch(() => ({})),
          getMostUsedTables(20).catch(() => []),
          getDataQualityScore().catch(() => ({})),
        ]);

        setReports({
          summary,
          assetAge,
          storage,
          mostUsed,
          qualityScore,
        });
      } catch (error) {
        toast.error('Failed to load reports');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadReports();
  }, []);

  if (loading) {
    return <LoadingSpinner />;
  }

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="mt-1 text-gray-600">
          View comprehensive statistics and insights about your database catalog
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        {reports.summary && (
          <>
            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Databases</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {reports.summary.total_databases || 0}
                  </p>
                </div>
                <FiDatabase className="text-blue-500" size={28} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Tables</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {reports.summary.total_tables || 0}
                  </p>
                </div>
                <FiTrendingUp className="text-green-500" size={28} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Columns</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {reports.summary.total_columns || 0}
                  </p>
                </div>
                <FiBarChart2 className="text-purple-500" size={28} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Total Size</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {(
                      ((reports.summary.total_size_mb || 0) / 1024).toFixed(1)
                    ).toLocaleString()}
                    GB
                  </p>
                </div>
                <FiHardDrive className="text-orange-500" size={28} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-600 text-sm">Data Quality</p>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {reports.qualityScore?.score || 0}%
                  </p>
                </div>
                <FiCheck className="text-green-500" size={28} />
              </div>
            </div>
          </>
        )}
      </div>

      {/* Most Used Tables Chart */}
      {reports.mostUsed && reports.mostUsed.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Most Used Tables</h2>

          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={reports.mostUsed}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="name"
                angle={-45}
                textAnchor="end"
                height={80}
                interval={0}
              />
              <YAxis />
              <Tooltip />
              <Bar dataKey="query_count" fill="#3b82f6" name="Query Count" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Storage Usage */}
      {reports.storage && reports.storage.by_database && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Storage by Database</h2>

            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={reports.storage.by_database}
                  dataKey="size_mb"
                  nameKey="database"
                  cx="50%"
                  cy="50%"
                  outerRadius={100}
                  label
                >
                  {reports.storage.by_database.map((_: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Database Details</h2>

            <div className="space-y-3 max-h-80 overflow-y-auto">
              {reports.storage.by_database?.map((db: any, idx: number) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded">
                  <div className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded"
                      style={{ backgroundColor: COLORS[idx % COLORS.length] }}
                    ></div>
                    <span className="font-medium text-gray-900">{db.database}</span>
                  </div>
                  <span className="text-gray-600 text-sm">
                    {((db.size_mb / 1024).toFixed(1)).toLocaleString()}GB
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Asset Age Distribution */}
      {reports.assetAge && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Asset Age Distribution</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-gray-600 text-sm">Less than 30 days</p>
              <p className="text-2xl font-bold text-green-700 mt-1">
                {reports.assetAge.less_than_30_days || 0}
              </p>
            </div>

            <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
              <p className="text-gray-600 text-sm">30 - 90 days</p>
              <p className="text-2xl font-bold text-yellow-700 mt-1">
                {reports.assetAge.thirty_to_ninety_days || 0}
              </p>
            </div>

            <div className="p-4 bg-red-50 rounded-lg border border-red-200">
              <p className="text-gray-600 text-sm">More than 90 days</p>
              <p className="text-2xl font-bold text-red-700 mt-1">
                {reports.assetAge.more_than_ninety_days || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quality Score Details */}
      {reports.qualityScore && (
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Data Quality Details</h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-gray-600 text-sm">Completeness</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {reports.qualityScore.completeness || 0}%
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-green-500 h-2 rounded-full"
                  style={{
                    width: `${reports.qualityScore.completeness || 0}%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-gray-600 text-sm">Accuracy</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {reports.qualityScore.accuracy || 0}%
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-blue-500 h-2 rounded-full"
                  style={{
                    width: `${reports.qualityScore.accuracy || 0}%`,
                  }}
                ></div>
              </div>
            </div>

            <div className="p-4 border border-gray-200 rounded-lg">
              <p className="text-gray-600 text-sm">Consistency</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {reports.qualityScore.consistency || 0}%
              </p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="bg-purple-500 h-2 rounded-full"
                  style={{
                    width: `${reports.qualityScore.consistency || 0}%`,
                  }}
                ></div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ReportsPage;
