"""
OSCAR — Package Download Statistics Client

Fetches monthly download counts from npm and PyPI registry APIs.
Extensible to other ecosystems via the strategy pattern.

npm:  https://api.npmjs.org/downloads/point/last-month/{package}
PyPI: https://pypistats.org/api/packages/{package}/recent
"""

import logging
from typing import Optional

import httpx
from cachetools import TTLCache

logger = logging.getLogger(__name__)


class DownloadStatsClient:
    """
    Async HTTP client for registry download statistics.
    Results are TTL-cached for 24 hours (download stats are daily).
    """

    def __init__(self, cache_ttl: int = 86400, cache_maxsize: int = 2000):
        self._cache: TTLCache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)
        self._timeout = httpx.Timeout(10.0, connect=5.0)

    async def get_downloads(self, ecosystem: str, package_name: str) -> Optional[int]:
        """
        Fetch monthly download count for a package.
        Returns None on failure (graceful degradation).
        """
        cache_key = f"{ecosystem}:{package_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        eco = ecosystem.lower()
        result = None

        if eco == "npm":
            result = await self._fetch_npm(package_name)
        elif eco == "pypi":
            result = await self._fetch_pypi(package_name)
        else:
            logger.debug(f"Download stats not supported for ecosystem: {ecosystem}")
            return None

        if result is not None:
            self._cache[cache_key] = result

        return result

    async def _fetch_npm(self, package_name: str) -> Optional[int]:
        """Fetch last-month downloads from the npm registry API."""
        # npm API uses the raw package name (scoped packages work as-is)
        url = f"https://api.npmjs.org/downloads/point/last-month/{package_name}"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                return data.get("downloads", 0)

        except Exception as e:
            logger.warning(f"npm download stats failed for {package_name}: {e}")
            return None

    async def _fetch_pypi(self, package_name: str) -> Optional[int]:
        """Fetch recent downloads from pypistats.org."""
        # pypistats uses lowercase normalized names
        normalized = package_name.lower().replace("-", "-")
        url = f"https://pypistats.org/api/packages/{normalized}/recent"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
                # pypistats returns {"data": {"last_month": N, "last_week": N, "last_day": N}}
                recent = data.get("data", {})
                return recent.get("last_month", 0)

        except Exception as e:
            logger.warning(f"PyPI download stats failed for {package_name}: {e}")
            return None
