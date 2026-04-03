"""
OSCAR Dependency Graph Observatory — PyPI Connector
"""

import httpx
from typing import Dict, Any, Optional

class PypiConnector:
    """
    Connects to the public PyPI API (pypi.org) to fetch package metadata.
    """
    BASE_URL = "https://pypi.org/pypi"

    def __init__(self):
        self.client = httpx.AsyncClient()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def fetch_package(self, package_name: str, version: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches the metadata payload from PyPI.
        If version is omitted, retrieves the latest version data.
        """
        if version:
            url = f"{self.BASE_URL}/{package_name}/{version}/json"
        else:
            url = f"{self.BASE_URL}/{package_name}/json"

        response = await self.client.get(url)

        if response.status_code == 404:
            raise ValueError(f"Package '{package_name}' (version: {version}) not found on PyPI registry.")
        
        response.raise_for_status()
        return response.json()
