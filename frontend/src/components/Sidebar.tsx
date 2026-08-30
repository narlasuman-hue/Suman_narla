import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  FiHome,
  FiSearch,
  FiShare2,
  FiBarChart2,
  FiTrendingUp,
  FiEye,
  FiGitBranch,
} from 'react-icons/fi';
import clsx from 'clsx';

interface SidebarProps {
  isOpen: boolean;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

const menuItems = [
  { icon: FiHome, label: 'Dashboard', href: '/' },
  { icon: FiSearch, label: 'Search', href: '/search' },
  { icon: FiGitBranch, label: 'Lineage', href: '/lineage/1' },
  { icon: FiShare2, label: 'Impact Analysis', href: '/analysis' },
  { icon: FiBarChart2, label: 'Reports', href: '/reports' },
  { icon: FiTrendingUp, label: 'Lifecycle', href: '/lifecycle' },
  { icon: FiEye, label: 'Query Analysis', href: '/analysis' },
];

const Sidebar: React.FC<SidebarProps> = ({ isOpen, isMobileOpen, onMobileClose }) => {
  const location = useLocation();

  const isActive = (href: string) => location.pathname === href;

  return (
    <>
      {/* Desktop Sidebar */}
      <div
        className={clsx(
          'hidden lg:flex flex-col bg-white border-r border-gray-200 transition-all duration-300 overflow-hidden',
          isOpen ? 'w-64' : 'w-20'
        )}
      >
        <nav className="flex-1 px-2 py-4 space-y-2">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.href);

            return (
              <Link
                key={item.href}
                to={item.href}
                className={clsx(
                  'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                  active
                    ? 'bg-blue-50 text-blue-600 font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                )}
              >
                <Icon size={20} className="flex-shrink-0" />
                {isOpen && <span className="text-sm">{item.label}</span>}
              </Link>
            );
          })}
        </nav>

        <div className="border-t border-gray-200 p-4">
          <div className={clsx('text-xs text-gray-500', !isOpen && 'text-center')}>
            {isOpen ? 'Database Metadata Catalog v1.0' : 'v1.0'}
          </div>
        </div>
      </div>

      {/* Mobile Sidebar */}
      <div
        className={clsx(
          'fixed inset-0 z-50 transform transition-transform duration-300 lg:hidden',
          isMobileOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        <div className="flex h-full w-64 flex-col bg-white shadow-lg">
          <div className="flex items-center justify-between p-4 border-b">
            <span className="font-bold text-lg">Menu</span>
            <button
              onClick={onMobileClose}
              className="p-1 text-gray-600 hover:bg-gray-100 rounded"
            >
              ×
            </button>
          </div>

          <nav className="flex-1 px-2 py-4 space-y-2">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);

              return (
                <Link
                  key={item.href}
                  to={item.href}
                  onClick={onMobileClose}
                  className={clsx(
                    'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
                    active
                      ? 'bg-blue-50 text-blue-600 font-medium'
                      : 'text-gray-600 hover:bg-gray-50'
                  )}
                >
                  <Icon size={20} />
                  <span className="text-sm">{item.label}</span>
                </Link>
              );
            })}
          </nav>
        </div>
      </div>
    </>
  );
};

export default Sidebar;
