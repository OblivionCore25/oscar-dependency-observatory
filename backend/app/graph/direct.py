"""
OSCAR Dependency Graph Observatory — Direct Dependency Service

Provides logic for resolving the immediate (direct) dependencies
of a specific package version, auto-ingesting if necessary.
"""

from typing import List

from app.ingestion.npm import NpmConnector, PackageNotFoundError
from app.normalization.npm_normalizer import NpmNormalizer
from app.storage import StorageService
from app.models.api import DependencyItem

class DirectDependencyService:
    """
    Service for querying direct dependencies from storage,
    with an auto-ingestion fallback layer for the MVP.
    """

    def __init__(self, storage: StorageService):
        self.storage = storage

    async def get_direct_dependencies(self, ecosystem: str, package_name: str, version: str) -> List[DependencyItem]:
        """
        Returns the direct dependencies for a given package and version.
        If the package is not found in storage, it attempts to ingest it.
        """
        if ecosystem != "npm":
            raise ValueError(f"Ecosystem {ecosystem} is not currently supported.")

        # Check if we already have this package's versions in our storage.
        # If we do, we assume we have its edges.
        # This is a naive MVP check: if version exists, we don't re-ingest.
        versions = self.storage.get_versions(ecosystem, package_name)
        version_exists = any(v.version == version for v in versions)

        if not version_exists:
            # Auto-ingest fallback
            await self._ingest_npm_package(package_name)
            
            # Check again after ingestion
            versions = self.storage.get_versions(ecosystem, package_name)
            version_exists = any(v.version == version for v in versions)
            if not version_exists:
                # The package exists on npm, but the requested version does not.
                raise ValueError(f"Version {version} not found for package {package_name}")

        # Retrieve direct edges
        edges = self.storage.get_edges_for_version(ecosystem, package_name, version)
        
        # We might have successfully ingested the version, but it has 0 edges (no dependencies)
        # So we just map the edges we found
        results = []
        for edge in edges:
            results.append(DependencyItem(
                name=edge.target_package,
                constraint=edge.version_constraint
            ))
            
        return results

    async def _ingest_npm_package(self, package_name: str) -> None:
        """Fetches, normalizes, and saves an npm package to storage."""
        async with NpmConnector() as connector:
            raw_data = await connector.fetch_package(package_name)
            
        package, versions, edges = NpmNormalizer.normalize_package_data(raw_data)
        
        self.storage.save_package(package)
        self.storage.save_versions(versions)
        self.storage.save_edges(edges)
