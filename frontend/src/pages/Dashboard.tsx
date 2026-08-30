import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  FiDatabase,
  FiTable,
  FiColumns,
  FiGitBranch,
  FiAlertCircle,
  FiClock,
  FiChevronRight,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getDatabases,
  getTables,
  getLifecycleSummary,
  getSummaryReport,
} from '../services/api';
import { StatCard } from '../components/StatCard';
import { LoadingSpinner } from '../components/LoadingSpinner';

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<any>(null);
  const [databases, setDatabases] = useState<any[]>([]);
  const [tables, setTables] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        setLoading(true);
        const [dbsData, tablesData, lifecycleData, summaryData] = await Promise.all([
          getDatabases(undefined, 0, 100),
          getTables(undefined, undefined, 0, 100),
          getLifecycleSummary(),
          getSummaryReport(),
        ]);

        setDatabases(dbsData.slice(0, 5));
        setTables(tablesData.slice(0, 5));

        setStats({
          databases: summaryData.total_databases || 0,
          tables: summaryData.total_tables || 0,
          columns: summaryData.total_columns || 0,
          activeAssets: lifecycleData.active || 0,
          deprecatedAssets: lifecycleData.deprecated || 0,
          decommissionedAssets: lifecycleData.decommissioned || 0,
        });
      } catch (error) {
        toast.error('Failed to load dashboard data');
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
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-gray-600">
          Welcome to the Database Metadata Catalog
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          title="Databases"
          value={stats?.databases || 0}
          icon={FiDatabase}
          color="blue"
        />
        <StatCard
          title="Tables"
          value={stats?.tables || 0}
          icon={FiTable}
          color="green"
        />
        <StatCard
          title="Columns"
          value={stats?.columns || 0}
          icon={FiColumns}
          color="purple"
        />
        <StatCard
          title="Active Assets"
          value={stats?.activeAssets || 0}
          icon={FiGitBranch}
          color="indigo"
        />
      </div>

      {/* Lifecycle Status */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Deprecated</p>
              <p className="text-2xl font-bold text-orange-600 mt-1">
                {stats?.deprecatedAssets || 0}
              </p>
            </div>
            <FiAlertCircle className="text-orange-500" size={32} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-600 text-sm font-medium">Decommissioned</p>
              <p className="text-2xl font-bold text-red-600 mt-1">
                {stats?.decommissionedAssets || 0}
              </p>
            </div>
            <FiClock className="text-red-500" size={32} />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <Link to="/lifecycle" className="flex items-center justify-between hover:opacity-80">
            <div>
              <p className="text-gray-600 text-sm font-medium">Lifecycle Status</p>
              <p className="text-sm text-blue-600 mt-2 font-medium">View details →</p>
            </div>
            <FiChevronRight className="text-blue-500" size={24} />
          </Link>
        </div>
      </div>

      {/* Recent Databases */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Recent Databases</h2>
            <Link
              to="/search"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all →
            </Link>
          </div>
        </div>

        <div className="divide-y">
          {databases.length > 0 ? (
            databases.map((db: any) => (
              <div key={db.id} className="p-6 hover:bg-gray-50 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <FiDatabase className="text-blue-500" size={24} />
                    <div>
                      <p className="font-medium text-gray-900">{db.name}</p>
                      <p className="text-sm text-gray-600">
                        {db.table_count || 0} tables • Owner: {db.owner || 'Unknown'}
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/databases/${db.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <FiChevronRight size={20} />
                  </Link>
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-gray-600">No databases found</div>
          )}
        </div>
      </div>

      {/* Recent Tables */}
      <div className="bg-white rounded-lg shadow">
        <div className="border-b border-gray-200 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">Recent Tables</h2>
            <Link
              to="/search"
              className="text-sm text-blue-600 hover:text-blue-700 font-medium"
            >
              View all →
            </Link>
          </div>
        </div>

        <div className="divide-y">
          {tables.length > 0 ? (
            tables.map((table: any) => (
              <div key={table.id} className="p-6 hover:bg-gray-50 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <FiTable className="text-green-500" size={24} />
                    <div>
                      <p className="font-medium text-gray-900">{table.name}</p>
                      <p className="text-sm text-gray-600">
                        {table.row_count || 0} rows • {table.column_count || 0} columns •{' '}
                        {table.size_mb || 0}MB
                      </p>
                    </div>
                  </div>
                  <Link
                    to={`/tables/${table.id}`}
                    className="text-blue-600 hover:text-blue-700"
                  >
                    <FiChevronRight size={20} />
                  </Link>
                </div>
              </div>
            ))
          ) : (
            <div className="p-6 text-center text-gray-600">No tables found</div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            to="/search"
            className="p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition"
          >
            <FiSearch className="text-blue-600 mb-2" size={24} />
            <p className="font-medium text-gray-900">Search Assets</p>
            <p className="text-sm text-gray-600">Find tables, columns, and more</p>
          </Link>

          <Link
            to="/lifecycle"
            className="p-4 border border-gray-200 rounded-lg hover:bg-orange-50 hover:border-orange-300 transition"
          >
            <FiClock className="text-orange-600 mb-2" size={24} />
            <p className="font-medium text-gray-900">Lifecycle Management</p>
            <p className="text-sm text-gray-600">Deprecate or decommission assets</p>
          </Link>

          <Link
            to="/reports"
            className="p-4 border border-gray-200 rounded-lg hover:bg-green-50 hover:border-green-300 transition"
          >
            <FiGitBranch className="text-green-600 mb-2" size={24} />
            <p className="font-medium text-gray-900">View Reports</p>
            <p className="text-sm text-gray-600">Analytics and insights</p>
          </Link>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
