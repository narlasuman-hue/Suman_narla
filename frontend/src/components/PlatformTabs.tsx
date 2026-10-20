import React from 'react';
import { PlatformInfo } from '../services/api';

interface PlatformTabsProps {
  platforms: PlatformInfo[];
  activeId: string;
  onChange: (platform: PlatformInfo) => void;
}

/** One tab per lineage platform, with its job, failed and late counts. */
const PlatformTabs: React.FC<PlatformTabsProps> = ({ platforms, activeId, onChange }) => (
  <div className="flex flex-wrap gap-2" role="tablist" aria-label="Platform">
    {platforms.map((p) => {
      const active = p.id === activeId;
      return (
        <button
          key={p.id}
          role="tab"
          aria-selected={active}
          onClick={() => onChange(p)}
          className={`flex min-h-[44px] flex-col gap-0.5 rounded-lg border-2 px-3.5 py-2 text-left ${
            active ? 'border-gray-900 bg-white shadow-sm' : 'border-transparent hover:bg-white'
          }`}
        >
          <span className="flex items-center gap-2 text-[13px] font-semibold text-gray-900">
            <span className="h-2 w-2 rounded-full" style={{ background: p.color }} aria-hidden="true" />
            {p.name}
          </span>
          <span className="flex gap-2.5 pl-4 text-xs text-gray-600">
            <span>{p.summary.jobs} jobs</span>
            {p.summary.failed > 0 && <span className="font-semibold text-red-700">{p.summary.failed} failed</span>}
            {p.summary.sla_late > 0 && <span className="font-semibold text-orange-800">{p.summary.sla_late} late</span>}
          </span>
        </button>
      );
    })}
  </div>
);

export default PlatformTabs;
