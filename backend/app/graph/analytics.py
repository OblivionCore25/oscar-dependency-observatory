"""
OSCAR Dependency Graph Observatory — Analytics Service

Computes central metrics on the graph structure using flat files.
"""

from typing import List, Dict, Optional
from collections import defaultdict

from app.storage import StorageService
from app.models.api import PackageMetrics, TopRiskItem, TopRiskResponse
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
        # Fan-out (direct dependencies)
        direct_edges = self.storage.get_edges_for_version(ecosystem, package_name, version)
        fan_out = len(direct_edges)
        
        # Fan-in (how many packages depend on this package)
        # Note: In MVP file storage, this requires scanning all edges.
        # This is expensive locally but sufficient for the MVP.
        all_edges = self.storage.get_all_edges(ecosystem)
        
        # Look for instances where `target_package` exactly matches this package name.
        # We don't resolve semver constraints here for fan_in MVP, just package references.
        dependent_packages = set()
        for edge in all_edges:
            if edge.target_package == package_name:
                dependent_packages.add(edge.source_package)
                
        fan_in = len(dependent_packages)
        
        # Bottleneck score = fan_in * fan_out (e.g. high centrality)
        bottleneck_score = float(fan_in * fan_out)
        
        return PackageMetrics(
            directDependencies=fan_out,
            transitiveDependencies=0, # Optional extra traversal
            fanIn=fan_in,
            fanOut=fan_out,
            bottleneckScore=bottleneck_score,
            diamondCount=0
        )

    async def get_top_risk(self, ecosystem: str, limit: int = 10) -> TopRiskResponse:
        """
        Retrieves the most depended-upon packages globally in our storage database.
        """
        all_edges = self.storage.get_all_edges(ecosystem)
        
        # fan_in counts per package
        fan_in_map: Dict[str, int] = defaultdict(int)
        
        # track all known versions to return in the list
        all_pkgs_map: Dict[str, str] = {}
        for edge in all_edges:
            # We count unique sources per target to avoid inflating fan-in via multi-versions
            # But simpler MVP: just sum up references
            fan_in_map[edge.target_package] += 1
            all_pkgs_map[edge.source_package] = edge.source_version
            # target versions might not be natively recorded unless we ingest them
            
        # Get actual versions for target packages from storage if available
        all_versions = self.storage.get_all_versions(ecosystem)
        latest_versions = {}
        for v in all_versions:
            # simple override gets us latest mapped chronologically
            latest_versions[v.package_name] = v.version
            
        items = []
        for pkg, fan_in in fan_in_map.items():
            version = latest_versions.get(pkg, "unknown")
            items.append(
                TopRiskItem(
                    id=f"{ecosystem}:{pkg}@{version}",
                    ecosystem=ecosystem,
                    name=pkg,
                    version=version,
                    fanIn=fan_in,
                    fanOut=0, # Would require a huge join for the whole list MVP. 
                    bottleneckScore=float(fan_in) # Simple proxy for top-risk sort
                )
            )
            
        # Sort desc by fan_in
        items.sort(key=lambda x: x.fan_in, reverse=True)
        top_items = items[:limit]
        
        return TopRiskResponse(items=top_items)
