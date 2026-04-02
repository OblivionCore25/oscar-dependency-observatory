"""
OSCAR Dependency Graph Observatory — Transitive Dependency Service

Provides logic for exploring full transitive graphs using BFS.
"""

from collections import deque
from typing import Set, Dict, Tuple, List

from app.models.api import TransitiveDependenciesResponse, GraphNode, GraphEdge
from app.graph.direct import DirectDependencyService

class TransitiveDependencyService:
    """
    Service for querying transitive dependency graphs.
    """

    # For the MVP, we place a hard cap on nodes to prevent unbounded ingestion
    # loops from stalling out the server or hitting API rate limits entirely.
    MAX_NODES = 1000

    def __init__(self, direct_service: DirectDependencyService):
        self.direct_service = direct_service

    async def get_transitive_graph(self, ecosystem: str, package_name: str, version: str) -> TransitiveDependenciesResponse:
        """
        Retrieves the full transitive dependency graph using Breadth-First Search.
        Automatically triggers ingestion for previously unexplored nodes.
        """
        root_id = f"{ecosystem}:{package_name}@{version}"
        
        # State tracking for BFS
        queue = deque([(package_name, version)])
        
        # Visited tracks resolving packages to avoid cycles. 
        # Format: (package_name, version)
        visited: Set[Tuple[str, str]] = set()
        visited.add((package_name, version))
        
        # API Response components
        nodes_dict: Dict[str, GraphNode] = {}
        edges_list: List[GraphEdge] = []
        
        node_count = 0
        
        while queue and node_count < self.MAX_NODES:
            current_pkg, current_ver = queue.popleft()
            current_id = f"{ecosystem}:{current_pkg}@{current_ver}"
            
            # Record structural node
            if current_id not in nodes_dict:
                nodes_dict[current_id] = GraphNode(
                    id=current_id,
                    label=f"{current_pkg}@{current_ver}",
                    ecosystem=ecosystem,
                    package=current_pkg,
                    version=current_ver
                )
                node_count += 1
            
            # Fetch direct edges (which will auto-ingest if not present locally)
            try:
                direct_deps = await self.direct_service.get_direct_dependencies(ecosystem, current_pkg, current_ver)
            except ValueError:
                # Version might be missing natively, gracefully skip mapping its children
                continue

            for dep in direct_deps:
                target_pkg = dep.name
                
                # To traverse transitively, we need a concrete version of the target package.
                # For this MVP, we will auto-ingest the target package (via get_direct_dependencies of its latest version)
                # But since we don't know its latest version yet, we can't call get_direct_dependencies directly.
                # Instead, we check storage for its versions, or trigger an ingest if missing.
                
                target_versions = self.direct_service.storage.get_versions(ecosystem, target_pkg)
                if not target_versions:
                    # Trigger ingestion
                    try:
                        await self.direct_service._ingest_npm_package(target_pkg)
                        target_versions = self.direct_service.storage.get_versions(ecosystem, target_pkg)
                    except Exception:
                        pass # Network error or 404
                
                if target_versions:
                    # Naive MVP resolution: pick the lexically/chronologically last version
                    # In a real app, we'd use a semver library against `dep.constraint`
                    resolved_ver = target_versions[-1].version
                    target_id = f"{ecosystem}:{target_pkg}@{resolved_ver}"
                    
                    edges_list.append(GraphEdge(
                        source=current_id,
                        target=target_id,
                        constraint=dep.constraint
                    ))
                    
                    # Enqueue for BFS if not visited
                    if (target_pkg, resolved_ver) not in visited:
                        visited.add((target_pkg, resolved_ver))
                        queue.append((target_pkg, resolved_ver))
                else:
                    # Could not resolve any versions for this package
                    target_id = f"{ecosystem}:{target_pkg}"
                    edges_list.append(GraphEdge(
                        source=current_id,
                        target=target_id,
                        constraint=dep.constraint
                    ))
        
        # Add any targets that were exclusively edges (unresolved) to our nodes list
        for edge in edges_list:
            if edge.target not in nodes_dict:
                pkg_only = edge.target.split(":")[-1].split("@")[0]
                nodes_dict[edge.target] = GraphNode(
                    id=edge.target,
                    label=edge.target.split(":")[-1],
                    ecosystem=ecosystem,
                    package=pkg_only,
                    version="unknown"
                )
        
        return TransitiveDependenciesResponse(
            root=root_id,
            nodes=list(nodes_dict.values()),
            edges=edges_list
        )
