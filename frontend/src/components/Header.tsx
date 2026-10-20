import React, { useState } from 'react';
import { FiLayers, FiMenu, FiSearch } from 'react-icons/fi';
import { Link, useLocation, useNavigate } from 'react-router-dom';
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
    <header className="flex min-h-[60px] flex-wrap items-center gap-x-4 gap-y-2 bg-gray-900 px-3 py-2.5 sm:px-4">
      <button
        onClick={onMenuToggle}
        aria-label="Toggle sidebar"
        className="hidden rounded-lg p-2 text-gray-300 hover:bg-gray-800 hover:text-white lg:block"
      >
        <FiMenu size={18} />
      </button>
      <button
        onClick={onMobileMenuToggle}
        aria-label="Open menu"
        className="rounded-lg p-2 text-gray-300 hover:bg-gray-800 hover:text-white lg:hidden"
      >
        <FiMenu size={18} />
      </button>

      <Link to="/" className="flex items-center gap-2 text-white hover:text-white" aria-label="TrailBlazers home">
        <FiLayers size={22} className="text-blue-400" aria-hidden="true" />
        <span className="text-[17px] font-bold tracking-tight">TrailBlazers</span>
      </Link>

      <nav aria-label="Breadcrumb" className="hidden items-center gap-2 border-l border-gray-700 pl-4 text-sm sm:flex">
        {crumbs.map((c, i) => (
          <React.Fragment key={c}>
            {i > 0 && <span className="text-gray-500" aria-hidden="true">/</span>}
            <span className={i === crumbs.length - 1 ? 'font-semibold text-white' : 'text-gray-400'}>{c}</span>
          </React.Fragment>
        ))}
      </nav>

      <form onSubmit={submit} role="search" className="relative ml-auto w-full max-w-sm sm:w-auto sm:flex-1">
        <label htmlFor="global-search" className="sr-only">
          Search tables, columns and views
        </label>
        <FiSearch className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
        <input
          id="global-search"
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search tables, columns, views"
          className="h-9 w-full rounded-lg border border-gray-700 bg-gray-800 pl-9 pr-3 text-sm text-white placeholder-gray-400 focus:border-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500/40"
        />
      </form>
    </header>
  );
};

export default Header;
