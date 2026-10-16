import React, { useEffect, useState } from 'react';
import { FiChevronRight } from 'react-icons/fi';
import { getLineageTableColumns, LineageColumn, LineagePlatform } from '../services/api';

interface TableColumnsListProps {
  platform: LineagePlatform;
  datasetId: string;
  onColumnSelect: (columnId: string) => void;
}

/** Columns of a table in the details panel; clicking one opens its column lineage. */
const TableColumnsList: React.FC<TableColumnsListProps> = ({ platform, datasetId, onColumnSelect }) => {
  const [columns, setColumns] = useState<LineageColumn[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setColumns(null);
    getLineageTableColumns(platform, datasetId)
      .then((data) => !cancelled && setColumns(data))
      .catch((error) => {
        console.error(error);
        if (!cancelled) setColumns([]);
      });
    return () => {
      cancelled = true;
    };
  }, [platform, datasetId]);

  if (columns === null) return <p className="text-xs text-gray-500">Loading columns…</p>;
  if (columns.length === 0) {
    return <p className="text-xs text-gray-500">No column information for this table.</p>;
  }

  return (
    <div>
      <p className="text-xs font-semibold uppercase text-gray-500 mb-1">
        Columns ({columns.length}) · click for column lineage
      </p>
      <ul className="border border-gray-200 rounded divide-y divide-gray-100 max-h-56 overflow-y-auto">
        {columns.map((c) => {
          const linked = (c.upstream_columns || 0) + (c.downstream_columns || 0) > 0;
          return (
            <li key={c.id}>
              <button
                onClick={() => onColumnSelect(c.id)}
                className="w-full flex items-center justify-between gap-2 px-2 py-1.5 text-left hover:bg-indigo-50"
              >
                <span className="text-sm font-medium text-gray-900 break-all">{c.column}</span>
                <span className="flex items-center gap-2 text-xs text-gray-500 shrink-0">
                  {c.data_type}
                  {linked && (
                    <span title="source columns ← · → columns it feeds">
                      ←{c.upstream_columns} →{c.downstream_columns}
                    </span>
                  )}
                  <FiChevronRight />
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
};

export default TableColumnsList;
