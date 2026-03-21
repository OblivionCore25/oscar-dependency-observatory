"""
OSCAR Dependency Graph Observatory — npm Registry Connector

Responsible for fetching package data from the public npm registry.
"""

import httpx
from typing import Optional, Dict, Any

class PackageNotFoundError(Exception):
    """Raised when a package is not found in the registry."""
    pass

class RegistryConnectionError(Exception):
    """Raised when the registry cannot be reached or returns an unexpected error."""
    pass

class NpmConnector:
    """
    Connector for the public npm registry (https://registry.npmjs.org/).
    Provides methods to fetch package metadata.
    """

    DEFAULT_BASE_URL = "https://registry.npmjs.org"

    def __init__(self, base_url: str = DEFAULT_BASE_URL, client: Optional[httpx.AsyncClient] = None):
        self.base_url = base_url.rstrip("/")
        self._client = client
        self._owns_client = client is None

    async def get_client(self) -> httpx.AsyncClient:
        """Returns the httpx client, creating it if necessary."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=10.0)
        return self._client

    async def close(self):
        """Closes the underlying HTTP client if this instance owns it."""
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self):
        await self.get_client()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def fetch_package(self, package_name: str) -> Dict[str, Any]:
        """
        Fetches full package metadata from the npm registry.
        
        Args:
            package_name: Name of the npm package (e.g. 'react' or '@types/node')
            
        Returns:
            A dictionary containing the raw JSON response from the registry.
            
        Raises:
            PackageNotFoundError: If the registry returns a 404.
            RegistryConnectionError: If network fails or registry returns other errors.
        """
        # Note: Scoped packages need their slashes URL-encoded for certain generic registries, but
        # the official registry.npmjs.org handles `@scope/pkg` directly in the path if properly encoded.
        # Actually, `httpx` will URL-encode the path component if we use it properly, but to be sure,
        # we can use urllib.parse.quote.
        from urllib.parse import quote
        safe_package_name = quote(package_name, safe='@/')
        url = f"{self.base_url}/{safe_package_name}"
        
        client = await self.get_client()
        try:
            response = await client.get(url)
        except httpx.RequestError as e:
            raise RegistryConnectionError(f"Failed to request {url}: {e}") from e
            
        if response.status_code == 404:
            raise PackageNotFoundError(f"Package '{package_name}' not found on npm registry.")
        elif response.status_code != 200:
            raise RegistryConnectionError(
                f"Registry returned status {response.status_code} for '{package_name}'"
            )
            
        try:
            return response.json()
        except Exception as e:
            raise RegistryConnectionError(f"Failed to parse registry response as JSON: {e}") from e
