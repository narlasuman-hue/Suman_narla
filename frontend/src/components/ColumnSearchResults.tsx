import React from 'react';
import { FiAlertTriangle, FiColumns, FiGitBranch, FiX } from 'react-icons/fi';
import { ColumnSearchResult } from '../services/api';
import { RunStatusBadge, SlaBadge } from './lineageBadges';

interface ColumnSearchResultsProps {
  query: string;
  exact: boolean;
  results: ColumnSearchResult[];
  loading: boolean;
  onColumnLineage: (columnId: string) => void;
  onTableLineage: (datasetId: string) => void;
  onClose: () => void;
}

/** Every table that has the searched column, with its database and load jobs. */
const ColumnSearchResults: React.FC<ColumnSearchResultsProps> = ({
  query,
  exact,
  results,
  loading,
  onColumnLineage,
  onTableLineage,
  onClose,
}) => {
  const tables = new Set(results.map((r) => r.dataset_id)).size;
  const databases = new Set(results.map((r) => r.database)).size;

  return (
    <div className="bg-white rounded-lg shadow">
      <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-200">
        <FiColumns className="text-indigo-600" size={18} />
        <p className="text-sm text-gray-800">
          {loading ? (
            'Searching…'
          ) : (
            <>
              Column <span className="font-semibold">{exact ? query : `*${query}*`}</span> found in{' '}
              <span className="font-semibold">{tables}</span> table{tables === 1 ? '' : 's'} across{' '}
              <span className="font-semibold">{databases}</span> database{databases === 1 ? '' : 's'}
            </>
          )}
        </p>
        <button onClick={onClose} title="Close" className="ml-auto text-gray-400 hover:text-gray-700">
          <FiX size={18} />
        </button>
      </div>
      {!loading && results.length === 0 ? (
        <p className="p-6 text-sm text-gray-600 text-center">No tables have a matching column.</p>
      ) : (
        <div className="overflow-x-auto max-h-80 overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-gray-700 sticky top-0">
              <tr>
                <th className="px-4 py-2 font-semibold">Table</th>
                {!exact && <th className="px-4 py-2 font-semibold">Column</th>}
                <th className="px-4 py-2 font-semibold">Database</th>
                <th className="px-4 py-2 font-semibold">Type</th>
                <th className="px-4 py-2 font-semibold">Loaded by (last run · SLA)</th>
                <th className="px-4 py-2 font-semibold">Read by</th>
                <th className="px-4 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {results.map((r) => (
                <tr key={r.id} className="hover:bg-gray-50">
                  <td className="px-4 py-2">
                    <p className="font-medium text-gray-900 break-all">{r.dataset_name}</p>
                    {r.impacted && (
                      <p className="flex items-center gap-1 text-xs text-amber-700">
                        <FiAlertTriangle /> impacted by {r.impacted_by.join(', ')}
                      </p>
                    )}
                  </td>
                  {!exact && <td className="px-4 py-2 font-medium">{r.column}</td>}
                  <td className="px-4 py-2 text-gray-700">{r.database}</td>
                  <td className="px-4 py-2 text-gray-600 whitespace-nowrap">{r.data_type || '-'}</td>
                  <td className="px-4 py-2">
                    {r.loaded_by.length ? (
                      r.loaded_by.map((j) => (
                        <div key={j.id} className="flex flex-wrap items-center gap-1.5">
                          <span className="font-medium">{j.name}</span>
                          <RunStatusBadge status={j.run_status} />
                          <SlaBadge status={j.sla_status} prefix="SLA: " />
                        </div>
                      ))
                    ) : (
                      <span className="text-xs text-gray-500">Source (not loaded by a job here)</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-gray-600">
                    {r.read_by.length ? r.read_by.map((j) => j.name).join(', ') : '-'}
                  </td>
                  <td className="px-4 py-2">
                    <div className="flex gap-1 justify-end whitespace-nowrap">
                      <button
                        onClick={() => onColumnLineage(r.id)}
                        className="px-2 py-1 text-xs rounded bg-indigo-600 text-white hover:bg-indigo-700"
                      >
                        Column lineage
                      </button>
                      <button
                        onClick={() => onTableLineage(r.dataset_id)}
                        title="Table lineage"
                        className="p-1.5 rounded border border-gray-300 text-gray-600 hover:bg-gray-50"
                      >
                        <FiGitBranch size={13} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default ColumnSearchResults;
