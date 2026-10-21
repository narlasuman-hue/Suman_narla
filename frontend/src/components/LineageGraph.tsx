import React, { useEffect, useRef } from 'react';
import cytoscape, { Core, ElementDefinition } from 'cytoscape';
import { FiMaximize, FiMinus, FiPlus } from 'react-icons/fi';
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
const ROW_GAP = 88;
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

/** Status line under a node's name, e.g. "FAILED · LATE". */
const nodeTags = (n: LineageNode): string[] => {
  if (n.type !== 'job') return n.impacted ? ['BLOCKED'] : [];
  const tags: string[] = [];
  if (n.run_status === 'FAILED') tags.push('FAILED');
  if (n.run_status === 'RUNNING') tags.push('RUNNING');
  if (n.impacted && n.run_status !== 'FAILED') tags.push('BLOCKED');
  if (n.sla?.status === 'LATE') tags.push('LATE');
  if (n.sla?.status === 'COMPLETED_LATE') tags.push('DONE LATE');
  return tags;
};

const toElements = (
  nodes: LineageNode[],
  edges: LineageEdge[]
): ElementDefinition[] => {
  const labelled = edges.some((e) => e.label);
  const columnGap = labelled ? LABELLED_COLUMN_GAP : COLUMN_GAP;
  const positions = layeredPositions(nodes, edges, columnGap);
  const byId = new Map(nodes.map((n) => [n.id, n]));
  const failed = (id: string) => {
    const n = byId.get(id);
    return n?.type === 'job' && n.run_status === 'FAILED';
  };

  return [
    ...nodes.map((n) => {
      const tags = nodeTags(n);
      const detail =
        n.type === 'job'
          ? [n.scheduler_system, n.schedule_name].filter(Boolean).join(' · ')
          : n.subtitle ?? n.dataset_type ?? '';
      const label = [n.name, detail, tags.join(' · ')].filter(Boolean).join('\n');
      const classes = [
        n.impacted ? 'impacted' : '',
        n.type === 'dataset' && n.dataset_type === 'DATABASE' ? 'database' : '',
      ];
      return {
        group: 'nodes' as const,
        data: {
          id: n.id,
          label,
          // JOB / LOAD for jobs; TABLE (the platform's tables) / SOURCE for datasets
          kind: n.type === 'job' ? n.job_type : n.is_table ? 'TABLE' : 'SOURCE',
          status: n.type === 'job' ? n.run_status : '',
          height: tags.length ? 66 : 52,
        },
        classes: classes.filter(Boolean).join(' '),
        position: positions[n.id],
      };
    }),
    ...edges.map((e) => {
      const impacted =
        byId.get(e.target)?.impacted && (byId.get(e.source)?.impacted || failed(e.source));
      // An arrow that skips a column would run straight through the boxes in between;
      // bow it out instead.
      const from = positions[e.source];
      const to = positions[e.target];
      const skips = from && to && Math.abs(to.x - from.x) > columnGap * 1.5 && Math.abs(to.y - from.y) < ROW_GAP;
      const classes = [
        impacted ? 'impacted' : '',
        e.status === 'FAILED' ? 'failed' : '',
        skips ? 'skip' : '',
      ];
      return {
        group: 'edges' as const,
        data: { id: e.id, source: e.source, target: e.target, ...(e.label ? { label: e.label } : {}) },
        classes: classes.filter(Boolean).join(' '),
      };
    }),
  ];
};

const FONT = 'Inter, system-ui, sans-serif';

// Status comes first: failed (red), running (blue) and blocked by a failure
// (orange, dashed) override the quiet base look of every node.
const style: cytoscape.StylesheetJson = [
  {
    selector: 'node',
    style: {
      label: 'data(label)',
      'font-family': FONT,
      'font-weight': 500,
      'text-wrap': 'wrap',
      'text-max-width': '164px',
      'text-overflow-wrap': 'anywhere',
      'text-valign': 'center',
      'text-halign': 'center',
      'line-height': 1.35,
      'font-size': 11.5,
      color: '#0f172a',
      width: 184,
      height: 'data(height)',
      'border-width': 1.5,
    },
  },
  // Structure stays neutral so colour always means status. Load jobs: grey cards.
  { selector: 'node[kind="JOB"]', style: { shape: 'round-rectangle', 'background-color': '#ffffff', 'border-color': '#cbd5e1' } },
  { selector: 'node[kind="LOAD"]', style: { shape: 'round-rectangle', 'background-color': '#f1f5f9', 'border-color': '#64748b' } },
  // Datasets: barrels; the platform's tables get a darker border than sources.
  { selector: 'node[kind="SOURCE"]', style: { shape: 'barrel', 'background-color': '#f8fafc', 'border-color': '#94a3b8', color: '#334155' } },
  { selector: 'node[kind="TABLE"]', style: { shape: 'barrel', 'background-color': '#ffffff', 'border-color': '#475569', 'border-width': 2 } },
  { selector: 'node.database', style: { shape: 'round-rectangle', 'border-width': 2.5, 'font-weight': 700 } },
  // Blocked by an upstream failure
  {
    selector: 'node.impacted',
    style: { 'background-color': '#fff7ed', 'background-opacity': 1, 'border-color': '#ea580c', 'border-width': 2.5, 'border-style': 'dashed', color: '#7c2d12' },
  },
  // Run status
  {
    selector: 'node[status="FAILED"]',
    style: { 'background-color': '#fef2f2', 'background-opacity': 1, 'border-color': '#dc2626', 'border-width': 3, 'border-style': 'solid', color: '#7f1d1d', 'font-weight': 600 },
  },
  {
    selector: 'node[status="RUNNING"]',
    style: { 'background-color': '#eff6ff', 'background-opacity': 1, 'border-color': '#2563eb', 'border-width': 3, 'border-style': 'solid', color: '#1e3a8a' },
  },
  {
    selector: 'edge',
    style: {
      width: 1.5,
      'line-color': '#94a3b8',
      'target-arrow-color': '#94a3b8',
      'target-arrow-shape': 'triangle',
      'arrow-scale': 1.1,
      'curve-style': 'bezier',
    },
  },
  {
    selector: 'edge[label]',
    style: {
      label: 'data(label)',
      'font-family': FONT,
      'font-size': 10,
      color: '#334155',
      'text-background-color': '#ffffff',
      'text-background-opacity': 0.95,
      'text-background-padding': '3px',
      'text-background-shape': 'roundrectangle',
      'text-max-width': '110px',
      'text-wrap': 'ellipsis',
    },
  },
  {
    selector: 'edge.skip',
    style: { 'curve-style': 'unbundled-bezier', 'control-point-distances': [-55], 'control-point-weights': [0.5] },
  },
  { selector: 'edge.impacted', style: { width: 2.5, 'line-color': '#ea580c', 'target-arrow-color': '#ea580c' } },
  { selector: 'edge.failed', style: { width: 2.5, 'line-color': '#dc2626', 'target-arrow-color': '#dc2626', color: '#b91c1c' } },
  { selector: '.selected-node', style: { 'overlay-color': '#2563eb', 'overlay-opacity': 0.14, 'overlay-padding': 7 } },
  { selector: '.dimmed', style: { opacity: 0.18 } },
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

  const zoomBy = (factor: number) => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * factor, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };
  const controls = [
    { label: 'Zoom in', icon: FiPlus, onClick: () => zoomBy(1.25) },
    { label: 'Zoom out', icon: FiMinus, onClick: () => zoomBy(0.8) },
    { label: 'Fit to screen', icon: FiMaximize, onClick: () => cyRef.current?.fit(undefined, 30) },
  ];

  return (
    <div className="relative h-full w-full">
      <div ref={containerRef} className="h-full w-full" />
      <div className="absolute bottom-3 right-3 flex flex-col divide-y divide-gray-200 overflow-hidden rounded-lg bg-white shadow">
        {controls.map((c) => (
          <button
            key={c.label}
            onClick={c.onClick}
            title={c.label}
            aria-label={c.label}
            className="flex h-9 w-9 items-center justify-center text-gray-700 hover:bg-gray-50"
          >
            <c.icon size={15} />
          </button>
        ))}
      </div>
    </div>
  );
};

export default LineageGraph;
