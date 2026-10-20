/** The app's navigation: sidebar sections and the header breadcrumb come from here. */
import {
  FiBarChart2,
  FiClock,
  FiEye,
  FiGitBranch,
  FiHome,
  FiLayers,
  FiSearch,
  FiServer,
  FiTrendingUp,
} from 'react-icons/fi';
import { IconType } from 'react-icons';

export interface NavItem {
  label: string;
  href: string;
  icon: IconType;
  /** True when this item is the current page. */
  isActive: (path: string, params: URLSearchParams) => boolean;
}

export interface NavSection {
  title: string;
  items: NavItem[];
}

const exact = (href: string) => (path: string) => path === href;
const prefix = (start: string) => (path: string) => path.startsWith(start);

export const NAV_SECTIONS: NavSection[] = [
  {
    title: 'Monitor',
    items: [
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
    ],
  },
  {
    title: 'Catalog',
    items: [
      { label: 'Dashboard', href: '/', icon: FiHome, isActive: exact('/') },
      { label: 'Search', href: '/search', icon: FiSearch, isActive: exact('/search') },
      { label: 'Table lineage', href: '/lineage/1', icon: FiGitBranch, isActive: prefix('/lineage') },
      { label: 'Lifecycle', href: '/lifecycle', icon: FiTrendingUp, isActive: exact('/lifecycle') },
    ],
  },
  {
    title: 'Analysis',
    items: [
      { label: 'Query analysis', href: '/analysis', icon: FiEye, isActive: exact('/analysis') },
      { label: 'Reports', href: '/reports', icon: FiBarChart2, isActive: exact('/reports') },
    ],
  },
];

/** Breadcrumb for the current page, e.g. ["Monitor", "Lineage Tracking"]. */
export const breadcrumb = (path: string, params: URLSearchParams): string[] => {
  for (const section of NAV_SECTIONS) {
    const item = section.items.find((i) => i.isActive(path, params));
    if (item) {
      return path.startsWith('/jobs/')
        ? [section.title, item.label, 'Job']
        : [section.title, item.label];
    }
  }
  if (path.startsWith('/tables/')) return ['Catalog', 'Table'];
  if (path.startsWith('/databases/')) return ['Catalog', 'Database'];
  return [];
};
