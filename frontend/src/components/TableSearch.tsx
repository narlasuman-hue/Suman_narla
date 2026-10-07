import React, { useEffect, useRef, useState } from 'react';
import { FiSearch, FiX } from 'react-icons/fi';
import { LineagePlatform, LineageTableResult, searchJobLineageTables } from '../services/api';
import { RunStatusBadge } from './LineageDetailsPanel';

interface TableSearchProps {
  platform: LineagePlatform;
  onSelect: (table: LineageTableResult) => void;
}

const PLACEHOLDER: Record<LineagePlatform, string> = {
  MAINFRAME: 'Search Teradata table, e.g. FINANCE_DB.GL_POSTINGS',
  HADOOP_ABINITIO: 'Search Hadoop table, e.g. fin_raw.gl_postings',
};

const DEBOUNCE_MS = 200;

/** Search box for the selected platform's tables; picking one shows its lineage. */
const TableSearch: React.FC<TableSearchProps> = ({ platform, onSelect }) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<LineageTableResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  // New platform -> start over.
  useEffect(() => {
    setQuery('');
    setResults([]);
    setOpen(false);
  }, [platform]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const data = await searchJobLineageTables(platform, query);
        if (!cancelled) {
          setResults(data);
          setActive(0);
        }
      } catch (error) {
        console.error(error);
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, DEBOUNCE_MS);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [platform, query, open]);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', onClickOutside);
    return () => document.removeEventListener('mousedown', onClickOutside);
  }, []);

  const choose = (table: LineageTableResult) => {
    setQuery(table.name);
    setOpen(false);
    onSelect(table);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && open && results[active]) {
      e.preventDefault();
      choose(results[active]);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative flex-1 min-w-[280px]">
      <label htmlFor="table-search" className="sr-only">Search table</label>
      <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
      <input
        id="table-search"
        role="combobox"
        aria-expanded={open}
        aria-controls="table-search-results"
        aria-autocomplete="list"
        autoComplete="off"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={PLACEHOLDER[platform]}
        className="w-full pl-9 pr-9 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
      {query && (
        <button
          onClick={() => {
            setQuery('');
            setOpen(true);
          }}
          title="Clear"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
        >
          <FiX size={16} />
        </button>
      )}

      {open && (
        <ul
          id="table-search-results"
          role="listbox"
          className="absolute z-20 mt-1 w-full max-h-80 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg"
        >
          {!loading && results.length === 0 && (
            <li className="px-4 py-3 text-sm text-gray-500">No matching tables</li>
          )}
          {results.map((t, i) => (
            <li
              key={t.id}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(t);
              }}
              onMouseEnter={() => setActive(i)}
              className={`px-4 py-2 cursor-pointer ${i === active ? 'bg-indigo-50' : ''}`}
            >
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm font-medium text-gray-900 break-all">{t.name}</span>
                <span className="text-xs text-gray-500 shrink-0">{t.dataset_type}</span>
              </div>
              <div className="flex flex-wrap items-center gap-2 mt-0.5 text-xs text-gray-600">
                {t.loaded_by.length ? (
                  t.loaded_by.map((j) => (
                    <span key={j.id} className="flex items-center gap-1">
                      Loaded by <span className="font-medium">{j.name}</span>
                      <RunStatusBadge status={j.run_status} />
                    </span>
                  ))
                ) : (
                  <span>Source table (not loaded by a job on this platform)</span>
                )}
                {t.impacted && <span className="text-amber-700">· impacted by {t.impacted_by.join(', ')}</span>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default TableSearch;
