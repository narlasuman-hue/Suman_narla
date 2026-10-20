import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { FiChevronsLeft, FiChevronsRight, FiLayers, FiX } from 'react-icons/fi';
import clsx from 'clsx';
import { NAV_SECTIONS } from './navigation';

interface SidebarProps {
  isOpen: boolean;
  isMobileOpen: boolean;
  onToggle: () => void;
  onMobileClose: () => void;
}

/** Label that pops out beside a collapsed sidebar icon. */
interface Flyout {
  section: string;
  label: string;
  top: number;
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
  const [flyout, setFlyout] = useState<Flyout | null>(null);

  // Collapsed: show the item's name beside its icon on hover and keyboard focus.
  const showFlyout = (section: string, label: string) => (e: React.SyntheticEvent<HTMLElement>) => {
    if (!compact) return;
    const rect = e.currentTarget.getBoundingClientRect();
    setFlyout({ section, label, top: rect.top + rect.height / 2 });
  };
  const hideFlyout = () => setFlyout(null);

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
                onClick={() => {
                  hideFlyout();
                  onNavigate?.();
                }}
                onMouseEnter={showFlyout(section.title, item.label)}
                onMouseLeave={hideFlyout}
                onFocus={showFlyout(section.title, item.label)}
                onBlur={hideFlyout}
                aria-label={compact ? item.label : undefined}
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
      {compact && flyout && (
        // Fixed, so the sidebar's overflow doesn't clip it.
        <div
          aria-hidden="true"
          className="pointer-events-none fixed left-[80px] z-50 -translate-y-1/2 rounded-lg bg-gray-900 px-3 py-1.5 shadow-lg ring-1 ring-white/10"
          style={{ top: flyout.top }}
        >
          <span className="absolute -left-1 top-1/2 h-2 w-2 -translate-y-1/2 rotate-45 bg-gray-900" />
          <span className="block text-[10px] font-semibold uppercase tracking-wider text-gray-400">{flyout.section}</span>
          <span className="block whitespace-nowrap text-[13px] font-medium text-white">{flyout.label}</span>
        </div>
      )}
    </nav>
  );
};

const Sidebar: React.FC<SidebarProps> = ({ isOpen, isMobileOpen, onToggle, onMobileClose }) => (
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
      <div className="border-t border-gray-800 px-3 pt-3">
        <button
          onClick={onToggle}
          aria-label={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          aria-expanded={isOpen}
          className={clsx(
            'flex h-9 w-full items-center gap-3 rounded-lg px-3 text-[13px] text-gray-400 hover:bg-gray-800 hover:text-white',
            !isOpen && 'justify-center'
          )}
        >
          {isOpen ? <FiChevronsLeft size={16} /> : <FiChevronsRight size={16} />}
          {isOpen && <span>Collapse</span>}
        </button>
      </div>
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
