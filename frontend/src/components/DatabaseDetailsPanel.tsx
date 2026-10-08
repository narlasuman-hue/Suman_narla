import React from 'react';
import { FiAlertTriangle, FiDatabase, FiX } from 'react-icons/fi';
import { LineageDatasetNode, LineageEdge } from '../services/api';
import { DatabaseView } from '../utils/lineageViews';

interface DatabaseDetailsPanelProps {
  databaseId: string;
  view: DatabaseView;
  onTableSelect: (datasetId: string) => void;
  onDatabaseSelect: (databaseId: string) => void;
  onClose: () => void;
}

const Flows: React.FC<{
  title: string;
  edges: LineageEdge[];
  other: (e: LineageEdge) => string;
  names: Map<string, string>;
  onSelect: (id: string) => void;
}> = ({ title, edges, other, names, onSelect }) =>
  edges.length ? (
    <div>
      <p className="text-xs font-semibold uppercase text-gray-500 mb-1">{title}</p>
      <ul className="space-y-1">
        {edges.map((e) => (
          <li key={e.id} className="text-sm flex items-center justify-between gap-2">
            <button onClick={() => onSelect(other(e))} className="text-indigo-600 hover:underline break-all text-left">
              {names.get(other(e))}
            </button>
            <span className={`text-xs shrink-0 ${e.status === 'FAILED' ? 'text-red-700' : 'text-gray-500'}`}>
              {e.label}
            </span>
          </li>
        ))}
      </ul>
    </div>
  ) : null;

/** A database in the database-level view: its tables and which databases feed it. */
const DatabaseDetailsPanel: React.FC<DatabaseDetailsPanelProps> = ({
  databaseId,
  view,
  onTableSelect,
  onDatabaseSelect,
  onClose,
}) => {
  const db = view.nodes.find((n) => n.id === databaseId);
  if (!db) return null;
  const tables: LineageDatasetNode[] = view.members.get(databaseId) || [];
  const names = new Map(view.nodes.map((n) => [n.id, n.name]));

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-5 space-y-4">
      <div className="relative pr-6">
        <button onClick={onClose} title="Close" className="absolute top-0 right-0 text-gray-400 hover:text-gray-700">
          <FiX size={18} />
        </button>
        <p className="flex items-center gap-1 text-xs text-gray-500">
          <FiDatabase /> Database
        </p>
        <h2 className="text-lg font-bold text-gray-900 break-all">{db.name}</h2>
      </div>

      {db.impacted && (
        <div className="flex gap-2 p-3 rounded bg-amber-50 border border-amber-200 text-sm text-amber-900">
          <FiAlertTriangle className="shrink-0 mt-0.5" />
          <span>Has tables impacted by: {db.impacted_by.join(', ')}</span>
        </div>
      )}

      <Flows
        title="Fed by"
        edges={view.edges.filter((e) => e.target === databaseId)}
        other={(e) => e.source}
        names={names}
        onSelect={onDatabaseSelect}
      />
      <Flows
        title="Feeds"
        edges={view.edges.filter((e) => e.source === databaseId)}
        other={(e) => e.target}
        names={names}
        onSelect={onDatabaseSelect}
      />

      <div>
        <p className="text-xs font-semibold uppercase text-gray-500 mb-1">
          Tables ({tables.length}) · click for table lineage
        </p>
        <ul className="border border-gray-200 rounded divide-y divide-gray-100">
          {tables.map((t) => (
            <li key={t.id}>
              <button
                onClick={() => onTableSelect(t.id)}
                className="w-full flex items-center justify-between gap-2 px-2 py-1.5 text-left hover:bg-indigo-50"
              >
                <span className="text-sm text-gray-900 break-all">{t.name}</span>
                <span className="flex items-center gap-1 text-xs text-gray-500 shrink-0">
                  {t.impacted && <FiAlertTriangle className="text-amber-600" />}
                  {t.dataset_type}
                </span>
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
};

export default DatabaseDetailsPanel;
