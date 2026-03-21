"""
OSCAR Dependency Graph Observatory — Domain Models

Core internal domain models representing the package dependency graph.
These models define the canonical data structures used throughout the
backend for ingestion, normalization, graph construction, and analytics.

See: docs/backend-implementation-guide.md §7 "Data Model (Minimum)"
"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class Package(BaseModel):
    """
    Represents a package within a software ecosystem.

    The combination of (ecosystem, name) uniquely identifies a package.
    """

    ecosystem: str = Field(
        ...,
        description="Package ecosystem, e.g. 'npm', 'pypi'",
        examples=["npm", "pypi"],
    )
    name: str = Field(
        ...,
        description="Package name within its ecosystem",
        examples=["react", "requests"],
    )

    @property
    def package_id(self) -> str:
        """Normalized package identifier: ecosystem:name"""
        return f"{self.ecosystem}:{self.name}"


class Version(BaseModel):
    """
    Represents a specific version of a package.

    The combination of (ecosystem, package_name, version) uniquely
    identifies a versioned package.
    """

    package_name: str = Field(
        ...,
        description="Name of the package",
        examples=["react"],
    )
    ecosystem: str = Field(
        ...,
        description="Package ecosystem",
        examples=["npm"],
    )
    version: str = Field(
        ...,
        description="Semantic version string",
        examples=["18.2.0"],
    )
    published_at: Optional[datetime] = Field(
        default=None,
        description="Publication timestamp, if available from registry",
    )

    @property
    def version_id(self) -> str:
        """Normalized version identifier: ecosystem:name@version"""
        return f"{self.ecosystem}:{self.package_name}@{self.version}"


class DependencyEdge(BaseModel):
    """
    Represents a directed dependency relationship between two packages.

    source → target means "source depends on target".
    """

    source_package: str = Field(
        ...,
        description="Name of the dependent package",
        examples=["react-dom"],
    )
    source_version: str = Field(
        ...,
        description="Version of the dependent package",
        examples=["18.2.0"],
    )
    target_package: str = Field(
        ...,
        description="Name of the dependency package",
        examples=["react"],
    )
    version_constraint: str = Field(
        ...,
        description="Version constraint as declared by the source",
        examples=["^18.2.0", ">=3.0,<4.0"],
    )
    resolved_target_version: Optional[str] = Field(
        default=None,
        description="Resolved concrete version of the target, if available",
        examples=["18.2.0"],
    )
    dependency_type: Optional[str] = Field(
        default="runtime",
        description="Type of dependency relationship",
        examples=["runtime", "dev", "peer", "optional"],
    )
    ecosystem: str = Field(
        ...,
        description="Ecosystem this edge belongs to",
        examples=["npm"],
    )
    ingestion_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this edge was ingested",
    )

    @property
    def edge_id(self) -> str:
        """Unique edge identifier."""
        return (
            f"{self.ecosystem}:{self.source_package}@{self.source_version}"
            f" -> {self.ecosystem}:{self.target_package}"
        )


class Snapshot(BaseModel):
    """
    Represents a point-in-time snapshot of the dependency graph.

    Snapshots enable reproducibility by capturing the graph state
    at a specific moment.
    """

    snapshot_id: str = Field(
        ...,
        description="Unique identifier for this snapshot",
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this snapshot was created",
    )
    ecosystem: str = Field(
        ...,
        description="Ecosystem this snapshot covers",
        examples=["npm"],
    )
    description: Optional[str] = Field(
        default=None,
        description="Human-readable description of the snapshot",
    )
