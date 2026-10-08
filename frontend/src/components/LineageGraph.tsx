import React, { useEffect, useRef } from 'react';
import cytoscape, { Core, ElementDefinition } from 'cytoscape';
import { FiMaximize } from 'react-icons/fi';
import { LineageEdge, LineageNode } from '../services/api';

interface LineageGraphProps {
  nodes: LineageNode[];
  edges: LineageEdge[];
  selectedId: string | null;
  /** When set, every node outside this set is dimmed (e.g. blast radius). */
  highlightIds: Set<string> | null;
  /** If fitting everything would be unreadable, center on this node instead. */
  centerId?: string | null;
  onSelect: (id: string | null) => void;
}

const COLUMN_GAP = 210;
const LABELLED_COLUMN_GAP = 300; // room for job names on the arrows
const ROW_GAP = 78;
const MAX_FIT_ZOOM = 1.1;
const MIN_READABLE_ZOOM = 0.75;

/**
 * Left-to-right layered layout: each node's column is the longest path from
 * a source, so data always flows rightward. Rows are ordered by the average
 * row of each node's predecessors to keep edge crossings down.
 */
const layeredPositions = (nodes: LineageNode[], edges: LineageEdge[], columnGap: number) => {
  const preds = new Map<string, string[]>();
  const succs = new Map<string, string[]>();
  const indegree = new Map<string, number>();
  nodes.forEach((n) => {
    preds.set(n.id, []);
    succs.set(n.id, []);
    indegree.set(n.id, 0);
  });
  edges.forEach((e) => {
    if (!preds.has(e.target) || !succs.has(e.source)) return;
    preds.get(e.target)!.push(e.source);
    succs.get(e.source)!.push(e.target);
    indegree.set(e.target, indegree.get(e.target)! + 1);
  });

  const rank = new Map<string, number>(nodes.map((n) => [n.id, 0]));
  const queue = nodes.filter((n) => indegree.get(n.id) === 0).map((n) => n.id);
  while (queue.length) {
    const id = queue.shift()!;
    succs.get(id)!.forEach((next) => {
      rank.set(next, Math.max(rank.get(next)!, rank.get(id)! + 1));
      indegree.set(next, indegree.get(next)! - 1);
      if (indegree.get(next) === 0) queue.push(next);
    });
  }
  // Nodes on a cycle (e.g. an INOUT dataset) keep the rank they reached.

  const columns = new Map<number, LineageNode[]>();
  nodes.forEach((n) => {
    const r = rank.get(n.id)!;
    columns.set(r, [...(columns.get(r) || []), n]);
  });

  const row = new Map<string, number>();
  const positions: Record<string, { x: number; y: number }> = {};
  Array.from(columns.keys())
    .sort((a, b) => a - b)
    .forEach((r) => {
      const column = columns.get(r)!;
      const score = (n: LineageNode) => {
        const rows = preds.get(n.id)!.map((p) => row.get(p)).filter((v) => v !== undefined);
        return rows.length ? rows.reduce((a, b) => a! + b!, 0)! / rows.length : Infinity;
      };
      column.sort((a, b) => score(a) - score(b) || a.name.localeCompare(b.name));
      column.forEach((n, i) => {
        row.set(n.id, i);
        positions[n.id] = { x: r * columnGap, y: (i - (column.length - 1) / 2) * ROW_GAP };
      });
    });
  return positions;
};

const statusIcon: Record<string, string> = { FAILED: '✖ ', RUNNING: '▶ ' };
const SLA_LATE = new Set(['LATE', 'COMPLETED_LATE']);

const toElements = (nodes: LineageNode[], edges: LineageEdge[]): ElementDefinition[] => {
  const labelled = edges.some((e) => e.label);
  const positions = layeredPositions(nodes, edges, labelled ? LABELLED_COLUMN_GAP : COLUMN_GAP);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const failed = (id: string) => {
    const n = byId.get(id);
    return n?.type === 'job' && n.run_status === 'FAILED';
  };

  return [
    ...nodes.map((n) => {
      const slaLate = n.type === 'job' && n.sla && SLA_LATE.has(n.sla.status) ? '⏰ ' : '';
      const label =
        n.type === 'job'
          ? `${slaLate}${statusIcon[n.run_status] || ''}${n.name}\n${n.scheduler_system || ''} · ${n.schedule_name || ''}`
          : `${n.name}\n${n.subtitle ?? n.dataset_type ?? ''}`;
      const classes = [
        n.impacted ? 'impacted' : '',
        n.type === 'dataset' && n.dataset_type === 'DATABASE' ? 'database' : '',
      ];
      return {
        group: 'nodes' as const,
        data: {
          id: n.id,
          label,
          kind: n.type === 'job' ? n.job_type : `DS_${n.platform}`,
          status: n.type === 'job' ? n.run_status : '',
        },
        classes: classes.filter(Boolean).join(' '),
        position: positions[n.id],
      };
    }),
    ...edges.map((e) => {
      const impacted =
        byId.get(e.target)?.impacted && (byId.get(e.source)?.impacted || failed(e.source));
      const classes = [impacted ? 'impacted' : '', e.status === 'FAILED' ? 'failed' : ''];
      return {
        group: 'edges' as const,
        data: { id: e.id, source: e.source, target: e.target, ...(e.label ? { label: e.label } : {}) },
        classes: classes.filter(Boolean).join(' '),
      };
    }),
  ];
};

const style: cytoscape.StylesheetJson = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'text-wrap': 'wrap',
      'text-max-width': '156px',
      'text-overflow-wrap': 'anywhere',
      'text-valign': 'center',
      'text-halign': 'center',
      'font-size': 12,
      width: 170,
      height: 54,
      'border-width': 2,
    },
  },
  // Jobs: solid fill, coloured by platform
  { selector: 'node[kind="JCL"]', style: { shape: 'round-rectangle', 'background-color': '#3730a3', 'border-color': '#312e81', color: '#fff' } },
  { selector: 'node[kind="TERADATA_LOAD"]', style: { shape: 'round-rectangle', 'background-color': '#c2410c', 'border-color': '#9a3412', color: '#fff' } },
  { selector: 'node[kind="AB_INITIO_GRAPH"]', style: { shape: 'round-rectangle', 'background-color': '#0f766e', 'border-color': '#115e59', color: '#fff' } },
  // Datasets: light fill, coloured border, by where the data lives
  { selector: 'node[kind="DS_MAINFRAME"]', style: { shape: 'barrel', 'background-color': '#eef2ff', 'border-color': '#6366f1', color: '#1e1b4b' } },
  { selector: 'node[kind="DS_TERADATA"]', style: { shape: 'barrel', 'background-color': '#fff7ed', 'border-color': '#f97316', color: '#431407' } },
  { selector: 'node[kind="DS_HADOOP"]', style: { shape: 'barrel', 'background-color': '#f0fdfa', 'border-color': '#14b8a6', color: '#042f2e' } },
  // Run status
  { selector: 'node[status="FAILED"]', style: { 'border-color': '#dc2626', 'border-width': 5 } },
  { selector: 'node[status="RUNNING"]', style: { 'border-color': '#60a5fa', 'border-width': 4, 'border-style': 'dashed' } },
  // Blast radius of failed jobs
  { selector: 'node.impacted', style: { 'underlay-color': '#f59e0b', 'underlay-opacity': 0.45, 'underlay-padding': 7 } },
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'curve-style': 'bezier',
    },
  },
  {
    selector: 'edge[label]',
    style: {
      label: 'data(label)',
      'font-size': 10,
      color: '#334155',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.9,
      'text-background-padding': '2px',
      'text-background-shape': 'roundrectangle',
      'text-max-width': '110px',
      'text-wrap': 'ellipsis',
    },
  },
  { selector: 'edge.impacted', style: { width: 3, 'line-color': '#f59e0b', 'target-arrow-color': '#f59e0b' } },
  { selector: 'edge.failed', style: { width: 3, 'line-color': '#dc2626', 'target-arrow-color': '#dc2626', color: '#b91c1c' } },
  { selector: 'node.database', style: { shape: 'round-rectangle', 'border-width': 3, 'font-weight': 'bold' } },
  { selector: '.selected-node', style: { 'overlay-color': '#111827', 'overlay-opacity': 0.2, 'overlay-padding': 8 } },
  { selector: '.dimmed', style: { opacity: 0.15 } },
];

const LineageGraph: React.FC<LineageGraphProps> = ({
  nodes,
  edges,
  selectedId,
  highlightIds,
  centerId,
  onSelect,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    if (!containerRef.current) return;
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(nodes, edges),
      style,
      layout: { name: 'preset', fit: true, padding: 30 },
      minZoom: 0.15,
      maxZoom: 2.5,
      wheelSensitivity: 0.2,
      autoungrabify: true,
    });
    cy.on('tap', 'node', (evt) => onSelectRef.current(evt.target.id()));
    cy.on('tap', (evt) => {
      if (evt.target === cy) onSelectRef.current(null);
    });
    // Fit everything, but don't blow a small focused subgraph up to giant nodes.
    if (cy.zoom() > MAX_FIT_ZOOM) {
      cy.zoom(MAX_FIT_ZOOM);
      cy.center();
    } else if (centerId && cy.zoom() < MIN_READABLE_ZOOM && cy.getElementById(centerId).nonempty()) {
      // Too big to fit readably: zoom in around the focus node, then slide the graph
      // toward any empty side so the focus's upstream/downstream fills the view.
      const focusNode = cy.getElementById(centerId);
      cy.zoom(MIN_READABLE_ZOOM);
      cy.center(focusNode);
      const pad = 30;
      const width = cy.width();
      const box = cy.elements().renderedBoundingBox();
      let dx = 0;
      if (box.x2 < width - pad) dx = width - pad - box.x2;
      else if (box.x1 > pad) dx = pad - box.x1;
      const fx = focusNode.renderedPosition().x;
      const half = focusNode.renderedWidth() / 2;
      dx = Math.min(Math.max(dx, pad + half - fx), width - pad - half - fx); // keep focus on screen
      cy.panBy({ x: dx, y: 0 });
    }
    cyRef.current = cy;
    // Keep cytoscape's viewport in sync when the container is resized
    // (e.g. the details drawer opening next to it).
    const resizeObserver = new ResizeObserver(() => cy.resize());
    resizeObserver.observe(containerRef.current);
    return () => {
      resizeObserver.disconnect();
      cy.destroy();
      cyRef.current = null;
    };
    // Re-run only when the graph itself changes, not when the center hint does.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [nodes, edges]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.batch(() => {
      cy.elements().removeClass('selected-node dimmed');
      if (selectedId) cy.getElementById(selectedId).addClass('selected-node');
      if (highlightIds) {
        cy.nodes().forEach((n) => {
          if (!highlightIds.has(n.id())) n.addClass('dimmed');
        });
        cy.edges().forEach((e) => {
          if (!highlightIds.has(e.source().id()) || !highlightIds.has(e.target().id())) {
            e.addClass('dimmed');
          }
        });
      }
    });
  }, [selectedId, highlightIds, nodes, edges]);

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <button
        onClick={() => cyRef.current?.fit(undefined, 30)}
        title="Fit to screen"
        className="absolute top-3 left-3 p-2 bg-white border border-gray-200 rounded-lg shadow-sm text-gray-600 hover:bg-gray-50"
      >
        <FiMaximize size={16} />
      </button>
    </div>
  );
};

export default LineageGraph;
