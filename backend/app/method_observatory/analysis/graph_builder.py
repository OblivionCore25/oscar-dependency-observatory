import networkx as nx
from ..models.method_node import MethodNode
from ..models.call_edge import CallEdge, CallType


class GraphBuilder:
    """
    Assembles a NetworkX DiGraph from the resolved call edges and method nodes.
    The graph is the in-memory representation used for all metric computation.
    """

    def build(
        self,
        methods: list[MethodNode],
        calls: list[CallEdge],
    ) -> nx.DiGraph:
        G = nx.DiGraph()

        # Add all method nodes with their attributes as node data
        for method in methods:
            G.add_node(method.id, **{
                "name": method.name,
                "module": method.module,
                "class_name": method.class_name,
                "kind": method.kind,
                "file_path": method.file_path,
                "line_start": method.line_start,
                "complexity": method.complexity,
                "loc": method.loc,
            })

        # Add edges from resolved calls
        # Only include edges where both source and target are in the project
        # (i.e., both are in the method node set — skip "unresolved:*" targets)
        project_ids = {m.id for m in methods}
        for call in calls:
            if call.target_id in project_ids and call.source_id in project_ids:
                # If a parallel edge already exists (same source+target, different call site),
                # keep the one with higher confidence; this is a simple graph (not multigraph)
                if G.has_edge(call.source_id, call.target_id):
                    existing = G[call.source_id][call.target_id]
                    if call.confidence > existing.get("confidence", 0):
                        G[call.source_id][call.target_id].update({
                            "call_type": call.call_type,
                            "confidence": call.confidence,
                        })
                else:
                    G.add_edge(call.source_id, call.target_id, **{
                        "call_type": call.call_type,
                        "confidence": call.confidence,
                        "line": call.line,
                    })

        return G
