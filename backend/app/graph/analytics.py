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
        
        return PackageMetrics(
            directDependencies=fan_out,
            transitiveDependencies=0,
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
        
        # fan_in: unique SOURCE PACKAGE NAMES that depend on a target (deduplicated across versions)
        fan_in_map: Dict[str, set] = defaultdict(set)
        # fan_out: number of dependencies each package declares (edge count across versions)
        fan_out_map: Dict[str, int] = defaultdict(int)
        
        all_pkgs_map: Dict[str, str] = {}
        for edge in all_edges:
            fan_in_map[edge.target_package].add(edge.source_package)  # set dedup: react@18.0+18.1 = 1 unique dependent
            fan_out_map[edge.source_package] += 1
            all_pkgs_map[edge.source_package] = edge.source_version
            
        # Get actual versions for target packages from storage if available
        all_versions = self.storage.get_all_versions(ecosystem)
        latest_versions = {}
        for v in all_versions:
            # simple override gets us latest mapped chronologically
            latest_versions[v.package_name] = v.version
            
        # Union of all known packages (appear either as source or target)
        all_known_packages = set(fan_in_map.keys()) | set(fan_out_map.keys())
            
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
                    bottleneckScore=bottleneck_score
                )
            )
            
        # Sort desc by bottleneck score (fan_in × fan_out), then fan_in as tie-breaker
        items.sort(key=lambda x: (x.bottleneck_score, x.fan_in), reverse=True)
        top_items = items[:limit]
        
        return TopRiskResponse(items=top_items)

