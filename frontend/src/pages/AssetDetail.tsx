import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  FiTable,
  FiDatabase,
  FiChevronRight,
  FiBarChart2,
  FiGitBranch,
  FiAlertCircle,
} from 'react-icons/fi';
import toast from 'react-hot-toast';
import {
  getTable,
  getTableColumns,
  getDatabase,
  getTableUsage,
} from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';

interface AssetDetailProps {
  assetType: 'table' | 'database';
}

const AssetDetail: React.FC<AssetDetailProps> = ({ assetType }) => {
  const { id } = useParams<{ id: string }>();
  const [asset, setAsset] = useState<any>(null);
  const [columns, setColumns] = useState<any[]>([]);
  const [usage, setUsage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      if (!id) return;

      try {
        setLoading(true);

        if (assetType === 'table') {
          const tableData = await getTable(parseInt(id));
          setAsset(tableData);

          const columnsData = await getTableColumns(parseInt(id));
          setColumns(columnsData);

          try {
            const usageData = await getTableUsage(parseInt(id));
            setUsage(usageData);
          } catch (error) {
            console.warn('Failed to load usage data', error);
          }
        } else if (assetType === 'database') {
          const dbData = await getDatabase(parseInt(id));
          setAsset(dbData);
        }
      } catch (error) {
        toast.error(`Failed to load ${assetType} details`);
        console.error(error);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [id, assetType]);

  if (loading) {
    return <LoadingSpinner />;
  }

  if (!asset) {
    return (
      <div className="bg-white rounded-lg shadow p-12 text-center">
        <FiAlertCircle className="mx-auto text-gray-400 mb-4" size={48} />
        <p className="text-gray-600">{assetType} not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 mb-4">
        {assetType === 'table' ? (
          <FiTable className="text-green-600" size={32} />
        ) : (
          <FiDatabase className="text-blue-600" size={32} />
        )}
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{asset.name}</h1>
          <p className="text-gray-600">{asset.database || 'Database Metadata Catalog'}</p>
        </div>
      </div>

      {/* Main Info */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Details</h2>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Status</p>
            <p className="text-lg font-semibold text-gray-900 mt-1">
              <span
                className={`px-2 py-1 rounded text-sm font-medium ${
                  asset.status === 'active'
                    ? 'bg-green-100 text-green-800'
                    : 'bg-orange-100 text-orange-800'
                }`}
              >
                {asset.status?.toUpperCase() || 'ACTIVE'}
              </span>
            </p>
          </div>

          {assetType === 'table' && (
            <>
              <div>
                <p className="text-gray-600 text-sm">Type</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">{asset.type || 'TABLE'}</p>
              </div>

              <div>
                <p className="text-gray-600 text-sm">Row Count</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {asset.row_count?.toLocaleString() || 0}
                </p>
              </div>

              <div>
                <p className="text-gray-600 text-sm">Size</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {asset.size_mb || 0} MB
                </p>
              </div>
            </>
          )}

          {assetType === 'database' && (
            <>
              <div>
                <p className="text-gray-600 text-sm">Tables</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {asset.table_count || 0}
                </p>
              </div>

              <div>
                <p className="text-gray-600 text-sm">Owner</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {asset.owner || 'Unknown'}
                </p>
              </div>

              <div>
                <p className="text-gray-600 text-sm">Last Synced</p>
                <p className="text-lg font-semibold text-gray-900 mt-1">
                  {asset.last_synced ? new Date(asset.last_synced).toLocaleDateString() : 'Never'}
                </p>
              </div>
            </>
          )}
        </div>

        {asset.description && (
          <div className="mt-6 pt-6 border-t">
            <p className="text-gray-600 text-sm">Description</p>
            <p className="text-gray-900 mt-2">{asset.description}</p>
          </div>
        )}
      </div>

      {/* Timestamps */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Timeline</h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Created</p>
            <p className="text-gray-900 font-semibold mt-1">
              {asset.created_at
                ? new Date(asset.created_at).toLocaleDateString()
                : 'Unknown'}
            </p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Last Accessed</p>
            <p className="text-gray-900 font-semibold mt-1">
              {asset.last_accessed
                ? new Date(asset.last_accessed).toLocaleDateString()
                : 'Never'}
            </p>
          </div>

          <div>
            <p className="text-gray-600 text-sm">Last Synced</p>
            <p className="text-gray-900 font-semibold mt-1">
              {asset.last_synced
                ? new Date(asset.last_synced).toLocaleDateString()
                : 'Never'}
            </p>
          </div>
        </div>
      </div>

      {/* Columns (for tables) */}
      {assetType === 'table' && columns.length > 0 && (
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="border-b border-gray-200 p-6">
            <h2 className="text-lg font-bold text-gray-900">Columns ({columns.length})</h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Name</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">Type</th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Nullable
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Sensitive
                  </th>
                  <th className="px-6 py-3 text-left text-sm font-semibold text-gray-900">
                    Description
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y">
                {columns.map((column) => (
                  <tr key={column.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 text-sm font-medium text-gray-900">
                      {column.name}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">{column.data_type}</td>
                    <td className="px-6 py-4 text-sm">
                      <span
                        className={`px-2 py-1 rounded text-xs font-medium ${
                          column.nullable
                            ? 'bg-green-100 text-green-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}
                      >
                        {column.nullable ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm">
                      {column.sensitive ? (
                        <span className="px-2 py-1 rounded text-xs font-medium bg-orange-100 text-orange-800">
                          Yes
                        </span>
                      ) : (
                        <span className="text-gray-600">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-600">
                      {column.description || '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Related Actions */}
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-bold text-gray-900 mb-4">Related Actions</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {assetType === 'table' && (
            <>
              <Link
                to={`/lineage/${id}`}
                className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition"
              >
                <div className="flex items-center gap-3">
                  <FiGitBranch className="text-blue-600" size={20} />
                  <div>
                    <p className="font-medium text-gray-900">View Lineage</p>
                    <p className="text-sm text-gray-600">Upstream and downstream dependencies</p>
                  </div>
                </div>
                <FiChevronRight className="text-gray-400" size={20} />
              </Link>

              <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-green-50 hover:border-green-300 transition cursor-pointer">
                <div className="flex items-center gap-3">
                  <FiBarChart2 className="text-green-600" size={20} />
                  <div>
                    <p className="font-medium text-gray-900">View Usage</p>
                    <p className="text-sm text-gray-600">Query patterns and performance</p>
                  </div>
                </div>
                <FiChevronRight className="text-gray-400" size={20} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default AssetDetail;
