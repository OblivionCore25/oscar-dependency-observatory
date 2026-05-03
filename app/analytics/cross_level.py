"""
OSCAR — Cross-Level Risk Propagation Analyzer

The crown jewel: orchestrates both the Dependency Observatory and the Method
Observatory to produce a unified risk ranking across the entire supply chain.

Architecture:
    Dependency Observatory (:8000)  →  transitive graph + enrichment
    Method Observatory     (:8001)  →  method hotspots + auto-ingest
    This module (orchestrator)      →  computes cross-level risk formula

Formula:
    Cross-Level Risk = Method_Composite_Risk × log₁₀(Ecosystem_Fan_In + 1)
"""

import asyncio
import logging
import math
from typing import Optional

import httpx

from app.models.cross_level import (
    CrossLevelMethodRisk,
    CrossLevelReport,
    AnalyzedDependency,
)
from app.enrichment.deps_dev_client import DepsDevClient

logger = logging.getLogger(__name__)

# Method Observatory base URL — runs as a sibling service
METHOD_OBSERVATORY_URL = "http://127.0.0.1:8001"


class CrossLevelAnalyzer:
    """
    Orchestrates cross-level risk analysis by:
    1. Resolving the transitive dependency graph
    2. Ranking deps by local bottleneck score
    3. For each top-N dep, fetching method-level hotspots
    4. Computing cross-level risk per method
    5. Returning a unified ranking
    """

    def __init__(self):
        self.deps_dev = DepsDevClient()
        self._http_timeout = httpx.Timeout(45.0, connect=10.0)

    async def analyze(
        self,
        ecosystem: str,
        package_name: str,
        version: str,
        top_n: int = 5,
    ) -> CrossLevelReport:
        """
        Main entry point. Performs cross-level risk analysis for the top-N
        most structurally important transitive dependencies.
        """

        # ── Step 1: Resolve transitive dependency graph ──────────────────
        graph_nodes, graph_edges = await self._resolve_transitive_graph(
            ecosystem, package_name, version
        )
        if not graph_nodes:
            return self._empty_report(ecosystem, package_name, version)

        total_deps = len(graph_nodes) - 1  # exclude root

        # ── Step 2: Compute local bottleneck scores and rank ─────────────
        dep_rankings = self._rank_deps_by_bottleneck(
            graph_nodes, graph_edges, ecosystem, package_name, version
        )

        # Select top-N by bottleneck (or all if fewer)
        selected_deps = dep_rankings[:top_n]

        # ── Step 3: Concurrently analyze each selected dependency ────────
        sem = asyncio.Semaphore(3)  # limit concurrent method observatory calls
        tasks = [
            self._analyze_single_dep(sem, dep, ecosystem)
            for dep in selected_deps
        ]
        dep_results = await asyncio.gather(*tasks, return_exceptions=True)

        # ── Step 4: Flatten all methods, compute cross-level risk, rank ──
        all_method_risks: list[CrossLevelMethodRisk] = []
        analyzed_deps_info: list[AnalyzedDependency] = []

        for dep, result in zip(selected_deps, dep_results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to analyze {dep['package']}: {result}")
                analyzed_deps_info.append(
                    AnalyzedDependency(
                        package=dep["package"],
                        version=dep["version"],
                        ecosystem=ecosystem,
                        method_count=0,
                        ecosystem_fan_in=dep.get("fan_in_global", 0),
                        bottleneck_score=dep["bottleneck_score"],
                        analysis_cached=False,
                    )
                )
                continue

            methods, dep_info = result
            all_method_risks.extend(methods)
            analyzed_deps_info.append(dep_info)

        # Sort by cross-level risk descending
        all_method_risks.sort(key=lambda m: m.cross_level_risk, reverse=True)

        return CrossLevelReport(
            root_package=package_name,
            root_version=version,
            root_ecosystem=ecosystem,
            analyzed_deps=len(analyzed_deps_info),
            total_deps=total_deps,
            top_risks=all_method_risks[:50],  # cap output
            analyzed_dependencies=analyzed_deps_info,
            analysis_coverage_pct=round(
                len(analyzed_deps_info) / max(total_deps, 1) * 100, 1
            ),
        )

    # ── Private helpers ──────────────────────────────────────────────────────

    async def _resolve_transitive_graph(
        self, ecosystem: str, package_name: str, version: str
    ) -> tuple[list[dict], list[dict]]:
        """Stream the transitive graph from the dependency observatory."""
        from app.storage.factory import get_storage
        from app.graph.direct import DirectDependencyService
        from app.graph.transitive import TransitiveDependencyService

        storage = get_storage()
        direct_service = DirectDependencyService(storage)
        transitive_service = TransitiveDependencyService(direct_service)

        nodes = []
        edges = []
        try:
            async for event in transitive_service.stream_transitive_graph(
                ecosystem, package_name, version
            ):
                if event.get("type") == "complete":
                    data = event.get("data", {})
                    nodes = data.get("nodes", [])
                    edges = data.get("edges", [])
        except Exception as e:
            logger.error(f"Transitive graph resolution failed: {e}")

        return nodes, edges

    def _rank_deps_by_bottleneck(
        self,
        nodes: list[dict],
        edges: list[dict],
        ecosystem: str,
        root_package: str,
        root_version: str,
    ) -> list[dict]:
        """
        Compute a local bottleneck score for each dep in the graph using
        fan-in × fan-out within the transitive tree.
        """
        # Build adjacency from edges
        fan_in = {}
        fan_out = {}

        for edge in edges:
            src = edge.get("source", "")
            tgt = edge.get("target", "")
            fan_out[src] = fan_out.get(src, 0) + 1
            fan_in[tgt] = fan_in.get(tgt, 0) + 1

        deps = []
        root_id = f"{ecosystem}:{root_package}@{root_version}"

        for node in nodes:
            node_id = node.get("id", "")
            if node_id == root_id:
                continue  # skip root

            fi = fan_in.get(node_id, 0)
            fo = fan_out.get(node_id, 0)
            bottleneck = fi * fo

            deps.append({
                "id": node_id,
                "package": node.get("package", ""),
                "version": node.get("version", ""),
                "ecosystem": node.get("ecosystem", ecosystem),
                "fan_in_local": fi,
                "fan_out_local": fo,
                "bottleneck_score": bottleneck,
            })

        # Sort by bottleneck descending, then by fan_out descending as tiebreaker
        deps.sort(key=lambda d: (d["bottleneck_score"], d["fan_out_local"]), reverse=True)
        return deps

    async def _analyze_single_dep(
        self,
        sem: asyncio.Semaphore,
        dep: dict,
        ecosystem: str,
    ) -> tuple[list[CrossLevelMethodRisk], AnalyzedDependency]:
        """
        For a single dependency:
        1. Ensure it's ingested in the method observatory
        2. Fetch its method hotspots
        3. Fetch ecosystem fan-in from deps.dev
        4. Compute cross-level risk per method
        """
        async with sem:
            pkg = dep["package"]
            ver = dep["version"]
            eco = dep.get("ecosystem", ecosystem)

            # Normalize slug the same way the method observatory does
            slug = pkg.replace("@", "").replace("/", "__")
            if eco.lower() == "pypi":
                slug = slug.lower()

            # ── 1. Check cache / trigger ingest ──────────────────────────
            analysis_cached = True
            async with httpx.AsyncClient(timeout=self._http_timeout) as client:
                # Check if project exists
                meta_resp = await client.get(
                    f"{METHOD_OBSERVATORY_URL}/methods/{slug}"
                )
                if meta_resp.status_code == 404:
                    # Not cached — trigger auto-ingest
                    analysis_cached = False
                    logger.info(f"Ingesting {eco}/{pkg} into method observatory...")
                    ingest_resp = await client.post(
                        f"{METHOD_OBSERVATORY_URL}/methods/ingest/{eco}/{pkg}",
                        params={"version": ver} if eco.lower() == "pypi" else {},
                    )
                    if ingest_resp.status_code != 200:
                        logger.warning(
                            f"Ingest failed for {pkg}: {ingest_resp.status_code}"
                        )
                        return [], AnalyzedDependency(
                            package=pkg, version=ver, ecosystem=eco,
                            method_count=0,
                            ecosystem_fan_in=0,
                            bottleneck_score=dep["bottleneck_score"],
                            analysis_cached=False,
                        )

                # ── 2. Fetch hotspots ────────────────────────────────────
                hotspots_resp = await client.get(
                    f"{METHOD_OBSERVATORY_URL}/methods/{slug}/hotspots",
                    params={"limit": 20},
                )
                if hotspots_resp.status_code != 200:
                    logger.warning(f"Hotspots failed for {slug}: {hotspots_resp.status_code}")
                    return [], AnalyzedDependency(
                        package=pkg, version=ver, ecosystem=eco,
                        method_count=0,
                        ecosystem_fan_in=0,
                        bottleneck_score=dep["bottleneck_score"],
                        analysis_cached=analysis_cached,
                    )

                hotspots = hotspots_resp.json()

            # ── 3. Fetch ecosystem fan-in from deps.dev ──────────────────
            dep_data = await self.deps_dev.get_dependents(eco, pkg, ver)
            ecosystem_fan_in = dep_data.total if dep_data else 0

            # ── 4. Compute cross-level risk per method ───────────────────
            methods: list[CrossLevelMethodRisk] = []
            for h in hotspots:
                method_node = h.get("method", {})
                metrics = h.get("metrics", {})
                composite = h.get("composite_risk", 0.0)

                cross_risk = composite * math.log10(ecosystem_fan_in + 1)

                methods.append(
                    CrossLevelMethodRisk(
                        method_name=method_node.get("name", "unknown"),
                        method_module=method_node.get("file_path", "unknown"),
                        method_qualified_name=method_node.get(
                            "qualified_name", method_node.get("name", "unknown")
                        ),
                        dependency_package=pkg,
                        dependency_version=ver,
                        dependency_ecosystem=eco,
                        complexity=metrics.get("complexity", 0),
                        method_blast_radius=metrics.get("blast_radius", 0),
                        method_centrality=metrics.get("betweenness_centrality", 0.0),
                        change_frequency=0,
                        method_composite_risk=composite,
                        ecosystem_fan_in=ecosystem_fan_in,
                        bottleneck_score=dep["bottleneck_score"],
                        cross_level_risk=round(cross_risk, 4),
                    )
                )

            top_method = methods[0] if methods else None
            dep_info = AnalyzedDependency(
                package=pkg,
                version=ver,
                ecosystem=eco,
                method_count=len(hotspots),
                top_method=top_method.method_qualified_name if top_method else None,
                top_method_risk=top_method.cross_level_risk if top_method else 0.0,
                ecosystem_fan_in=ecosystem_fan_in,
                bottleneck_score=dep["bottleneck_score"],
                analysis_cached=analysis_cached,
            )

            return methods, dep_info

    def _empty_report(
        self, ecosystem: str, package_name: str, version: str
    ) -> CrossLevelReport:
        return CrossLevelReport(
            root_package=package_name,
            root_version=version,
            root_ecosystem=ecosystem,
            analyzed_deps=0,
            total_deps=0,
            top_risks=[],
            analyzed_dependencies=[],
            analysis_coverage_pct=0.0,
        )
