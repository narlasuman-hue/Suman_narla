import React, { useState } from 'react';
import { FiMenu, FiSearch } from 'react-icons/fi';
import { useLocation, useNavigate } from 'react-router-dom';
import { breadcrumb } from './navigation';

interface HeaderProps {
  onMenuToggle: () => void;
  onMobileMenuToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuToggle, onMobileMenuToggle }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const crumbs = breadcrumb(location.pathname, new URLSearchParams(location.search));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const q = query.trim();
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : '/search');
  };

  return (
    <header className="flex min-h-[64px] flex-wrap items-center gap-4 border-b border-gray-200 bg-white px-4 py-3 sm:px-6">
      <button
        onClick={onMenuToggle}
        aria-label="Collapse sidebar"
        className="hidden rounded-lg p-2 text-gray-600 hover:bg-gray-100 lg:block"
      >
        <FiMenu size={18} />
      </button>
      <button
        onClick={onMobileMenuToggle}
        aria-label="Open menu"
        className="rounded-lg p-2 text-gray-600 hover:bg-gray-100 lg:hidden"
      >
        <FiMenu size={18} />
      </button>

      <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-sm">
        {crumbs.map((c, i) => (
          <React.Fragment key={c}>
            {i > 0 && <span className="text-gray-400" aria-hidden="true">/</span>}
            <span className={i === crumbs.length - 1 ? 'font-semibold text-gray-900' : 'text-gray-600'}>{c}</span>
          </React.Fragment>
        ))}
      </nav>

      <form onSubmit={submit} role="search" className="relative ml-auto w-full max-w-sm sm:w-auto sm:flex-1">
        <label htmlFor="global-search" className="sr-only">
          Search tables, columns and views
        </label>
        <FiSearch className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={16} />
        <input
          id="global-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tables, columns, views"
          className="h-9 w-full rounded-lg border border-gray-300 bg-gray-50 pl-9 pr-3 text-sm focus:border-blue-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-200"
        />
      </form>
    </header>
  );
};

export default Header;
