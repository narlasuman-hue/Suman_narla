import React, { useEffect, useState } from 'react';
import { FiBarChart2, FiTrendingUp, FiUsers } from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getHeavyUsers,
  parseQueryLogs,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';

const QueryAnalysisPage: React.FC = () => {
  const [heavyUsers, setHeavyUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const users = await getHeavyUsers().catch(() => []);
        setHeavyUsers(users);
      } catch (error) {
        toast.error('Failed to load query analysis data');
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const handleParseQueryLogs = async () => {
    try {
      setAnalyzing(true);
      await parseQueryLogs(24);
      toast.success('Query logs parsed successfully');
    } catch (error) {
      toast.error('Failed to parse query logs');
      console.error(error);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return <LoadingSpinner />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Query Analysis</h1>
        <p className="mt-1 text-gray-600">
          Analyze query patterns, usage trends, and identify heavy users
        </p>
      </div>

      {/* Query Log Analysis */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-bold text-gray-900">Query Log Parser</h2>
            <p className="text-gray-600 text-sm mt-1">
              Analyze query logs from the last 24 hours to update usage metrics
            </p>
          </div>

          <button
            onClick={handleParseQueryLogs}
            disabled={analyzing}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-medium transition"
          >
            {analyzing ? 'Analyzing...' : 'Parse Query Logs'}
          </button>
        </div>
      </div>

      {/* Heavy Users Section */}
      {heavyUsers.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Heavy Users Chart */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <FiUsers className="text-purple-600" size={20} />
              Top Users by Query Count
            </h2>

            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={heavyUsers.slice(0, 10).map((user: any) => ({
                  name: user.user_name || user.username,
                  queries: user.query_count || 0,
                }))}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
                <YAxis />
                <Tooltip />
                <Bar dataKey="queries" fill="#a855f7" name="Queries" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Users List */}
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">User Details</h2>

            <div className="space-y-3 max-h-96 overflow-y-auto">
              {heavyUsers.slice(0, 15).map((user: any, idx: number) => (
                <div
                  key={idx}
                  className="p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-semibold text-gray-900">
                        {user.user_name || user.username}
                      </p>
                      <p className="text-xs text-gray-600 mt-1">
                        {user.query_count || 0} queries
                        {user.avg_duration && ` • Avg: ${user.avg_duration}ms`}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-purple-600">
                        {user.query_count || 0}
                      </p>
                      <p className="text-xs text-gray-600">queries</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Query Statistics Info Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Total Users</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{heavyUsers.length}</p>
            </div>
            <FiUsers className="text-blue-500" size={28} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Top User Queries</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {heavyUsers[0]?.query_count || 0}
              </p>
            </div>
            <FiBarChart2 className="text-green-500" size={28} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm">Avg Queries per User</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">
                {(
                  (heavyUsers.reduce((sum: number, u: any) => sum + (u.query_count || 0), 0) /
                    heavyUsers.length) || 0
                ).toFixed(0)}
              </p>
            </div>
            <FiTrendingUp className="text-orange-500" size={28} />
          </div>
        </div>
      </div>

      {/* Query Patterns Information */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Understanding Query Analysis</h2>

        <div className="space-y-4 text-gray-700">
          <div className="border-l-4 border-blue-500 pl-4">
            <p className="font-semibold text-gray-900">Query Count</p>
            <p className="text-sm text-gray-600 mt-1">
              Total number of queries executed by each user in the analysis period
            </p>
          </div>

          <div className="border-l-4 border-green-500 pl-4">
            <p className="font-semibold text-gray-900">Heavy Users</p>
            <p className="text-sm text-gray-600 mt-1">
              Users with the highest query volume, helpful for identifying power users
            </p>
          </div>

          <div className="border-l-4 border-purple-500 pl-4">
            <p className="font-semibold text-gray-900">Query Patterns</p>
            <p className="text-sm text-gray-600 mt-1">
              Analyze how tables and columns are used by queries to optimize performance
            </p>
          </div>

          <div className="border-l-4 border-orange-500 pl-4">
            <p className="font-semibold text-gray-900">Performance Metrics</p>
            <p className="text-sm text-gray-600 mt-1">
              Track query execution times and resource consumption for capacity planning
            </p>
          </div>
        </div>
      </div>

      {/* Usage Tips */}
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-6">
        <h2 className="text-lg font-bold text-blue-900 mb-4">Tips for Using Query Analysis</h2>

        <ul className="space-y-2 text-blue-800 text-sm">
          <li className="flex gap-2">
            <span className="font-bold">•</span>
            <span>Identify heavy users to understand data consumption patterns</span>
          </li>
          <li className="flex gap-2">
            <span className="font-bold">•</span>
            <span>Use query patterns to optimize table indexes and partitioning</span>
          </li>
          <li className="flex gap-2">
            <span className="font-bold">•</span>
            <span>Monitor performance metrics to detect slow queries</span>
          </li>
          <li className="flex gap-2">
            <span className="font-bold">•</span>
            <span>Regularly update query logs to keep analysis current</span>
          </li>
        </ul>
      </div>
    </div>
  );
};

export default QueryAnalysisPage;
