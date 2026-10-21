/** The app's navigation: the sidebar items and the header breadcrumb come from here. */
import { FiClock, FiLayers, FiServer } from 'react-icons/fi';
import { IconType } from 'react-icons';

export interface NavItem {
  label: string;
  href: string;
  icon: IconType;
  /** True when this item is the current page. */
  isActive: (path: string, params: URLSearchParams) => boolean;
}

const prefix = (start: string) => (path: string) => path.startsWith(start);

export const NAV_ITEMS: NavItem[] = [
  {
    label: 'Lineage Tracking',
    href: '/job-lineage',
    icon: FiLayers,
    isActive: (path, params) => path === '/job-lineage' && params.get('tab') !== 'sla',
  },
  {
    label: 'SLA Tracking',
    href: '/job-lineage?tab=sla',
    icon: FiClock,
    isActive: (path, params) => path === '/job-lineage' && params.get('tab') === 'sla',
  },
  { label: 'Jobs Tracking', href: '/jobs', icon: FiServer, isActive: prefix('/jobs') },
];

/** Breadcrumb for the current page, e.g. ["Lineage Tracking"] or ["Jobs Tracking", "Job"]. */
export const breadcrumb = (path: string, params: URLSearchParams): string[] => {
  const item = NAV_ITEMS.find((i) => i.isActive(path, params));
  if (!item) return [];
  return path.startsWith('/jobs/') ? [item.label, 'Job'] : [item.label];
};
