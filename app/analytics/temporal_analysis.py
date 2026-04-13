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
                        # PyPI /pypi/pkg/json doesn't give historical dependencies easily,
                        # requires fetching /pypi/pkg/version/json usually, but we can default to 0
                        # and let deps.dev provide missing data if possible.
                        # Wait, we can fetch version details sequentially or parallel if needed, but 
                        # for PyPI, let's keep direct_deps as 0 if we can't get it fast.
                        direct_deps = 0
                        if "requires_dist" in data.get("info", {}) and data["info"].get("version") == v:
                            # if it's the latest
                            direct_deps = len(data["info"].get("requires_dist") or [])

                        if upload_time:
                            versions.append({
                                "version": v,
                                "published_at": upload_time,
                                "fan_out": direct_deps
                            })
        
        # Sort by published string (ISO date format)
        versions.sort(key=lambda x: x.get("published_at", ""))
        return versions

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
        
        async def enrich_version(vid: int, vdata: dict) -> TemporalDataPoint:
            ver = vdata["version"]
            pub = vdata["published_at"]
            fan_out_guess = vdata.get("fan_out", 0)

            async with sem:
                # 1. Fetch historical dependents from deps.dev
                dep_data = await self.deps_dev.get_dependents(ecosystem, package_name, ver)
                global_fan_in = dep_data.total if dep_data else None

                # For PyPI, if we didn't get fan_out, we can get it from deps_dev graph API conditionally
                # but for now, we'll just use what we have or 0 if missing.

                # 2. Historical vulnerability count
                # query OSV to get vulnerabilities overlapping with this version
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
                    fan_out=fan_out_guess,
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
