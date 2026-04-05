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
        libyears = 0.0
        diamond_count = 0
        transitive_depth = 0
        
        if G.has_node(package_name):
            try:
                pagerank = nx.pagerank(G).get(package_name, 0.0)
            except:
                pass
            
            # Calculate blast radius
            blast_radius = len(nx.descendants(G, package_name))
            
            # Safely compute eigenvector on the largest connected component of the undirected graph
            try:
                if len(G) > 0:
                    udG = G.to_undirected()
                    largest_cc = max(nx.connected_components(udG), key=len)
                    if package_name in largest_cc:
                        subG = udG.subgraph(largest_cc)
                        eigenvector = nx.eigenvector_centrality_numpy(subG).get(package_name, 0.0)
            except Exception:
                pass
                
        # Tier 2 Metrics (Libyears, Diamonds, Transitive Depth)
        try:
                # Setup dates and versions for libyears
                all_versions = self.storage.get_all_versions(ecosystem)
                from collections import defaultdict
                versions_by_pkg = defaultdict(list)
                for v in all_versions:
                    versions_by_pkg[v.package_name].append(v)
                
                latest_date_by_pkg = {}
                latest_version_by_pkg = {}
                for pkg, vlist in versions_by_pkg.items():
                    valid_versions = [v for v in vlist if v.published_at]
                    if valid_versions:
                        latest_v = max(valid_versions, key=lambda x: x.published_at)
                        latest_date_by_pkg[pkg] = latest_v.published_at
                        latest_version_by_pkg[pkg] = latest_v.version
                    elif vlist:
                        latest_version_by_pkg[pkg] = vlist[-1].version
                        
                date_by_vid = {f"{v.package_name}@{v.version}": v.published_at for v in all_versions if v.published_at}
                
                # Build version-aware directed graph to trace exact resolved dependencies
                # We extract the base numerical constraint string to bind the correct baseline date for tech lag!
                import re
                VG = nx.DiGraph()
                for edge in all_edges:
                    base_ver = edge.resolved_target_version
                    if not base_ver and edge.version_constraint:
                        # Strip ^ ~ >= < markers to pinpoint the developer's exact pinned "developed against" threshold
                        match = re.search(r"(\d+\.\d+(?:\.\d+)?)", edge.version_constraint)
                        if match:
                            base_ver = match.group(1)
                    
                    if not base_ver:
                        base_ver = latest_version_by_pkg.get(edge.target_package, "unknown")
                        
                    VG.add_edge(f"{edge.source_package}@{edge.source_version}", f"{edge.target_package}@{base_ver}")
            
                root_id = f"{package_name}@{version}"
                if VG.has_node(root_id):
                    descendants_v = nx.descendants(VG, root_id)
                    
                    # Transitive Depth
                    try:
                        sub_VG = VG.subgraph(descendants_v | {root_id})
                        transitive_depth = nx.dag_longest_path_length(sub_VG)
                    except Exception:
                        transitive_depth = 0
                
                # Compute diamonds and libyears
                seen_pkgs = defaultdict(set)
                for tgt_id in descendants_v:
                    if "@" not in tgt_id: continue
                    pkg_only, ver_only = tgt_id.rsplit("@", 1)
                    seen_pkgs[pkg_only].add(ver_only)
                    
                    latest_date = latest_date_by_pkg.get(pkg_only)
                    used_date = date_by_vid.get(tgt_id)
                    
                    if not used_date and pkg_only in versions_by_pkg:
                        # Fuzzy match if constraint lacked patch version (e.g. "tough-cookie@2.4")
                        for v in versions_by_pkg[pkg_only]:
                            if v.version.startswith(ver_only) and v.published_at:
                                used_date = v.published_at
                                break
                    
                    if used_date and latest_date and latest_date > used_date:
                        delta = (latest_date - used_date).days / 365.25
                        libyears += delta
                
                # A diamond conflict is a transitive package required in multiple distinct versions
                diamond_count = sum(1 for versions_set in seen_pkgs.values() if len(versions_set) > 1)
                
        except Exception as e:
            import logging
            logging.error(f"Tier 2 Metrics Calculation Failed: {e}")

        return PackageMetrics(
            directDependencies=fan_out,
            transitiveDependencies=0,
            fanIn=fan_in,
            fanOut=fan_out,
            bottleneckScore=bottleneck_score,
            diamondCount=diamond_count,
            pageRank=pagerank,
            closenessCentrality=closeness,
            betweennessCentrality=betweenness,
            eigenvectorCentrality=eigenvector,
            blastRadius=blast_radius,
            libyears=round(libyears, 2),
            transitiveDepth=transitive_depth
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
                if len(G) > 0:
                    udG = G.to_undirected()
                    largest_cc = max(nx.connected_components(udG), key=len)
                    subG = udG.subgraph(largest_cc)
                    eigenvectors = nx.eigenvector_centrality_numpy(subG)
                else:
                    eigenvectors = {}
            except Exception:
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

    def get_transitive_depths(self, ecosystem: str, package_name: str, version: str) -> Dict[str, int]:
        """
        Computes the shortest path depth from the root node to all reachable dependencies.
        Returns a dictionary mapping node IDs (e.g. 'pkg@1.0') to integer depths (0 = root, 1 = direct, 2+ = transitive).
        """
        all_edges = self.storage.get_all_edges(ecosystem)
        all_versions = self.storage.get_all_versions(ecosystem)
        
        latest_version_by_pkg = {}
        for v in all_versions:
            latest_version_by_pkg[v.package_name] = v.version

        import re
        VG = nx.DiGraph()
        for edge in all_edges:
            base_ver = edge.resolved_target_version
            if not base_ver and edge.version_constraint:
                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", edge.version_constraint)
                if match:
                    base_ver = match.group(1)
            
            if not base_ver:
                base_ver = latest_version_by_pkg.get(edge.target_package, "unknown")
                
            VG.add_edge(f"{edge.source_package}@{edge.source_version}", f"{edge.target_package}@{base_ver}")
            
        root_id = f"{package_name}@{version}"
        VG.add_node(root_id)
        depths = nx.single_source_shortest_path_length(VG, root_id)
            
        return depths

    def get_libyears_breakdown(self, ecosystem: str, package_name: str, version: str) -> Dict[str, float]:
        """
        Computes the libyears debt introduced by each transitive dependency.
        Returns a dictionary mapping node IDs (e.g. 'pkg@ver') to libyears debt (float).
        """
        all_edges = self.storage.get_all_edges(ecosystem)
        all_versions = self.storage.get_all_versions(ecosystem)
        
        from collections import defaultdict
        import re
        
        versions_by_pkg = defaultdict(list)
        for v in all_versions:
            versions_by_pkg[v.package_name].append(v)
            
        latest_date_by_pkg = {}
        latest_version_by_pkg = {}
        for pkg, vlist in versions_by_pkg.items():
            valid_versions = [v for v in vlist if v.published_at]
            if valid_versions:
                latest_v = max(valid_versions, key=lambda x: x.published_at)
                latest_date_by_pkg[pkg] = latest_v.published_at
                latest_version_by_pkg[pkg] = latest_v.version
            elif vlist:
                latest_version_by_pkg[pkg] = vlist[-1].version
                
        date_by_vid = {f"{v.package_name}@{v.version}": v.published_at for v in all_versions if v.published_at}
        
        VG = nx.DiGraph()
        for edge in all_edges:
            base_ver = edge.resolved_target_version
            if not base_ver and edge.version_constraint:
                match = re.search(r"(\d+\.\d+(?:\.\d+)?)", edge.version_constraint)
                if match:
                    base_ver = match.group(1)
            
            if not base_ver:
                base_ver = latest_version_by_pkg.get(edge.target_package, "unknown")
                
            VG.add_edge(f"{edge.source_package}@{edge.source_version}", f"{edge.target_package}@{base_ver}")
            
        root_id = f"{package_name}@{version}"
        libyears_breakdown = {}
        
        if VG.has_node(root_id):
            descendants_v = nx.descendants(VG, root_id)
            
            for tgt_id in descendants_v:
                if "@" not in tgt_id: continue
                pkg_only, ver_only = tgt_id.rsplit("@", 1)
                
                latest_date = latest_date_by_pkg.get(pkg_only)
                used_date = date_by_vid.get(tgt_id)
                
                if not used_date and pkg_only in versions_by_pkg:
                    for v in versions_by_pkg[pkg_only]:
                        if v.version.startswith(ver_only) and v.published_at:
                            used_date = v.published_at
                            break
                            
                if used_date and latest_date:
                    delta = (latest_date - used_date).days / 365.25
                    if delta > 0:
                        libyears_breakdown[tgt_id] = round(delta, 2)
                    else:
                        libyears_breakdown[tgt_id] = 0.0
                    
        return libyears_breakdown
