import React from 'react';
import { FiMenu, FiX, FiSearch } from 'react-icons/fi';
import { Link } from 'react-router-dom';

interface HeaderProps {
  onMenuToggle: () => void;
  onMobileMenuToggle: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuToggle, onMobileMenuToggle }) => {
  return (
    <header className="bg-white border-b border-gray-200 shadow-sm">
      <div className="px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuToggle}
            className="hidden lg:block p-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            <FiMenu size={20} />
          </button>

          <button
            onClick={onMobileMenuToggle}
            className="lg:hidden p-2 text-gray-600 hover:bg-gray-100 rounded"
          >
            <FiMenu size={20} />
          </button>

          <Link to="/" className="text-xl font-bold text-blue-600">
            Database Catalog
          </Link>
        </div>

        <div className="flex-1 max-w-md mx-4">
          <Link to="/search" className="w-full">
            <div className="relative">
              <input
                type="text"
                placeholder="Search assets..."
                className="w-full px-4 py-2 border border-gray-300 rounded-lg bg-gray-50 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                onClick={(e) => e.currentTarget.focus()}
              />
              <FiSearch className="absolute right-3 top-2.5 text-gray-400" size={18} />
            </div>
          </Link>
        </div>

        <div className="text-sm text-gray-600">
          Connected to Teradata
        </div>
      </div>
    </header>
  );
};

export default Header;
