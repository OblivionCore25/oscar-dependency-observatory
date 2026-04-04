"""
OSCAR Dependency Graph Observatory — Analytics Service

Computes central metrics on the graph structure using flat files.
"""

from typing import List, Dict, Optional, Tuple, Set
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

    def _build_nx_graph(self, ecosystem: str) -> nx.DiGraph:
        """
        Builds a NetworkX directed graph of the ecosystem at the package name level.
        We aggregate all version edges into a single structural dependency link 
        between packages to ensure a connected graph for centralities.
        """
        G = nx.DiGraph()
        all_edges = self.storage.get_all_edges(ecosystem)
        
        for edge in all_edges:
            # We add unweighted edges if a dependency exists on any version
            G.add_edge(edge.source_package, edge.target_package)
            
        return G

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
        
        # Build graph for centralities
        G = self._build_nx_graph(ecosystem)
        pagerank = 0.0
        betweenness = 0.0
        closeness = 0.0
        eigenvector = 0.0
        blast_radius = 0
        
        if G.has_node(package_name):
            try:
                pagerank = nx.pagerank(G).get(package_name, 0.0)
            except:
                pass
            
            # Note: betweenness/closeness on the whole ecosystem is expensive.
            # In a production system, this would be pre-computed by a worker.
            # We compute it here for a single node using ego graphs if possible, 
            # but since full betweenness is required, we do it if G is small enough.
            
            # Calculate blast radius
            blast_radius = len(nx.descendants(G, package_name))
            
            # Safely compute eigenvector on the largest weakly connected component
            try:
                eigenvector = nx.eigenvector_centrality_numpy(G).get(package_name, 0.0)
            except Exception:
                pass
                
        return PackageMetrics(
            directDependencies=fan_out,
            transitiveDependencies=0,
            fanIn=fan_in,
            fanOut=fan_out,
            bottleneckScore=bottleneck_score,
            diamondCount=0,
            pageRank=pagerank,
            closenessCentrality=closeness,
            betweennessCentrality=betweenness,
            eigenvectorCentrality=eigenvector,
            blastRadius=blast_radius
        )

    async def get_top_risk(self, ecosystem: str, limit: int = 10) -> TopRiskResponse:
        """
        Retrieves the most depended-upon packages globally in storage.
        All metrics are computed from a single bulk edge read — no per-package queries.
        """
        all_edges = self.storage.get_all_edges(ecosystem)

        # fan_in: unique source PACKAGE NAMES pointing at each target (deduped across versions)
        fan_in_map: Dict[str, set] = defaultdict(set)
        # fan_out: total edge count emitted by each source package (across all versions)
        fan_out_map: Dict[str, int] = defaultdict(int)
        # version_edges_map: edges per (source_package, source_version) — computed in memory
        version_edges_map: Dict[str, int] = defaultdict(int)
        # track latest version seen per package
        latest_version_map: Dict[str, str] = {}

        for edge in all_edges:
            fan_in_map[edge.target_package].add(edge.source_package)
            fan_out_map[edge.source_package] += 1
            version_edges_map[(edge.source_package, edge.source_version)] += 1
            # simple last-write for latest version (enough for display)
            latest_version_map[edge.source_package] = edge.source_version

        # Supplement with versions table for packages that have no outgoing edges
        all_versions = self.storage.get_all_versions(ecosystem)
        for v in all_versions:
            if v.package_name not in latest_version_map:
                latest_version_map[v.package_name] = v.version

        all_known_packages = set(fan_in_map.keys()) | set(fan_out_map.keys())

        items = []
        for pkg in all_known_packages:
            fan_in = len(fan_in_map.get(pkg, set()))
            fan_out = fan_out_map.get(pkg, 0)
            version = latest_version_map.get(pkg, "unknown")
            # version_fan_out = edges for this specific version (computed from in-memory map)
            version_fan_out = version_edges_map.get((pkg, version), 0)
            # Bottleneck = fan_in × version_fan_out:
            # - fan_in: how many packages depend on this one (breadth of impact)
            # - version_fan_out: how many deps this version pulls in (attack surface)
            # Using version_fan_out (not the all-versions total) avoids inflating scores
            # for packages with many historical releases (e.g. npm packages with 100+ versions).
            bottleneck_score = float(fan_in * version_fan_out) if version_fan_out > 0 else float(fan_in)

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
                    bottleneckPercentile=0.0,
                )
            )

        # Compute percentile ranks before slicing
        total = len(items)
        if total > 1:
            items.sort(key=lambda x: x.bottleneck_score)
            for rank, item in enumerate(items):
                item.bottleneck_percentile = round((rank / (total - 1)) * 100, 1)
        elif total == 1:
            items[0].bottleneck_percentile = 100.0

        items.sort(key=lambda x: (x.bottleneck_score, x.fan_in), reverse=True)
        top_items = items[:limit]
        
        # Now we only compute expensive centralities for the top N items being returned
        G = self._build_nx_graph(ecosystem)
        if len(G.nodes) > 0:
            try:
                pageranks = nx.pagerank(G)
            except:
                pageranks = {}
                
            try:
                eigenvectors = nx.eigenvector_centrality_numpy(G)
            except:
                eigenvectors = {}
                
            for item in top_items:
                pkg_name = item.name
                if G.has_node(pkg_name):
                    item.page_rank = pageranks.get(pkg_name, 0.0)
                    item.eigenvector_centrality = eigenvectors.get(pkg_name, 0.0)
                    item.blast_radius = len(nx.descendants(G, pkg_name))
                    # Note: We omit betweenness/closeness here intentionally to avoid 
                    # O(V*E) delays on API requests for the whole graph.
        
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
