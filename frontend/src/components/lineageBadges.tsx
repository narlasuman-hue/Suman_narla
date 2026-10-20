/** Small shared pieces for the Job Lineage page: status badges and time helpers. */
import React from 'react';
import { format, formatDistanceToNow } from 'date-fns';
import { SlaStatus } from '../services/api';

/** API timestamps are naive UTC; mark them as UTC before parsing. */
export const parseUtc = (iso?: string | null) =>
  iso ? new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`) : null;

export const relative = (iso?: string | null) => {
  const d = parseUtc(iso);
  return d ? formatDistanceToNow(d, { addSuffix: true }) : '-';
};

export const formatTime = (iso?: string | null) => {
  const d = parseUtc(iso);
  return d ? format(d, 'MMM d, HH:mm') : '-';
};

export const formatLate = (minutes: number) =>
  minutes >= 60 ? `${Math.floor(minutes / 60)}h ${minutes % 60}m` : `${minutes}m`;

const RUN_STYLE: Record<string, string> = {
  SUCCESS: 'bg-green-50 text-green-800',
  FAILED: 'bg-red-700 text-white',
  RUNNING: 'bg-blue-700 text-white',
};

export const RunStatusBadge: React.FC<{ status: string }> = ({ status }) => (
  <span className={`px-2 py-0.5 rounded text-xs font-semibold ${RUN_STYLE[status] || 'bg-gray-100 text-gray-700'}`}>
    {status}
  </span>
);

export const SLA_LABEL: Record<SlaStatus, string> = {
  LATE: 'Late',
  COMPLETED_LATE: 'Completed late',
  AT_RISK: 'At risk',
  ON_TRACK: 'On track',
  MET: 'Met',
};

export const SLA_STYLE: Record<SlaStatus, string> = {
  LATE: 'bg-red-700 text-white',
  COMPLETED_LATE: 'bg-amber-100 text-amber-900',
  AT_RISK: 'bg-orange-100 text-orange-900',
  ON_TRACK: 'bg-blue-50 text-blue-800',
  MET: 'bg-green-50 text-green-800',
};

export const SlaBadge: React.FC<{ status?: SlaStatus | null; prefix?: string }> = ({ status, prefix }) =>
  status ? (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold whitespace-nowrap ${SLA_STYLE[status]}`}>
      {prefix}
      {SLA_LABEL[status]}
    </span>
  ) : null;

/** Compact upper-case status label, matching the status line on graph nodes. */
export type StatusKind = 'FAILED' | 'RUNNING' | 'BLOCKED' | 'LATE' | 'DONE_LATE';

const CHIP_STYLE: Record<StatusKind, string> = {
  FAILED: 'bg-red-700 text-white',
  RUNNING: 'bg-blue-700 text-white',
  BLOCKED: 'bg-orange-100 text-orange-900',
  LATE: 'bg-red-100 text-red-900',
  DONE_LATE: 'bg-amber-100 text-amber-900',
};

export const StatusChip: React.FC<{ kind: StatusKind }> = ({ kind }) => (
  <span className={`inline-flex h-[18px] items-center rounded px-1.5 text-[10px] font-bold tracking-wide whitespace-nowrap ${CHIP_STYLE[kind]}`}>
    {kind.replace('_', ' ')}
  </span>
);
