import React from 'react';
import { Link } from 'react-router-dom';
import { FiAlertTriangle, FiCrosshair, FiExternalLink, FiX, FiZap } from 'react-icons/fi';
import { JobLineageImpact, LineageEdge, LineageNode, LineagePlatform } from '../services/api';
import {
  formatLate,
  formatTime,
  relative,
  RunStatusBadge,
  SlaBadge,
} from './lineageBadges';
import TableColumnsList from './TableColumnsList';

interface Props {
  node: LineageNode | null;
  nodesById: Map<string, LineageNode>;
  edges: LineageEdge[];
  impact: JobLineageImpact | null;
  impactLoading: boolean;
  onFocus: (id: string) => void;
  onShowImpact: (id: string) => void;
  onSelect: (id: string) => void;
  onClose: () => void;
  platform: LineagePlatform;
  /** Open column-level lineage for a column of the selected table. */
  onColumnSelect: (columnId: string) => void;
}


const jobTypeLabel: Record<string, string> = {
  JCL: 'Mainframe JCL job',
  TERADATA_LOAD: 'Mainframe → Teradata load job',
  AB_INITIO_GRAPH: 'Ab Initio graph (Hadoop)',
};

const datasetPlatformLabel: Record<string, string> = {
  MAINFRAME: 'Mainframe dataset',
  TERADATA: 'Teradata table',
  HADOOP: 'Hadoop (HDFS / Hive)',
};

const Row: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <div className="flex justify-between gap-3 py-1.5 text-sm border-b border-gray-100 last:border-0">
    <span className="text-gray-500 shrink-0">{label}</span>
    <span className="text-gray-900 text-right break-all">{children}</span>
  </div>
);

const NodeLinkList: React.FC<{
  title: string;
  ids: string[];
  nodesById: Map<string, LineageNode>;
  onSelect: (id: string) => void;
}> = ({ title, ids, nodesById, onSelect }) =>
  ids.length ? (
    <div>
      <p className="text-xs font-semibold uppercase text-gray-500 mb-1">{title}</p>
      <ul className="space-y-1">
        {ids.map((id) => (
          <li key={id}>
            <button onClick={() => onSelect(id)} className="text-sm text-indigo-600 hover:underline text-left break-all">
              {nodesById.get(id)?.name || id}
            </button>
          </li>
        ))}
      </ul>
    </div>
  ) : null;

const LineageDetailsPanel: React.FC<Props> = ({
  node,
  nodesById,
  edges,
  impact,
  impactLoading,
  onFocus,
  onShowImpact,
  onSelect,
  onClose,
  platform,
  onColumnSelect,
}) => {
  if (!node) return null;

  // Teradata / Hadoop tables are "loaded" by jobs; mainframe datasets are written.
  const writtenLabel =
    node.type === 'dataset' && node.platform !== 'MAINFRAME' ? 'Loaded by' : 'Written by';
  const inputs = edges.filter((e) => e.target === node.id).map((e) => e.source);
  const outputs = edges.filter((e) => e.source === node.id).map((e) => e.target);

  return (
    <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-5 space-y-4">
      <div className="relative pr-6">
        <button onClick={onClose} title="Close" className="absolute top-0 right-0 text-gray-400 hover:text-gray-700">
          <FiX size={18} />
        </button>
        <p className="text-xs text-gray-500">
          {node.type === 'job' ? jobTypeLabel[node.job_type] : datasetPlatformLabel[node.platform]}
        </p>
        <h2 className="text-lg font-bold text-gray-900 break-all">{node.name}</h2>
        {node.type === 'job' && node.description && (
          <p className="text-sm text-gray-600 mt-1">{node.description}</p>
        )}
      </div>

      {node.type === 'job' ? (
        <div>
          <Row label="Last run">
            <RunStatusBadge status={node.run_status} /> {relative(node.last_run)}
          </Row>
          {node.run_duration_seconds != null && (
            <Row label="Duration">{Math.round(node.run_duration_seconds / 60)} min</Row>
          )}
          <Row label="Next run">{relative(node.next_run)}</Row>
          <Row label="Scheduler">{node.scheduler_system || '-'}</Row>
          <Row label="Schedule">{node.schedule_name || '-'}</Row>
          <Row label="Frequency">{node.frequency || '-'}</Row>
          <Row label="Owner">{node.owner || '-'}</Row>
          {node.sla ? (
            <>
              <Row label="SLA">
                <SlaBadge status={node.sla.status} />
                {node.sla.late_by_minutes > 0 && (
                  <span className="ml-2 font-semibold text-red-700">
                    {formatLate(node.sla.late_by_minutes)} late
                  </span>
                )}
              </Row>
              <Row label="Expected by">{formatTime(node.sla.expected_completion)}</Row>
              <p className="text-xs text-gray-500 pt-1">{node.sla.reason}</p>
            </>
          ) : (
            <Row label="SLA">Not tracked</Row>
          )}
        </div>
      ) : (
        <div>
          <Row label="Type">{node.dataset_type || '-'}</Row>
          <Row label="Database">{node.database}</Row>
          <Row label={writtenLabel}>{inputs.length} job(s)</Row>
          <Row label="Read by">{outputs.length} job(s)</Row>
        </div>
      )}

      {node.type === 'job' && node.run_error && (
        <div className="p-3 rounded bg-red-50 border border-red-200 text-sm text-red-800 break-words">
          {node.run_error}
        </div>
      )}

      {node.impacted && (
        <div className="flex gap-2 p-3 rounded bg-amber-50 border border-amber-200 text-sm text-amber-900">
          <FiAlertTriangle className="shrink-0 mt-0.5" />
          <span>Impacted by upstream failure: {node.impacted_by.join(', ')}</span>
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => onFocus(node.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
        >
          <FiCrosshair size={14} /> Focus lineage
        </button>
        <button
          onClick={() => onShowImpact(node.id)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg bg-amber-500 text-white hover:bg-amber-600"
        >
          <FiZap size={14} /> Blast radius
        </button>
        {node.type === 'job' && node.platform === 'MAINFRAME' && (
          <Link
            to={`/mainframe/jobs/${node.catalog_id}`}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
          >
            <FiExternalLink size={14} /> Job details
          </Link>
        )}
      </div>

      {impactLoading && <p className="text-sm text-gray-500">Calculating blast radius…</p>}
      {impact && impact.node.id === node.id && (
        <div className="space-y-3 pt-2 border-t border-gray-200">
          <p className="text-sm font-semibold text-gray-900">
            Blast radius: {impact.impacted_jobs.length} downstream job(s),{' '}
            {impact.impacted_datasets.length} dataset(s)
          </p>
          {impact.impacted_jobs.length > 0 && (
            <ul className="space-y-1.5">
              {impact.impacted_jobs.map((j) => (
                <li key={j.id} className="text-sm">
                  <button onClick={() => onSelect(j.id)} className="text-indigo-600 hover:underline text-left break-all">
                    {j.name}
                  </button>
                  <p className="text-xs text-gray-500">
                    {j.distance} level{j.distance > 1 ? 's' : ''} down · {j.owner || 'no owner'} ·
                    next run {relative(j.next_run)}
                  </p>
                </li>
              ))}
            </ul>
          )}
          {impact.upstream_issues.length > 0 && (
            <div className="p-3 rounded bg-red-50 border border-red-200">
              <p className="text-xs font-semibold uppercase text-red-800 mb-1">Upstream issues</p>
              {impact.upstream_issues.map((j) => (
                <button key={j.id} onClick={() => onSelect(j.id)} className="flex items-center gap-2 text-sm text-red-900 hover:underline">
                  <RunStatusBadge status={j.run_status} /> {j.name}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
      {node.type === 'dataset' && (
        <TableColumnsList platform={platform} datasetId={node.id} onColumnSelect={onColumnSelect} />
      )}

      <NodeLinkList title={node.type === 'job' ? 'Reads' : writtenLabel} ids={inputs} nodesById={nodesById} onSelect={onSelect} />
      <NodeLinkList title={node.type === 'job' ? 'Writes' : 'Read by'} ids={outputs} nodesById={nodesById} onSelect={onSelect} />

    </div>
  );
};

export default LineageDetailsPanel;
