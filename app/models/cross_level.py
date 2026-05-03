"""
OSCAR — Cross-Level Risk Propagation Models

Bridges ecosystem-level dependency metrics with method-level internal
architecture metrics to produce a unified cross-level risk score.

Formula:
    Cross-Level Risk = Method_Composite_Risk × log₁₀(Ecosystem_Fan_In + 1)
"""

from typing import Optional
from pydantic import BaseModel


class CrossLevelMethodRisk(BaseModel):
    """A single method's risk synthesized across both observatories."""

    # Method identity
    method_name: str
    method_module: str
    method_qualified_name: str

    # Which dependency this method belongs to
    dependency_package: str
    dependency_version: str
    dependency_ecosystem: str

    # Method-level metrics (from Method Observatory)
    complexity: int
    method_blast_radius: int
    method_centrality: float
    change_frequency: int = 0
    method_composite_risk: float

    # Ecosystem-level metrics (from Dependency Observatory / deps.dev)
    ecosystem_fan_in: int
    bottleneck_score: float

    # Cross-level synthesis
    cross_level_risk: float


class AnalyzedDependency(BaseModel):
    """Summary of a dependency that was analyzed at the method level."""

    package: str
    version: str
    ecosystem: str
    method_count: int
    top_method: Optional[str] = None
    top_method_risk: float = 0.0
    ecosystem_fan_in: int = 0
    bottleneck_score: float = 0.0
    analysis_cached: bool = False


class CrossLevelReport(BaseModel):
    """Complete cross-level risk report for a package's supply chain."""

    root_package: str
    root_version: str
    root_ecosystem: str
    analyzed_deps: int
    total_deps: int
    top_risks: list[CrossLevelMethodRisk]
    analyzed_dependencies: list[AnalyzedDependency]
    analysis_coverage_pct: float  # analyzed_deps / total_deps × 100
