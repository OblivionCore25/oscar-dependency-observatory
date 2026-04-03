"""
OSCAR Dependency Graph Observatory — API Response Schemas

Pydantic models defining the shape of all API responses.
These schemas serve as the contract between backend and frontend.

See: docs/backend-implementation-guide.md §8 "API Contracts"
"""

from typing import List, Optional

from pydantic import BaseModel, Field


# ─── Health ─────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    """Response for GET /health"""

    status: str = Field(
        default="ok",
        description="Health status of the application",
        examples=["ok"],
    )


# ─── Ingestion ──────────────────────────────────────────────────────

class IngestResponse(BaseModel):
    """Response for POST /ingest/{ecosystem}/{package}"""

    status: str = Field(
        ...,
        description="Ingestion status",
        examples=["accepted"],
    )
    ecosystem: str = Field(..., examples=["npm"])
    package: str = Field(..., examples=["react"])
    version: Optional[str] = Field(default=None, examples=["18.2.0"])


# ─── Dependencies ───────────────────────────────────────────────────

class DependencyItem(BaseModel):
    """A single direct dependency entry."""

    name: str = Field(..., description="Dependency package name", examples=["loose-envify"])
    constraint: str = Field(..., description="Version constraint", examples=["^1.1.0"])


class DirectDependenciesResponse(BaseModel):
    """Response for GET /dependencies/{ecosystem}/{package}/{version}"""

    package: str = Field(..., examples=["react"])
    version: str = Field(..., examples=["18.2.0"])
    ecosystem: str = Field(..., examples=["npm"])
    dependencies: List[DependencyItem] = Field(default_factory=list)


# ─── Transitive Dependencies (Graph) ───────────────────────────────

class GraphNode(BaseModel):
    """A node in the dependency graph."""

    id: str = Field(..., description="Normalized node ID", examples=["npm:react@18.2.0"])
    label: str = Field(..., description="Display label", examples=["react@18.2.0"])
    ecosystem: str = Field(..., examples=["npm"])
    package: str = Field(..., examples=["react"])
    version: str = Field(..., examples=["18.2.0"])


class GraphEdge(BaseModel):
    """A directed edge in the dependency graph."""

    source: str = Field(..., description="Source node ID", examples=["npm:react-dom@18.2.0"])
    target: str = Field(..., description="Target node ID", examples=["npm:react@18.2.0"])
    constraint: Optional[str] = Field(default=None, examples=["^18.2.0"])


class TransitiveDependenciesResponse(BaseModel):
    """Response for GET /dependencies/{ecosystem}/{package}/{version}/transitive"""

    root: str = Field(..., description="Root node ID", examples=["npm:react@18.2.0"])
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)


# ─── Package Details ────────────────────────────────────────────────

class PackageMetrics(BaseModel):
    """Computed metrics for a package version."""

    direct_dependencies: int = Field(default=0, alias="directDependencies")
    transitive_dependencies: int = Field(default=0, alias="transitiveDependencies")
    fan_in: int = Field(default=0, alias="fanIn")
    fan_out: int = Field(default=0, alias="fanOut")
    bottleneck_score: float = Field(default=0.0, alias="bottleneckScore")
    diamond_count: int = Field(default=0, alias="diamondCount")
    page_rank: float = Field(default=0.0, alias="pageRank")
    closeness_centrality: float = Field(default=0.0, alias="closenessCentrality")
    betweenness_centrality: float = Field(default=0.0, alias="betweennessCentrality")
    blast_radius: int = Field(default=0, alias="blastRadius")

    model_config = {"populate_by_name": True}


class PackageDetailsResponse(BaseModel):
    """Response for GET /packages/{ecosystem}/{package}/{version}"""

    id: str = Field(..., examples=["npm:react@18.2.0"])
    ecosystem: str = Field(..., examples=["npm"])
    name: str = Field(..., examples=["react"])
    version: str = Field(..., examples=["18.2.0"])
    metrics: PackageMetrics = Field(default_factory=PackageMetrics)


# ─── Ingested Packages ──────────────────────────────────────────────

class IngestedPackageItem(BaseModel):
    """A single ingested package entry (name + latest known version)."""

    ecosystem: str = Field(..., examples=["npm"])
    name: str = Field(..., examples=["react"])
    version: str = Field(..., examples=["18.2.0"])


class IngestedPackagesResponse(BaseModel):
    """Response for GET /packages?ecosystem=npm&q=react"""

    ecosystem: str = Field(..., examples=["npm"])
    packages: List[IngestedPackageItem] = Field(default_factory=list)
    total: int = Field(default=0, description="Total matches before pagination.")


# ─── Analytics ──────────────────────────────────────────────────────

class TopRiskItem(BaseModel):
    """A single entry in the top-risk ranking."""

    id: str = Field(..., examples=["npm:example@1.0.0"])
    ecosystem: str = Field(..., examples=["npm"])
    name: str = Field(..., examples=["example"])
    version: str = Field(..., examples=["1.0.0"])
    fan_in: int = Field(default=0, alias="fanIn")
    fan_out: int = Field(default=0, alias="fanOut")
    version_fan_out: int = Field(default=0, alias="versionFanOut")
    bottleneck_score: float = Field(default=0.0, alias="bottleneckScore")
    bottleneck_percentile: float = Field(
        default=0.0,
        alias="bottleneckPercentile",
        description="Percentile rank (0–100) of this package's bottleneck score within the ingested graph.",
    )
    page_rank: float = Field(default=0.0, alias="pageRank")
    closeness_centrality: float = Field(default=0.0, alias="closenessCentrality")
    betweenness_centrality: float = Field(default=0.0, alias="betweennessCentrality")
    blast_radius: int = Field(default=0, alias="blastRadius")

    model_config = {"populate_by_name": True}


class TopRiskResponse(BaseModel):
    """Response for GET /analytics/top-risk"""

    items: List[TopRiskItem] = Field(default_factory=list)
    total_packages: int = Field(
        default=0,
        alias="totalPackages",
        description="Total unique packages in the ingested graph for this ecosystem.",
    )

    model_config = {"populate_by_name": True}


# ─── Coverage ────────────────────────────────────────────────────────

class CoverageResponse(BaseModel):
    """Response for GET /analytics/coverage"""

    ecosystem: str = Field(..., examples=["npm"])
    ingested_packages: int = Field(
        ...,
        alias="ingestedPackages",
        description="Number of unique packages ingested into the local graph.",
    )
    estimated_total: int = Field(
        ...,
        alias="estimatedTotal",
        description="Approximate total packages published in this ecosystem (published figure).",
    )
    coverage_pct: float = Field(
        ...,
        alias="coveragePct",
        description="Percentage of the ecosystem covered by the ingested graph (0–100).",
    )

    model_config = {"populate_by_name": True}
