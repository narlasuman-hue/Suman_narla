import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiLayers, FiX } from 'react-icons/fi';
import clsx from 'clsx';
import { NAV_SECTIONS } from './navigation';

interface SidebarProps {
  isOpen: boolean;
  isMobileOpen: boolean;
  onMobileClose: () => void;
}

const Brand: React.FC<{ compact?: boolean }> = ({ compact }) => (
  <Link to="/" className="flex items-center gap-2.5 px-2 py-1 text-white hover:text-white">
    <FiLayers size={24} className="flex-shrink-0 text-blue-400" />
    {!compact && (
      <span>
        <span className="block text-[15px] font-bold leading-tight">Lineage Catalog</span>
        <span className="block text-[11px] text-gray-400">Jobs · tables · SLAs</span>
      </span>
    )}
  </Link>
);

const NavLinks: React.FC<{ compact?: boolean; onNavigate?: () => void }> = ({ compact, onNavigate }) => {
  const location = useLocation();
  const params = new URLSearchParams(location.search);

  return (
    <nav aria-label="Main" className="flex-1 space-y-5 overflow-y-auto px-3 py-2">
      {NAV_SECTIONS.map((section) => (
        <div key={section.title} className="space-y-0.5">
          {compact ? (
            <div className="mx-3 mb-2 border-t border-gray-800" aria-hidden="true" />
          ) : (
            <div className="px-3 pb-1.5 text-[11px] font-semibold uppercase tracking-wider text-gray-400">
              {section.title}
            </div>
          )}
          {section.items.map((item) => {
            const Icon = item.icon;
            const active = item.isActive(location.pathname, params);
            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={onNavigate}
                title={compact ? item.label : undefined}
                aria-current={active ? 'page' : undefined}
                className={clsx(
                  'flex h-9 items-center gap-3 rounded-lg px-3 text-[13px]',
                  compact && 'justify-center',
                  active
                    ? 'bg-gray-800 font-semibold text-white hover:text-white'
                    : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                )}
              >
                <Icon size={16} className="flex-shrink-0" />
                {!compact && <span>{item.label}</span>}
              </Link>
            );
          })}
        </div>
      ))}
    </nav>
  );
};

const Sidebar: React.FC<SidebarProps> = ({ isOpen, isMobileOpen, onMobileClose }) => (
  <>
    {/* Desktop */}
    <aside
      className={clsx(
        'hidden flex-col gap-4 overflow-hidden bg-gray-900 py-4 transition-all duration-300 lg:flex',
        isOpen ? 'w-60' : 'w-[72px]'
      )}
    >
      <div className={clsx('px-3', !isOpen && 'flex justify-center')}>
        <Brand compact={!isOpen} />
      </div>
      <NavLinks compact={!isOpen} />
    </aside>

    {/* Mobile */}
    <div
      className={clsx(
        'fixed inset-y-0 left-0 z-50 transform transition-transform duration-300 lg:hidden',
        isMobileOpen ? 'translate-x-0' : '-translate-x-full'
      )}
    >
      <aside className="flex h-full w-64 flex-col gap-4 bg-gray-900 py-4 shadow-lg">
        <div className="flex items-center justify-between px-3">
          <Brand />
          <button
            onClick={onMobileClose}
            aria-label="Close menu"
            className="rounded-lg p-2 text-gray-300 hover:bg-gray-800 hover:text-white"
          >
            <FiX size={18} />
          </button>
        </div>
        <NavLinks onNavigate={onMobileClose} />
      </aside>
    </div>
  </>
);

export default Sidebar;
