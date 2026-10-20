/** The app's navigation: sidebar sections and the header breadcrumb come from here. */
import { FiClock, FiLayers, FiServer } from 'react-icons/fi';
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
  return [];
};
