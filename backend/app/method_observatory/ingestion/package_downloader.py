import asyncio
import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path

import httpx

class PackageDownloader:
    """Service to automatically download and extract Python packages from PyPI."""

    def __init__(self, registry_url: str = "https://pypi.org/pypi"):
        self.registry_url = registry_url

    async def _get_package_info(self, package_name: str, version: str) -> dict:
        """Fetch package metadata from PyPI."""
        url = f"{self.registry_url}/{package_name}/{version}/json"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            if response.status_code == 404:
                raise ValueError(f"Package {package_name}=={version} not found on PyPI")
            response.raise_for_status()
            return response.json()

    def _find_source_distribution(self, releases: list[dict]) -> dict | None:
        """Find the source distribution (sdist) URL in the release info."""
        for release in releases:
            if release.get("packagetype") == "sdist":
                return release
        return None

    async def download_and_extract(self, package_name: str, version: str, extract_dir: Path) -> Path:
        """
        Download the source distribution for a package and extract it.
        Returns the path to the extracted source code directory.
        """
        info = await self._get_package_info(package_name, version)
        releases = info.get("urls", [])

        sdist_info = self._find_source_distribution(releases)
        if not sdist_info:
            raise ValueError(f"No source distribution found for {package_name}=={version}")

        url = sdist_info["url"]
        filename = sdist_info["filename"]

        # Download
        archive_path = extract_dir / filename
        async with httpx.AsyncClient(follow_redirects=True) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                with open(archive_path, "wb") as f:
                    async for chunk in response.aiter_bytes():
                        f.write(chunk)

        # Extract
        source_dir = extract_dir / f"{package_name}-{version}-src"
        source_dir.mkdir(parents=True, exist_ok=True)

        if filename.endswith(".tar.gz") or filename.endswith(".tgz"):
            with tarfile.open(archive_path, "r:gz") as tar:
                # Use data filter to prevent directory traversal attacks during extraction
                tar.extractall(path=source_dir, filter="data")
        elif filename.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(source_dir)
        else:
            raise ValueError(f"Unknown archive format for {filename}")

        # The extracted archive usually contains a single top-level directory
        # e.g. boto3-1.34.40.tar.gz extracts to boto3-1.34.40/
        extracted_dirs = [d for d in source_dir.iterdir() if d.is_dir()]
        if len(extracted_dirs) == 1:
             return extracted_dirs[0]

        return source_dir
