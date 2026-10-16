import React from 'react';
import { FiAlertTriangle, FiCrosshair, FiGitBranch, FiX } from 'react-icons/fi';
import { ColumnLineageEdge, ColumnLineageGraph, LineageColumn } from '../services/api';
import { RunStatusBadge, SlaBadge } from './lineageBadges';

interface ColumnDetailsPanelProps {
  lineage: ColumnLineageGraph;
  columnId: string;
  onTrace: (columnId: string) => void;
  onTableLineage: (datasetId: string) => void;
  onClose: () => void;
}

const MappingList: React.FC<{
  title: string;
  edges: ColumnLineageEdge[];
  other: (e: ColumnLineageEdge) => LineageColumn | undefined;
  onTrace: (columnId: string) => void;
}> = ({ title, edges, other, onTrace }) =>
  edges.length ? (
    <div>
      <p className="text-xs font-semibold uppercase text-gray-500 mb-1">{title}</p>
      <ul className="space-y-2">
        {edges.map((e) => {
          const col = other(e);
          return (
            <li key={e.id} className="text-sm border border-gray-200 rounded p-2">
              <button
                onClick={() => col && onTrace(col.id)}
                className="text-indigo-600 hover:underline text-left break-all"
              >
                {col ? `${col.dataset_name}.${col.column}` : '?'}
              </button>
              <div className="flex flex-wrap items-center gap-1.5 mt-1 text-xs text-gray-600">
                via <span className="font-medium text-gray-800">{e.job_name}</span>
                <RunStatusBadge status={e.run_status} />
              </div>
              {e.transformation && (
                <p className="mt-1 text-xs text-gray-700 bg-gray-50 rounded px-2 py-1 font-mono break-words">
                  {e.transformation}
                </p>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  ) : null;

/** Details of a column in the column lineage graph: where it comes from and where it goes. */
const ColumnDetailsPanel: React.FC<ColumnDetailsPanelProps> = ({
  lineage,
  columnId,
  onTrace,
  onTableLineage,
  onClose,
}) => {
  const byId = new Map(lineage.nodes.map((c) => [c.id, c]));
  const column = byId.get(columnId);
  if (!column) return null;
  const isFocus = columnId === lineage.focus.id;
  const incoming = lineage.edges.filter((e) => e.target === columnId);
  const outgoing = lineage.edges.filter((e) => e.source === columnId);

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-5 space-y-4">
      <div className="relative pr-6">
        <button onClick={onClose} title="Close" className="absolute top-0 right-0 text-gray-400 hover:text-gray-700">
          <FiX size={18} />
        </button>
        <p className="text-xs text-gray-500">Column · {column.database}</p>
        <h2 className="text-lg font-bold text-gray-900 break-all">{column.column}</h2>
        <p className="text-sm text-gray-600 break-all">{column.dataset_name}</p>
        {column.data_type && <p className="text-xs text-gray-500 mt-1">{column.data_type}</p>}
        {column.description && <p className="text-sm text-gray-600 mt-1">{column.description}</p>}
      </div>

      {isFocus && lineage.focus.loaded_by.length > 0 && (
        <div className="text-sm">
          <p className="text-xs font-semibold uppercase text-gray-500 mb-1">Table loaded by</p>
          {lineage.focus.loaded_by.map((j) => (
            <div key={j.id} className="flex flex-wrap items-center gap-1.5">
              <span className="font-medium">{j.name}</span>
              <RunStatusBadge status={j.run_status} />
              <SlaBadge status={j.sla_status} prefix="SLA: " />
            </div>
          ))}
        </div>
      )}

      {column.impacted && (
        <div className="flex gap-2 p-3 rounded bg-amber-50 border border-amber-200 text-sm text-amber-900">
          <FiAlertTriangle className="shrink-0 mt-0.5" />
          <span>Table impacted by upstream failure: {column.impacted_by.join(', ')}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {!isFocus && (
          <button
            onClick={() => onTrace(columnId)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-indigo-600 text-white hover:bg-indigo-700"
          >
            <FiCrosshair size={14} /> Trace this column
          </button>
        )}
        <button
          onClick={() => onTableLineage(column.dataset_id)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          <FiGitBranch size={14} /> Table lineage
        </button>
      </div>

      <MappingList title="Derived from" edges={incoming} other={(e) => byId.get(e.source)} onTrace={onTrace} />
      <MappingList title="Feeds" edges={outgoing} other={(e) => byId.get(e.target)} onTrace={onTrace} />
      {incoming.length === 0 && outgoing.length === 0 && (
        <p className="text-sm text-gray-500">No column mappings recorded for this column.</p>
      )}
    </div>
  );
};

export default ColumnDetailsPanel;
