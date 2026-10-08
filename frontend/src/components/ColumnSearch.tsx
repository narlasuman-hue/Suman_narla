import React, { useEffect, useRef, useState } from 'react';
import { FiSearch, FiX } from 'react-icons/fi';
import { LineagePlatform, searchJobLineageColumns } from '../services/api';

interface ColumnSearchProps {
  platform: LineagePlatform;
  /** Show every table with this column: exact name, or any column containing the text. */
  onSearch: (column: string, exact: boolean) => void;
}

interface Suggestion {
  name: string;
  tables: number;
  types: string[];
}

const DEBOUNCE_MS = 200;

/** Column name search; suggestions are grouped by column name with the number of tables. */
const ColumnSearch: React.FC<ColumnSearchProps> = ({ platform, onSearch }) => {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setQuery('');
    setSuggestions([]);
    setOpen(false);
  }, [platform]);

  useEffect(() => {
    if (!open || !query.trim()) {
      setSuggestions([]);
      return;
    }
    let cancelled = false;
    const timer = setTimeout(async () => {
      try {
        const rows = await searchJobLineageColumns(platform, query.trim());
        const grouped = new Map<string, Suggestion>();
        rows.forEach((r) => {
          const key = r.column.toUpperCase();
          const entry = grouped.get(key) || { name: r.column, tables: 0, types: [] };
          entry.tables += 1;
          if (r.data_type && !entry.types.includes(r.data_type)) entry.types.push(r.data_type);
          grouped.set(key, entry);
        });
        if (!cancelled) {
          setSuggestions(Array.from(grouped.values()));
          setActive(-1);
        }
      } catch (error) {
        console.error(error);
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

  const choose = (name: string, exact: boolean) => {
    setQuery(name);
    setOpen(false);
    onSearch(name, exact);
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter' && query.trim()) {
      e.preventDefault();
      // A highlighted suggestion is an exact column; otherwise search the typed text.
      if (active >= 0 && suggestions[active]) choose(suggestions[active].name, true);
      else choose(query.trim(), false);
    } else if (e.key === 'Escape') {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className="relative flex-1 min-w-[280px]">
      <label htmlFor="column-search" className="sr-only">Search column</label>
      <FiSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
      <input
        id="column-search"
        role="combobox"
        aria-expanded={open}
        aria-controls="column-search-results"
        aria-autocomplete="list"
        autoComplete="off"
        value={query}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder="Search column, e.g. CUSTOMER_ID (Enter to list every table)"
        className="w-full pl-9 pr-9 py-2 text-sm border border-gray-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
      />
      {query && (
        <button
          onClick={() => setQuery('')}
          title="Clear"
          className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
        >
          <FiX size={16} />
        </button>
      )}
      {open && query.trim() && (
        <ul
          id="column-search-results"
          role="listbox"
          className="absolute z-20 mt-1 w-full max-h-80 overflow-y-auto bg-white border border-gray-200 rounded-lg shadow-lg"
        >
          {suggestions.length === 0 && (
            <li className="px-4 py-3 text-sm text-gray-500">No matching columns</li>
          )}
          {suggestions.map((s, i) => (
            <li
              key={s.name}
              role="option"
              aria-selected={i === active}
              onMouseDown={(e) => {
                e.preventDefault();
                choose(s.name, true);
              }}
              onMouseEnter={() => setActive(i)}
              className={`px-4 py-2 cursor-pointer flex items-center justify-between gap-3 ${
                i === active ? 'bg-indigo-50' : ''
              }`}
            >
              <span className="text-sm font-medium text-gray-900 break-all">{s.name}</span>
              <span className="text-xs text-gray-500 shrink-0">
                in {s.tables} table{s.tables > 1 ? 's' : ''}
                {s.types.length > 0 && ` · ${s.types.slice(0, 2).join(', ')}${s.types.length > 2 ? '…' : ''}`}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default ColumnSearch;
