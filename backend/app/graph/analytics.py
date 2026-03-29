"""
OSCAR Dependency Graph Observatory — Analytics Service

Computes central metrics on the graph structure using flat files.
"""

import logging
from typing import List, Dict, Optional
from collections import defaultdict
import networkx as nx

from app.storage import StorageService
from app.models.api import PackageMetrics, TopRiskItem, TopRiskResponse, CoverageResponse
from app.graph.direct import DirectDependencyService

class AnalyticsService:
    """
    Computes analytics across the stored package edges.
    """
    
    def __init__(self, storage: StorageService):
        self.storage = storage

    async def get_package_metrics(self, ecosystem: str, package_name: str, version: str) -> PackageMetrics:
        """
        Calculates fan-in, fan-out, and bottleneck scores for a specific package.
        """
        # Fan-out (direct dependencies of this specific version)
        direct_edges = self.storage.get_edges_for_version(ecosystem, package_name, version)
        fan_out = len(direct_edges)
        
        # Fan-in: count unique PACKAGE NAMES that depend on this package (deduped across versions)
        all_edges = self.storage.get_all_edges(ecosystem)
        dependent_packages: set = set()
        for edge in all_edges:
            if edge.target_package == package_name:
                dependent_packages.add(edge.source_package)  # add name, not per-version edge
                
        fan_in = len(dependent_packages)
        
        bottleneck_score = float(fan_in * fan_out)
        
        # Calculate Advanced Metrics for this specific package
        G = nx.DiGraph()
        for edge in all_edges:
            G.add_edge(edge.source_package, edge.target_package)

        page_rank = 0.0
        closeness = 0.0
        betweenness = 0.0
        blast_radius = 0

        if G.number_of_nodes() > 0:
            try:
                page_rank = nx.pagerank(G, alpha=0.85).get(package_name, 0.0)
            except nx.PowerIterationFailedConvergence:
                pass

            try:
                closeness = nx.closeness_centrality(G).get(package_name, 0.0)
            except Exception:
                pass

            try:
                # Approximate betweenness centrality for performance, using k=min(nodes, 50)
                # This measures the package's role as a bridge between different sub-ecosystems.
                k = min(G.number_of_nodes(), 50)
                betweenness_dict = nx.betweenness_centrality(G, k=k)
                betweenness = betweenness_dict.get(package_name, 0.0)
            except Exception:
                pass

            try:
                # Blast Radius: The number of unique packages that transitively depend on this package.
                # In a directed dependency graph A -> B, descendants(G, B) are NOT A.
                # To find dependents, we need the reverse graph or to use ancestors.
                blast_radius_nodes = nx.ancestors(G, package_name)
                blast_radius = len(blast_radius_nodes)
            except Exception:
                pass

        # Diamond Dependency Detection
        # Traverse the sub-graph from this package to count diamonds (reachable via multiple distinct paths)
        diamond_count = 0
        transitive_deps = 0
        if fan_out > 0:
            # We only look downstream (what this package depends on)
            descendants = set()
            try:
                descendants = nx.descendants(G, package_name)
                transitive_deps = len(descendants)

                # A naive approach to diamonds: count nodes that have an in-degree > 1
                # strictly within the subgraph originating from `package_name`
                subgraph = G.subgraph(descendants | {package_name})
                for node in descendants:
                    # if a downstream node is reachable via multiple immediate parents in this subgraph, it's a diamond
                    if subgraph.in_degree(node) > 1:
                        diamond_count += 1
            except nx.NetworkXError:
                pass

        return PackageMetrics(
            directDependencies=fan_out,
            transitiveDependencies=transitive_deps,
            fanIn=fan_in,
            fanOut=fan_out,
            bottleneckScore=bottleneck_score,
            diamondCount=diamond_count,
            pageRank=page_rank,
            closenessCentrality=closeness,
            betweennessCentrality=betweenness,
            blastRadius=blast_radius
        )

    async def get_top_risk(self, ecosystem: str, limit: int = 10) -> TopRiskResponse:
        """
        Retrieves the most depended-upon packages globally in our storage database.
        """
        all_edges = self.storage.get_all_edges(ecosystem)
        
        # Build NetworkX DiGraph for advanced metrics
        G = nx.DiGraph()

        # fan_in: unique SOURCE PACKAGE NAMES that depend on a target (deduplicated across versions)
        fan_in_map: Dict[str, set] = defaultdict(set)
        # fan_out: number of dependencies each package declares (edge count across versions)
        fan_out_map: Dict[str, int] = defaultdict(int)
        
        all_pkgs_map: Dict[str, str] = {}
        for edge in all_edges:
            fan_in_map[edge.target_package].add(edge.source_package)  # set dedup: react@18.0+18.1 = 1 unique dependent
            fan_out_map[edge.source_package] += 1
            all_pkgs_map[edge.source_package] = edge.source_version
            
            # Add to graph
            G.add_edge(edge.source_package, edge.target_package)

        # Get actual versions for target packages from storage if available
        all_versions = self.storage.get_all_versions(ecosystem)
        latest_versions = {}
        for v in all_versions:
            # simple override gets us latest mapped chronologically
            latest_versions[v.package_name] = v.version
            
        # Union of all known packages (appear either as source or target)
        all_known_packages = set(fan_in_map.keys()) | set(fan_out_map.keys())

        # Compute Advanced Metrics
        pagerank_scores = {}
        closeness_scores = {}
        betweenness_scores = {}

        if G.number_of_nodes() > 0:
            try:
                pagerank_scores = nx.pagerank(G, alpha=0.85, max_iter=100)
            except nx.PowerIterationFailedConvergence:
                logging.getLogger(__name__).warning("PageRank failed to converge")

            try:
                # Note: Closeness centrality on directed graphs is based on incoming paths
                # and can be expensive on very large graphs. In an MVP context with < 1M edges, it's generally okay.
                closeness_scores = nx.closeness_centrality(G)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Closeness Centrality failed: {e}")

            try:
                k = min(G.number_of_nodes(), 50)
                betweenness_scores = nx.betweenness_centrality(G, k=k)
            except Exception as e:
                logging.getLogger(__name__).warning(f"Betweenness Centrality failed: {e}")
            
        items = []
        for pkg in all_known_packages:
            fan_in = len(fan_in_map.get(pkg, set()))  # unique package count
            fan_out = fan_out_map.get(pkg, 0)
            version = latest_versions.get(pkg, all_pkgs_map.get(pkg, "unknown"))
            
            # Get the exact fan-out (direct dependencies) for this specific version
            version_edges = self.storage.get_edges_for_version(ecosystem, pkg, version)
            version_fan_out = len(version_edges)
            
            # Bottleneck = fan_in × fan_out: high when a pkg is both heavily used AND has many deps
            bottleneck_score = float(fan_in * fan_out) if fan_out > 0 else float(fan_in)
            items.append(
                TopRiskItem(
                    id=f"{ecosystem}:{pkg}@{version}",
                    ecosystem=ecosystem,
                    name=pkg,
                    version=version,
                    fanIn=fan_in,
                    fanOut=fan_out,
                    versionFanOut=version_fan_out,
                    bottleneckScore=bottleneck_score,
                    bottleneckPercentile=0.0,  # filled in below
                    page_rank=pagerank_scores.get(pkg, 0.0),
                    closeness_centrality=closeness_scores.get(pkg, 0.0),
                    betweenness_centrality=betweenness_scores.get(pkg, 0.0),
                    blast_radius=len(nx.ancestors(G, pkg)) if G.has_node(pkg) else 0,
                )
            )

        # Compute percentile rank across ALL packages (before slicing to limit)
        # Sort ascending so we can assign rank by position
        total = len(items)
        if total > 1:
            items.sort(key=lambda x: x.bottleneck_score)  # ascending for rank
            for rank, item in enumerate(items):
                # Use mid-point convention: items with same score share the average rank
                item.bottleneck_percentile = round((rank / (total - 1)) * 100, 1)
        elif total == 1:
            items[0].bottleneck_percentile = 100.0

        # Sort desc by bottleneck score (fan_in × fan_out), then fan_in as tie-breaker
        items.sort(key=lambda x: (x.bottleneck_score, x.fan_in), reverse=True)
        top_items = items[:limit]

        return TopRiskResponse(items=top_items, totalPackages=total)

    # Known ecosystem sizes (approximate published figures, updated 2024)
    _ECOSYSTEM_ESTIMATES: Dict[str, int] = {
        "npm": 3_000_000,
        "pypi": 550_000,
        "maven": 600_000,
        "cargo": 150_000,
    }

    async def get_coverage(self, ecosystem: str) -> CoverageResponse:
        """
        Returns graph coverage statistics for the given ecosystem:
        how many unique packages are ingested vs. the estimated ecosystem total.
        """
        all_versions = self.storage.get_all_versions(ecosystem)
        unique_packages: set = {v.package_name for v in all_versions}
        # Also count packages that only appear as edge targets (not yet fully ingested)
        all_edges = self.storage.get_all_edges(ecosystem)
        for edge in all_edges:
            unique_packages.add(edge.source_package)
            unique_packages.add(edge.target_package)

        ingested = len(unique_packages)
        estimated = self._ECOSYSTEM_ESTIMATES.get(ecosystem.lower(), 0)
        coverage_pct = round((ingested / estimated) * 100, 4) if estimated > 0 else 0.0

        return CoverageResponse(
            ecosystem=ecosystem,
            ingestedPackages=ingested,
            estimatedTotal=estimated,
            coveragePct=coverage_pct,
        )
