import React, { useState, useEffect } from 'react';
import { FiSearch, FiTable, FiColumns, FiDatabase } from 'react-icons/fi';
import toast from 'react-hot-toast';
import { globalSearch, autocomplete } from '../services/api';
import { LoadingSpinner } from '../components/LoadingSpinner';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

const SearchPage: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [assetTypeFilter, setAssetTypeFilter] = useState<string[]>([
    'tables',
    'columns',
    'views',
  ]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  useEffect(() => {
    if (query.length >= 2) {
      loadSuggestions();
    } else {
      setSuggestions([]);
      setShowSuggestions(false);
    }
  }, [query]);

  const loadSuggestions = async () => {
    try {
      const data = await autocomplete(query, 'table');
      setSuggestions(data.slice(0, 8));
      setShowSuggestions(true);
    } catch (error) {
      console.error('Failed to load suggestions', error);
    }
  };

  const handleSearch = async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      toast.error('Please enter a search query');
      return;
    }

    try {
      setLoading(true);
      setShowSuggestions(false);
      const data = await globalSearch(searchQuery, assetTypeFilter, undefined, 100);
      setResults(data);
      setQuery(searchQuery);
    } catch (error) {
      toast.error('Failed to search assets');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const toggleAssetType = (type: string) => {
    setAssetTypeFilter((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type]
    );
  };

  return (
    <div className="space-y-6 max-w-6xl">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Search Assets</h1>
        <p className="mt-1 text-gray-600">
          Search across tables, columns, views, and more
        </p>
      </div>

      {/* Search Input */}
      <div className="relative">
        <div className="flex gap-2">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch(query)}
              onFocus={() => query.length >= 2 && setShowSuggestions(true)}
              placeholder="Search tables, columns, databases..."
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-base"
            />

            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="absolute top-full left-0 right-0 mt-2 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                {suggestions.map((suggestion, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSearch(suggestion)}
                    className="w-full text-left px-4 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                  >
                    <FiSearch className="inline mr-2 text-gray-400" size={16} />
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={() => handleSearch(query)}
            disabled={loading}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-medium transition"
          >
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <h3 className="font-medium text-gray-900 mb-3">Asset Type</h3>
        <div className="flex flex-wrap gap-2">
          {[
            { id: 'tables', label: 'Tables', icon: FiTable },
            { id: 'columns', label: 'Columns', icon: FiColumns },
            { id: 'views', label: 'Views', icon: FiDatabase },
          ].map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => toggleAssetType(id)}
              className={clsx(
                'flex items-center gap-2 px-4 py-2 rounded-lg border transition',
                assetTypeFilter.includes(id)
                  ? 'bg-blue-50 border-blue-300 text-blue-700'
                  : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400'
              )}
            >
              <Icon size={16} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Results */}
      {loading ? (
        <LoadingSpinner />
      ) : results ? (
        <div className="space-y-4">
          {/* Tables Results */}
          {results.tables && results.tables.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="border-b border-gray-200 p-4 flex items-center gap-2">
                <FiTable className="text-green-600" size={20} />
                <h2 className="font-bold text-gray-900">
                  Tables ({results.tables.length})
                </h2>
              </div>

              <div className="divide-y">
                {results.tables.map((table: any) => (
                  <Link
                    key={table.id}
                    to={`/tables/${table.id}`}
                    className="block p-4 hover:bg-gray-50 transition"
                  >
                    <div>
                      <p className="font-medium text-gray-900">{table.name}</p>
                      {table.description && (
                        <p className="text-sm text-gray-600 mt-1">{table.description}</p>
                      )}
                      <div className="flex gap-4 text-sm text-gray-500 mt-2">
                        <span>{table.row_count?.toLocaleString() || 0} rows</span>
                        <span>{table.size_mb || 0}MB</span>
                        <span>{table.database}</span>
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Columns Results */}
          {results.columns && results.columns.length > 0 && (
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="border-b border-gray-200 p-4 flex items-center gap-2">
                <FiColumns className="text-purple-600" size={20} />
                <h2 className="font-bold text-gray-900">
                  Columns ({results.columns.length})
                </h2>
              </div>

              <div className="divide-y">
                {results.columns.map((column: any) => (
                  <div key={column.id} className="p-4 hover:bg-gray-50">
                    <div>
                      <p className="font-medium text-gray-900">{column.name}</p>
                      <p className="text-sm text-gray-600 mt-1">
                        In table <span className="font-medium">{column.table_name}</span> (
                        {column.data_type})
                        {column.sensitive && (
                          <span className="ml-2 inline-block px-2 py-1 bg-orange-100 text-orange-700 rounded text-xs font-medium">
                            Sensitive
                          </span>
                        )}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* No Results Message */}
          {(!results.tables || results.tables.length === 0) &&
            (!results.columns || results.columns.length === 0) && (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <FiSearch className="mx-auto text-gray-400 mb-4" size={48} />
                <p className="text-gray-600">No results found for "{query}"</p>
                <p className="text-sm text-gray-500 mt-2">
                  Try a different search term or adjust your filters
                </p>
              </div>
            )}
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <FiSearch className="mx-auto text-gray-400 mb-4" size={48} />
          <p className="text-gray-600">Start by entering a search query</p>
        </div>
      )}
    </div>
  );
};

export default SearchPage;
