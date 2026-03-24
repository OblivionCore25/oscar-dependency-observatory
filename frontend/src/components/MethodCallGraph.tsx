import { useEffect, useRef, useState } from "react";
import {
  SigmaContainer,
  useLoadGraph,
  useRegisterEvents,
  useSigma,
} from "@react-sigma/core";
import "@react-sigma/core/lib/style.css";
import Graph from "graphology";

interface MethodCallGraphProps {
  data: {
    nodes: any[];
    edges: any[];
    root?: string;
  };
  highlightedNodes?: string[];
  onNodeSelect?: (nodeId: string | null) => void;
}

// ── Inner component that populates the graph ──────────────────────────────── //
function GraphLoader({
  data,
  highlightedNodes,
  onNodeSelect,
  onError,
}: {
  data: MethodCallGraphProps["data"];
  highlightedNodes?: string[];
  onNodeSelect?: (id: string | null) => void;
  onError: (msg: string) => void;
}) {
  const loadGraph = useLoadGraph();
  const sigma = useSigma();
  const registerEvents = useRegisterEvents();
  const hasLoadedRef = useRef(false);

  // ── Register click handlers ────────────────────────────────────────────── //
  useEffect(() => {
    registerEvents({
      clickNode: (e) => onNodeSelect?.(e.node),
      clickStage: () => onNodeSelect?.(null),
    });
  }, [registerEvents, onNodeSelect]);

  // ── Build the graphology instance and load it into Sigma ───────────────── //
  useEffect(() => {
    if (!data?.nodes?.length) return;

    try {
      const graph = new Graph({ type: "directed" });

      const communityColors = [
        "#ef4444", "#f97316", "#f59e0b", "#84cc16", "#22c55e",
        "#10b981", "#14b8a6", "#06b6d4", "#0ea5e9", "#3b82f6",
        "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#f43f5e",
      ];

      const getCommunityColor = (cid: number | null | undefined) =>
        cid == null ? "#94a3b8" : communityColors[cid % communityColors.length];

      // ── Nodes ────────────────────────────────────────────────────────── //
      const nodeCount = data.nodes.length;
      // Spread nodes in a circle so they have sensible initial positions
      data.nodes.forEach((node, idx) => {
        const isRoot = node.id === data.root;
        const size = isRoot
          ? 15
          : Math.max(5, Math.min(20, 5 + (node.blast_radius || 0) * 0.5));

        let color = isRoot ? "#000000" : getCommunityColor(node.community_id);

        if (highlightedNodes?.length && !highlightedNodes.includes(node.id)) {
          color = "#e2e8f0";
        }

        // Place nodes on a circle so Sigma's camera can frame them
        const angle = (2 * Math.PI * idx) / nodeCount;
        const radius = Math.sqrt(nodeCount) * 10;

        graph.addNode(node.id, {
          x: Math.cos(angle) * radius,
          y: Math.sin(angle) * radius,
          size,
          label: node.name || node.id,
          color,
          hidden:
            highlightedNodes?.length
              ? !highlightedNodes.includes(node.id)
              : false,
        });
      });

      // ── Edges ────────────────────────────────────────────────────────── //
      data.edges.forEach((edge) => {
        if (
          graph.hasNode(edge.source_id) &&
          graph.hasNode(edge.target_id) &&
          edge.source_id !== edge.target_id &&
          !graph.hasEdge(edge.source_id, edge.target_id)
        ) {
          const isDynamic = edge.call_type === "dynamic";
          let edgeColor = isDynamic ? "#f43f5e" : "#cbd5e1";

          if (
            highlightedNodes?.length &&
            (!highlightedNodes.includes(edge.source_id) ||
              !highlightedNodes.includes(edge.target_id))
          ) {
            edgeColor = "transparent";
          }

          graph.addEdge(edge.source_id, edge.target_id, {
            size: isDynamic ? 3 : 1,
            color: edgeColor,
            hidden:
              highlightedNodes?.length
                ? !highlightedNodes.includes(edge.source_id) ||
                  !highlightedNodes.includes(edge.target_id)
                : false,
            type: "arrow",
          });
        }
      });

      loadGraph(graph);

      // ── Camera reset: frame all nodes after the graph is loaded ─────── //
      // Use a small timeout so Sigma finishes its internal render cycle first
      requestAnimationFrame(() => {
        try {
          const camera = sigma.getCamera();
          camera.animatedReset({ duration: 300 });
        } catch {
          // camera not ready, ignore
        }
      });

      hasLoadedRef.current = true;
    } catch (err: any) {
      console.error("[MethodCallGraph] graph build error:", err);
      onError(err.message || String(err));
    }
  }, [data, loadGraph, sigma, onError, highlightedNodes]);

  return null;
}

// ── Main wrapper component ────────────────────────────────────────────────── //
export default function MethodCallGraph({
  data,
  highlightedNodes,
  onNodeSelect,
}: MethodCallGraphProps) {
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  if (errorMsg) {
    return (
      <div className="w-full h-full bg-red-50 text-red-600 font-medium p-6 rounded-lg overflow-auto border border-red-200">
        <h3 className="font-bold text-lg mb-2">Graphology Render Crash</h3>
        <pre className="text-xs whitespace-pre-wrap">{errorMsg}</pre>
      </div>
    );
  }

  return (
    <div
      style={{ width: "100%", height: "100%", position: "relative" }}
      className="bg-slate-50 border border-gray-200 rounded-lg overflow-hidden"
    >
      <SigmaContainer
        settings={{
          allowInvalidContainer: true,
          defaultNodeType: "circle",
          defaultEdgeType: "arrow",
          labelDensity: 1.5,
          labelSize: 11,
          labelColor: { color: "#475569" },
          labelFont: "Inter, sans-serif",
          renderEdgeLabels: false,
        }}
        style={{ width: "100%", height: "100%" }}
      >
        <GraphLoader
          data={data}
          highlightedNodes={highlightedNodes}
          onNodeSelect={onNodeSelect}
          onError={setErrorMsg}
        />
      </SigmaContainer>

      {/* Legend overlays */}
      <div className="absolute bottom-4 left-4 bg-white/90 backdrop-blur-sm p-3 rounded shadow-sm border border-gray-200 text-xs pointer-events-none">
        <h4 className="font-bold text-gray-700 mb-2">Graph Legend</h4>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-3 rounded-full bg-slate-400" />
          <span className="text-gray-600">Static Node</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-0.5 bg-slate-300" />
          <span className="text-gray-600">Static AST Edge</span>
        </div>
        <div className="flex items-center gap-2 mb-1">
          <div className="w-3 h-1 bg-rose-500" />
          <span className="text-gray-600">Dynamic Trace Edge</span>
        </div>
        <div className="mt-2 text-[10px] text-gray-400">
          Node color: Louvain Community
          <br />
          Node size: Blast Radius
        </div>
      </div>
    </div>
  );
}
