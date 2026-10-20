import React from 'react';
import { FiCheckCircle } from 'react-icons/fi';
import { LineageJobNode, LineageNode } from '../services/api';
import { formatLate, relative, StatusChip, StatusKind } from './lineageBadges';

interface AttentionPanelProps {
  nodes: LineageNode[];
  onShowImpact: (id: string) => void;
  onSelect: (id: string) => void;
}

interface AttentionItem {
  job: LineageJobNode;
  kind: StatusKind;
  text: string;
}

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

/** Failed, late, running and completed-late jobs, worst first. */
export const attentionItems = (nodes: LineageNode[]): AttentionItem[] => {
  const jobs = nodes.filter((n): n is LineageJobNode => n.type === 'job');
  const blockedBy = (name: string) => {
    const blocked = nodes.filter((n) => n.impacted_by.includes(name));
    const blockedJobs = blocked.filter((n) => n.type === 'job').length;
    const blockedTables = blocked.filter((n) => n.type === 'dataset' && n.is_table).length;
    const parts = [
      blockedJobs ? plural(blockedJobs, 'job') : '',
      blockedTables ? plural(blockedTables, 'table') : '',
    ].filter(Boolean);
    return parts.length ? `blocks ${parts.join(' and ')}` : 'nothing downstream';
  };

  const failed = jobs
    .filter((j) => j.run_status === 'FAILED')
    .map((job) => ({
      job,
      kind: 'FAILED' as const,
      text: `${job.run_error || 'Last run failed'} · ${blockedBy(job.name)}`,
    }));
  const late = jobs
    .filter((j) => j.run_status !== 'FAILED' && j.sla?.status === 'LATE')
    .map((job) => ({
      job,
      kind: 'LATE' as const,
      text: [
        `Late by ${formatLate(job.sla!.late_by_minutes)}`,
        job.impacted_by.length ? `waiting on ${job.impacted_by.join(', ')}` : job.sla!.reason,
      ].join(' · '),
    }));
  const running = jobs
    .filter((j) => j.run_status === 'RUNNING' && j.sla?.status !== 'LATE')
    .map((job) => ({ job, kind: 'RUNNING' as const, text: `Started ${relative(job.last_run)}` }));
  const doneLate = jobs
    .filter((j) => j.sla?.status === 'COMPLETED_LATE')
    .map((job) => ({
      job,
      kind: 'DONE_LATE' as const,
      text: `Completed ${formatLate(job.sla!.late_by_minutes)} after its SLA`,
    }));
  return [...failed, ...late, ...running, ...doneLate];
};

/** Side panel shown next to the graph when nothing is selected. */
const AttentionPanel: React.FC<AttentionPanelProps> = ({ nodes, onShowImpact, onSelect }) => {
  const items = attentionItems(nodes);

  return (
    <div className="flex h-full flex-col rounded-lg bg-white shadow">
      <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3">
        <h2 className="text-[15px] font-semibold text-gray-900">Needs attention</h2>
        <span className="text-xs text-gray-600">{plural(items.length, 'item')}</span>
      </div>
      {items.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 p-8 text-center text-sm text-gray-600">
          <FiCheckCircle size={22} className="text-green-700" />
          All clear: no failed, late or running jobs.
        </div>
      ) : (
        <ul className="flex-1 divide-y divide-gray-100 overflow-y-auto">
          {items.map(({ job, kind, text }) => (
            <li key={`${kind}-${job.id}`} className="space-y-1.5 px-4 py-3">
              <div className="flex items-center gap-2">
                <StatusChip kind={kind} />
                <span className="truncate font-mono text-[13px] font-semibold text-gray-900">{job.name}</span>
              </div>
              <p className="break-words text-xs text-gray-600">{text}</p>
              <div className="flex gap-1.5 pt-0.5">
                {kind === 'FAILED' && (
                  <button
                    onClick={() => onShowImpact(job.id)}
                    className="h-[30px] rounded-lg bg-blue-700 px-2.5 text-xs font-medium text-white hover:bg-blue-800"
                  >
                    Show blast radius
                  </button>
                )}
                <button
                  onClick={() => onSelect(job.id)}
                  className="h-[30px] rounded-lg border border-gray-300 bg-white px-2.5 text-xs font-medium text-gray-800 hover:bg-gray-50"
                >
                  Details
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};

export default AttentionPanel;
