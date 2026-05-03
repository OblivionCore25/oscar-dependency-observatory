import asyncio
import logging
from typing import List, Optional
import math
from datetime import datetime

from app.models.temporal import TemporalDataPoint, TemporalReport
from app.ingestion.npm import NpmConnector, PackageNotFoundError as NpmNotFoundError
from app.ingestion.pypi import PypiConnector
from app.enrichment.deps_dev_client import DepsDevClient
from app.vulnerability.osv_client import query_batch_vulns

logger = logging.getLogger(__name__)

class TemporalAnalyzer:
    def __init__(self):
        self.deps_dev = DepsDevClient()
    
    async def _fetch_versions_and_dates(self, ecosystem: str, package_name: str) -> List[dict]:
        """
        Returns a list of dicts: {"version": "...", "published_at": "..."} sorted Old -> New
        """
        eco = ecosystem.lower()
        versions = []
        if eco == "npm":
            async with NpmConnector() as npm:
                data = await npm.fetch_package(package_name)
                # 'time' is a dict mapping version -> ISO date
                time_data = data.get("time", {})
                for v, dt in time_data.items():
                    # skip 'created' and 'modified' meta keys
                    if v in ("created", "modified"):
                        continue
                    # also skip versions not in 'versions' if we want strictly published
                    if v in data.get("versions", {}):
                        # Calculate direct deps from this specific version
                        v_data = data["versions"][v]
                        direct_deps = len(v_data.get("dependencies", {}))
                        
                        versions.append({
                            "version": v,
                            "published_at": dt,
                            "fan_out": direct_deps
                        })
        elif eco == "pypi":
            async with PypiConnector() as pypi:
                data = await pypi.fetch_package(package_name)
                releases = data.get("releases", {})
                for v, files in releases.items():
                    if files:
                        # take the first file's upload time
                        upload_time = files[0].get("upload_time_iso_8601") or files[0].get("upload_time")
                        # Fan-out will be resolved per-version during the enrichment phase
                        if upload_time:
                            versions.append({
                                "version": v,
                                "published_at": upload_time,
                                "fan_out": -1  # sentinel: resolve later
                            })
        
        # Sort by published string (ISO date format)
        versions.sort(key=lambda x: x.get("published_at", ""))
        return versions

    async def _resolve_pypi_fan_out(self, package_name: str, version: str) -> int:
        """Fetch requires_dist for a specific PyPI version."""
        try:
            async with PypiConnector() as pypi:
                data = await pypi.fetch_package(package_name, version)
                requires = data.get("info", {}).get("requires_dist") or []
                # Filter out extras-only deps (e.g. "argon2-cffi ; extra == 'argon2'")
                core_deps = [r for r in requires if "; extra ==" not in r]
                return len(core_deps)
        except Exception as e:
            logger.warning(f"Failed to fetch PyPI deps for {package_name}@{version}: {e}")
            return 0

    async def analyze_temporal(self, ecosystem: str, package_name: str, 
                               num_versions: int = 15) -> TemporalReport:
        versions_data = await self._fetch_versions_and_dates(ecosystem, package_name)
        total_available = len(versions_data)

        if total_available == 0:
            return TemporalReport(
                ecosystem=ecosystem,
                package_name=package_name,
                data_points=[],
                total_versions_available=0,
                sampled_versions=0
            )

        # Sample evenly spaced versions
        if total_available <= num_versions:
            sampled = versions_data
        else:
            step = (total_available - 1) / (num_versions - 1) if num_versions > 1 else 0
            indices = [round(i * step) for i in range(num_versions)]
            # ensure no duplicates due to rounding
            indices = sorted(list(set(indices)))
            sampled = [versions_data[i] for i in indices]

        # Gather data concurrently with a semaphore
        sem = asyncio.Semaphore(5)
        eco = ecosystem.lower()
        
        async def enrich_version(vid: int, vdata: dict) -> TemporalDataPoint:
            ver = vdata["version"]
            pub = vdata["published_at"]
            fan_out = vdata.get("fan_out", 0)

            async with sem:
                # Resolve PyPI fan_out per-version if it was deferred
                if fan_out == -1 and eco == "pypi":
                    fan_out = await self._resolve_pypi_fan_out(package_name, ver)

                # 1. Fetch historical dependents from deps.dev
                dep_data = await self.deps_dev.get_dependents(ecosystem, package_name, ver)
                global_fan_in = dep_data.total if dep_data else None

                # 2. Historical vulnerability count
                q = {
                    "ecosystem": ecosystem,
                    "package": package_name,
                    "version": ver
                }
                osv_res = await query_batch_vulns([q])
                key = f"{package_name}@{ver}"
                vuln_count = len(osv_res.get(key, []))

                return TemporalDataPoint(
                    version=ver,
                    published_at=pub,
                    fan_out=fan_out,
                    global_fan_in=global_fan_in,
                    vuln_count=vuln_count
                )

        tasks = [enrich_version(i, vdata) for i, vdata in enumerate(sampled)]
        data_points = await asyncio.gather(*tasks)

        # Sort just in case async returns slightly out of order (though gather preserves it usually)
        data_points.sort(key=lambda dp: dp.published_at)

        return TemporalReport(
            ecosystem=ecosystem,
            package_name=package_name,
            data_points=data_points,
            total_versions_available=total_available,
            sampled_versions=len(data_points)
        )

