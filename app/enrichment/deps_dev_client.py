"""
OSCAR — deps.dev (Google Open Source Insights) Client

Wraps the deps.dev v3/v3alpha API for:
  - Dependent counts (true ecosystem-wide fan-in)
  - Package metadata (source repo URL, licenses, advisories)

API docs: https://docs.deps.dev
"""

import logging
from typing import Optional
from urllib.parse import quote

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)

# Ecosystem name mapping: OSCAR → deps.dev system identifiers
ECOSYSTEM_MAP = {
    "npm": "NPM",
    "pypi": "PYPI",
    "maven": "MAVEN",
    "cargo": "CARGO",
    "go": "GO",
}

DEPS_DEV_BASE = "https://api.deps.dev"


class DependentsData:
    """Parsed response from the :dependents endpoint."""

    def __init__(self, total: int, direct: int, indirect: int):
        self.total = total
        self.direct = direct
        self.indirect = indirect

    def __repr__(self) -> str:
        return f"DependentsData(total={self.total}, direct={self.direct}, indirect={self.indirect})"


class PackageInfoData:
    """Parsed response from the package version endpoint."""

    def __init__(
        self,
        source_repo_url: Optional[str] = None,
        licenses: Optional[list[str]] = None,
        published_at: Optional[str] = None,
        is_deprecated: bool = False,
    ):
        self.source_repo_url = source_repo_url
        self.licenses = licenses or []
        self.published_at = published_at
        self.is_deprecated = is_deprecated


class DepsDevClient:
    """
    Async HTTP client for the Google deps.dev API.
    All responses are TTL-cached in memory to minimize redundant external calls.
    """

    def __init__(self, cache_ttl: int = 3600, cache_maxsize: int = 2000):
        self._dependents_cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._info_cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._timeout = httpx.Timeout(10.0, connect=5.0)

    def _encode_package(self, package_name: str) -> str:
        """URL-encode package name for deps.dev path segments."""
        return quote(package_name, safe="")

    def _get_system(self, ecosystem: str) -> Optional[str]:
        """Map OSCAR ecosystem to deps.dev system identifier."""
        return ECOSYSTEM_MAP.get(ecosystem.lower())

    async def _resolve_latest_version(self, system: str, package_name: str) -> Optional[str]:
        encoded_pkg = self._encode_package(package_name)
        url = f"{DEPS_DEV_BASE}/v3/systems/{system}/packages/{encoded_pkg}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                for version in data.get("versions", []):
                    if version.get("isDefault"):
                        return version.get("versionKey", {}).get("version")
                # Fallback to last version if no default is marked
                if data.get("versions"):
                    return data["versions"][-1].get("versionKey", {}).get("version")
        except Exception as e:
            logger.warning(f"deps.dev failed to resolve latest version for {system}/{package_name}: {e}")
        return None

    async def get_dependents(
        self, ecosystem: str, package_name: str, version: str
    ) -> Optional[DependentsData]:
        """
        Fetch dependent counts from the v3alpha :dependents endpoint.
        Returns None on failure (graceful degradation).
        """
        system = self._get_system(ecosystem)
        if not system:
            return None

        if version == "latest" or not version:
            resolved = await self._resolve_latest_version(system, package_name)
            if not resolved:
                return None
            version = resolved

        cache_key = f"{ecosystem}:{package_name}:{version}:dependents"
        if cache_key in self._dependents_cache:
            return self._dependents_cache[cache_key]

        encoded_pkg = self._encode_package(package_name)
        encoded_ver = self._encode_package(version)
        url = f"{DEPS_DEV_BASE}/v3alpha/systems/{system}/packages/{encoded_pkg}/versions/{encoded_ver}:dependents"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                result = DependentsData(
                    total=data.get("dependentCount", 0),
                    direct=data.get("directDependentCount", 0),
                    indirect=data.get("indirectDependentCount", 0),
                )
                self._dependents_cache[cache_key] = result
                return result

        except Exception as e:
            logger.warning(f"deps.dev dependents call failed for {ecosystem}/{package_name}@{version}: {e}")
            return None

    async def get_package_info(
        self, ecosystem: str, package_name: str, version: str
    ) -> Optional[PackageInfoData]:
        """
        Fetch package version metadata from the v3 API.
        Extracts source repo URL, licenses, and publish date.
        """
        system = self._get_system(ecosystem)
        if not system:
            return None

        original_version = version

        if version == "latest" or not version:
            resolved = await self._resolve_latest_version(system, package_name)
            if not resolved:
                return None
            version = resolved

        cache_key = f"{ecosystem}:{package_name}:{version}:info"
        if cache_key in self._info_cache:
            return self._info_cache[cache_key]

        encoded_pkg = self._encode_package(package_name)
        encoded_ver = self._encode_package(version)
        url = f"{DEPS_DEV_BASE}/v3/systems/{system}/packages/{encoded_pkg}/versions/{encoded_ver}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()

                # Extract source repo URL from links
                source_repo_url = None
                for link in data.get("links", []):
                    if link.get("label") == "SOURCE_REPO":
                        source_repo_url = link.get("url", "")
                        # Normalize: strip git+ prefix (git+https://, git+ssh://)
                        if source_repo_url.startswith("git+"):
                            source_repo_url = source_repo_url[4:]
                        # Normalize: remove trailing .git
                        if source_repo_url.endswith(".git"):
                            source_repo_url = source_repo_url[:-4]
                        # Normalize: convert ssh:// to https://
                        if source_repo_url.startswith("ssh://"):
                            source_repo_url = source_repo_url.replace("ssh://", "https://", 1)
                        break

                # Fallback: if we didn't find the source repo in this old version,
                # often older versions of PyPI/NPM packages lack the metadata.
                # Re-query the 'latest' version to pull the repository URL.
                if not source_repo_url and original_version != "latest":
                    latest_info = await self.get_package_info(ecosystem, package_name, "latest")
                    if latest_info and latest_info.source_repo_url:
                        source_repo_url = latest_info.source_repo_url

                result = PackageInfoData(
                    source_repo_url=source_repo_url,
                    licenses=data.get("licenses", []),
                    published_at=data.get("publishedAt"),
                    is_deprecated=data.get("isDeprecated", False),
                )
                self._info_cache[cache_key] = result
                return result

        except Exception as e:
            logger.warning(f"deps.dev info call failed for {ecosystem}/{package_name}@{version}: {e}")
            return None
