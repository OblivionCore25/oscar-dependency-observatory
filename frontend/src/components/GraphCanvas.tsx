import { useMemo, useRef, useState } from 'react';
import CytoscapeComponent from 'react-cytoscapejs';
import cytoscape from 'cytoscape';
import type { TransitiveGraphResponse } from '../types/api';

interface GraphCanvasProps {
  data: TransitiveGraphResponse;
  onEdgeSelect?: (edge: { source: string; target: string } | null) => void;
}

interface EdgeTooltip {
  source: string;
  target: string;
  constraint: string;
  x: number;
  y: number;
}

export default function GraphCanvas({ data, onEdgeSelect }: GraphCanvasProps) {
  const cyRef = useRef<cytoscape.Core | null>(null);
  const [tooltip, setTooltip] = useState<EdgeTooltip | null>(null);

  // Translate the strictly typed backend generic models directly into Cytoscape abstract element maps
  const elements = useMemo(() => {
    const nodes = data.nodes.map(node => ({
      data: {
        id: node.id,
        label: node.label || node.package,
        isRoot: node.id === data.root,
      }
    }));

    const edges = data.edges.map(edge => ({
      data: {
        source: edge.source,
        target: edge.target,
        constraint: edge.constraint || 'unconstrained',
      }
    }));

    return [...nodes, ...edges] as cytoscape.ElementDefinition[];
  }, [data]);

  // Apply default styling dynamically separating root elements and generic bounds
  const stylesheet = [
    {
      selector: 'node',
      style: {
        'label': 'data(label)',
        'font-family': 'Inter, sans-serif',
        'font-size': '10px',
        'text-valign': 'center',
        'text-halign': 'center',
        'background-color': '#94a3b8',
        'color': '#111827',
        'text-outline-width': 1.5,
        'text-outline-color': '#fff',
        'width': 40,
        'height': 40,
      }
    },
    {
      selector: 'node[?isRoot]',
      style: {
        'background-color': '#3b82f6',
        'width': 70,
        'height': 70,
        'font-weight': 'bold',
        'font-size': '12px',
        'color': '#ffffff',
        'text-outline-color': '#2563eb',
        'z-index': 100
      }
    },
    {
      selector: 'edge',
      style: {
        'width': 6,                    // Wide enough to hover/click reliably
        'line-color': '#cbd5e1',
        'target-arrow-color': '#cbd5e1',
        'target-arrow-shape': 'triangle',
        'curve-style': 'bezier',
        'opacity': 0.9,
      }
    },
    {
      // Highlight the hovered edge so users know it's interactive
      selector: 'edge:active, edge.hovered',
      style: {
        'line-color': '#3b82f6',
        'target-arrow-color': '#3b82f6',
        'width': 2.5,
      }
    }
  ] as any;

  // Wire up Cytoscape instance events for edge hover tooltip
  const handleCyInit = (cy: cytoscape.Core) => {
    cyRef.current = cy;

    cy.on('mouseover', 'edge', (evt) => {
      const edge = evt.target;
      const renderedPos = evt.renderedPosition;
      edge.addClass('hovered');
      setTooltip({
        source: edge.data('source'),
        target: edge.data('target'),
        constraint: edge.data('constraint'),
        x: renderedPos.x,
        y: renderedPos.y,
      });
    });

    cy.on('mouseout', 'edge', (evt) => {
      evt.target.removeClass('hovered');
      setTooltip(null);
    });

    // Click/tap on edge to pin the tooltip (useful on touch screens and for testing)
    cy.on('tap', 'edge', (evt) => {
      const edge = evt.target;
      const renderedPos = evt.renderedPosition;
      cy.elements('edge').removeClass('hovered');
      edge.addClass('hovered');
      setTooltip({
        source: edge.data('source'),
        target: edge.data('target'),
        constraint: edge.data('constraint'),
        x: renderedPos.x,
        y: renderedPos.y,
      });
      onEdgeSelect?.({ source: edge.data('source'), target: edge.data('target') });
    });

    // Tap on background to dismiss pinned tooltip
    cy.on('tap', (evt) => {
      if (evt.target === cy) {
        cy.elements('edge').removeClass('hovered');
        setTooltip(null);
        onEdgeSelect?.(null);
      }
    });

    // Clear on pan/zoom
    cy.on('pan zoom', () => {
      setTooltip(null);
    });
  };

  // Classify the constraint severity for color coding
  const getConstraintBadgeStyle = (constraint: string): string => {
    if (!constraint || constraint === 'unconstrained') return 'bg-red-100 text-red-800 border border-red-200';
    if (constraint.startsWith('==') || constraint.includes('===')) return 'bg-amber-100 text-amber-800 border border-amber-200';
    return 'bg-green-100 text-green-800 border border-green-200';
  };

  const getConstraintLabel = (constraint: string): string => {
    if (!constraint || constraint === 'unconstrained') return 'Unconstrained ⚠️';
    if (constraint.startsWith('==') || constraint.includes('===')) return 'Pinned 🔒';
    return 'Range Bounded ✓';
  };

  return (
    <div className="w-full h-full relative cursor-grab active:cursor-grabbing">
      <CytoscapeComponent
        elements={elements}
        style={{ width: '100%', height: '100%' }}
        stylesheet={stylesheet}
        layout={{
          name: 'cose',
          padding: 50,
          animate: false,
          nodeRepulsion: 400000,
          idealEdgeLength: 100,
        }}
        minZoom={0.1}
        maxZoom={3.5}
        cy={handleCyInit}
      />

      {/* Edge hover tooltip */}
      {tooltip && (
        <div
          className="absolute z-20 pointer-events-none"
          style={{ left: tooltip.x + 16, top: tooltip.y - 8 }}
        >
          <div className="bg-white border border-gray-200 shadow-lg rounded-lg p-3 text-xs min-w-[180px]">
            <div className="font-semibold text-gray-700 mb-2 flex items-center gap-1">
              <span className="text-gray-400">Edge Constraint</span>
            </div>
            <div className="space-y-1.5">
              <div className="flex justify-between">
                <span className="text-gray-500">From:</span>
                <span className="font-mono font-medium text-gray-800 truncate max-w-[110px]">{tooltip.source}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-500">To:</span>
                <span className="font-mono font-medium text-gray-800 truncate max-w-[110px]">{tooltip.target}</span>
              </div>
              <div className="border-t border-gray-100 pt-1.5 mt-1.5">
                <span className="text-gray-500 block mb-1">Constraint:</span>
                <span className={`font-mono text-xs px-2 py-0.5 rounded-full font-semibold ${getConstraintBadgeStyle(tooltip.constraint)}`}>
                  {tooltip.constraint}
                </span>
              </div>
              <div className="text-[10px] text-gray-400 pt-0.5">
                {getConstraintLabel(tooltip.constraint)}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Hint badge — only shown when graph has edges */}
      {data.edges.length > 0 && (
        <div className="absolute bottom-4 right-4 bg-white/80 backdrop-blur-sm border border-gray-200 rounded-md px-3 py-1.5 text-xs text-gray-500 pointer-events-none shadow-sm">
          Hover over an edge to inspect version constraint
        </div>
      )}
    </div>
  );
}
