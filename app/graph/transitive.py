"""
OSCAR Dependency Graph Observatory — Transitive Dependency Service

Provides logic for exploring the complete transitive dependency graph using
BFS, bounded by MAX_NODES to prevent unbounded ingestion.

Performance design
------------------
Two complementary optimisations keep repeated and large queries fast:

1. Per-request in-memory cache (local dicts)
   Every get_versions / get_edges_for_version DB call is memoised for the
   lifetime of one get_transitive_graph() invocation.  A shared dep like
   `jmespath` appearing under five different packages only triggers one DB
   round-trip instead of five (O(unique_packages) vs O(3N)).

2. Concurrent child ingestion via asyncio.gather
   When a BFS level expands to K child packages that are not yet in storage,
   instead of fetching them sequentially (K × ~300 ms = seconds of wait) we
   fire all K registry HTTP calls concurrently and await them together.  This
   turns an 8-minute cold-start into a near-linear function of the slowest
   single registry response, regardless of fan-out width.
"""

import asyncio
import logging
from collections import deque
from typing import Dict, List, Optional, Tuple

from app.models.api import GraphEdge, GraphNode, TransitiveDependenciesResponse
from app.graph.direct import DirectDependencyService
from app.models.domain import DependencyEdge, Version

logger = logging.getLogger("oscar")

# Maximum concurrent registry HTTP requests during a cold-start ingestion.
# Keeps us well below rate-limit thresholds for both PyPI and npm.
_MAX_CONCURRENT_INGEST = 10


class TransitiveDependencyService:
    """Service for querying transitive dependency graphs."""

    # Hard cap on nodes — stops BFS once the graph reaches this size.
    # Keeps ingestion bounded and the Cytoscape canvas responsive.
    MAX_NODES = 1000

    def __init__(self, direct_service: DirectDependencyService):
        self.direct_service = direct_service

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def stream_transitive_graph(
        self,
        ecosystem: str,
        package_name: str,
        version: str,
    ):
        """
        Retrieves the complete transitive dependency graph using Breadth-First Search.
        BFS continues until the graph is fully explored or MAX_NODES is reached.

        This is an active generator yielding progress state during resolution,
        ending with a 'complete' event containing the final payload.

        Args:
            ecosystem:    'npm' or 'pypi'
            package_name: Root package name
            version:      Root package version
        """
        root_id = f"{ecosystem}:{package_name}@{version}"

        # ── Per-request caches ──────────────────────────────────────────
        _versions_cache: Dict[Tuple[str, str], List[Version]] = {}
        _edges_cache: Dict[Tuple[str, str, str], List[DependencyEdge]] = {}

        def cached_get_versions(eco: str, pkg: str) -> List[Version]:
            key = (eco, pkg)
            if key not in _versions_cache:
                _versions_cache[key] = self.direct_service.storage.get_versions(eco, pkg)
            return _versions_cache[key]

        def cached_get_edges(eco: str, pkg: str, ver: str) -> List[DependencyEdge]:
            key = (eco, pkg, ver)
            if key not in _edges_cache:
                _edges_cache[key] = self.direct_service.storage.get_edges_for_version(eco, pkg, ver)
            return _edges_cache[key]

        async def ensure_ingested(eco: str, pkg: str, ver: Optional[str] = None) -> bool:
            """Ensures a package is in storage, ingesting if necessary."""
            versions = cached_get_versions(eco, pkg)
            if ver:
                if any(v.version == ver for v in versions):
                    return True
            elif versions:
                return True

            try:
                await self.direct_service._ingest_package(eco, pkg, ver)
            except Exception:
                return False

            # Refresh local cache after ingestion
            fresh = self.direct_service.storage.get_versions(eco, pkg)
            _versions_cache[(eco, pkg)] = fresh
            return bool(fresh)

        async def resolve_child_version(eco: str, pkg: str) -> Optional[str]:
            """Returns the latest known version for a child package (cache-first)."""
            versions = cached_get_versions(eco, pkg)
            if not versions:
                ok = await ensure_ingested(eco, pkg)
                if not ok:
                    return None
                versions = cached_get_versions(eco, pkg)
            return versions[-1].version if versions else None

        # ── BFS state ───────────────────────────────────────────────────
        # We process the graph level-by-level so we can batch-ingest all
        # missing packages at the same depth concurrently.
        # current_level holds (pkg_name, version) pairs ready to expand.
        current_level: List[Tuple[str, str]] = [(package_name, version)]
        visited: Dict[Tuple[str, str], int] = {(package_name, version): 0}

        nodes_dict: Dict[str, GraphNode] = {}
        edges_list: List[GraphEdge] = []
        node_count = 0

        depth = 0
        while current_level and node_count < self.MAX_NODES:
            # Record all nodes at this level
            for pkg, ver in current_level:
                node_id = f"{ecosystem}:{pkg}@{ver}"
                if node_id not in nodes_dict:
                    nodes_dict[node_id] = GraphNode(
                        id=node_id,
                        label=f"{pkg}@{ver}",
                        ecosystem=ecosystem,
                        package=pkg,
                        version=ver,
                    )
                    node_count += 1

            # ── Step 1: Ensure all current-level packages are ingested ──
            # Missing packages are fetched concurrently (bounded parallelism).
            missing = [
                (pkg, ver) for pkg, ver in current_level
                if not any(v.version == ver for v in cached_get_versions(ecosystem, pkg))
            ]

            # Yield progress before potential slow ingestion
            yield {
                "type": "progress",
                "processed": node_count - len(current_level),
                "discovered": len(visited),
                "inQueue": len(current_level),
                "missing": len(missing)
            }

            if missing:
                sem = asyncio.Semaphore(_MAX_CONCURRENT_INGEST)

                async def ingest_one(p: str, v: str) -> None:
                    async with sem:
                        await ensure_ingested(ecosystem, p, v)

                logger.info(
                    "BFS depth %d: ingesting %d missing packages concurrently (max %d parallel)",
                    depth, len(missing), _MAX_CONCURRENT_INGEST,
                )
                await asyncio.gather(*[ingest_one(p, v) for p, v in missing])

            # ── Step 2: Collect all edges for the current level ──────────
            next_level_candidates: Dict[str, GraphEdge] = {}  # target_pkg -> edge info
            current_node_ids = {f"{ecosystem}:{p}@{v}": (p, v) for p, v in current_level}

            for pkg, ver in current_level:
                current_id = f"{ecosystem}:{pkg}@{ver}"
                raw_edges = cached_get_edges(ecosystem, pkg, ver)

                for edge in raw_edges:
                    target_pkg = edge.target_package
                    # We'll resolve versions in a batch below
                    next_level_candidates[target_pkg] = (current_id, edge.version_constraint)

            # ── Step 3: Resolve child versions concurrently ──────────────
            # All packages that need a version lookup are fetched in parallel.
            unresolved_targets = list(next_level_candidates.keys())
            sem2 = asyncio.Semaphore(_MAX_CONCURRENT_INGEST)

            async def resolve_one(pkg: str) -> Tuple[str, Optional[str]]:
                async with sem2:
                    return pkg, await resolve_child_version(ecosystem, pkg)

            logger.debug("BFS depth %d: resolving %d child packages", depth, len(unresolved_targets))
            resolution_results = await asyncio.gather(*[resolve_one(p) for p in unresolved_targets])

            # ── Step 4: Build edges & next BFS level ─────────────────────
            next_level: List[Tuple[str, str]] = []

            for target_pkg, resolved_ver in resolution_results:
                current_id, constraint = next_level_candidates[target_pkg]

                if resolved_ver:
                    target_id = f"{ecosystem}:{target_pkg}@{resolved_ver}"
                    edges_list.append(GraphEdge(
                        source=current_id,
                        target=target_id,
                        constraint=constraint,
                    ))
                    child_key = (target_pkg, resolved_ver)
                    if child_key not in visited:
                        visited[child_key] = depth + 1
                        next_level.append((target_pkg, resolved_ver))
                else:
                    target_id = f"{ecosystem}:{target_pkg}"
                    edges_list.append(GraphEdge(
                        source=current_id,
                        target=target_id,
                        constraint=constraint,
                    ))

            current_level = next_level
            depth += 1

        logger.info(
            "BFS complete: %d nodes, %d edges, %d version cache entries, %d edge cache entries",
            node_count, len(edges_list),
            len(_versions_cache), len(_edges_cache),
        )

        # Ensure every edge target has a matching node entry
        for edge in edges_list:
            if edge.target not in nodes_dict:
                pkg_only = edge.target.split(":")[-1].split("@")[0]
                nodes_dict[edge.target] = GraphNode(
                    id=edge.target,
                    label=edge.target.split(":")[-1],
                    ecosystem=ecosystem,
                    package=pkg_only,
                    version="unknown",
                )

        yield {
            "type": "complete",
            "data": TransitiveDependenciesResponse(
                root=root_id,
                nodes=list(nodes_dict.values()),
                edges=edges_list,
            ).model_dump(by_alias=True)
        }
