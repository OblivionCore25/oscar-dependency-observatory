"""
OSCAR Dependency Graph Observatory — Vulnerability API Endpoint

Exposes a transitive vulnerability breakdown for a specific package version
by querying the OSV.dev advisory database in batch.
"""

from fastapi import APIRouter, Depends, HTTPException

from app.models.api import VulnerabilityBreakdownResponse
from app.graph.direct import DirectDependencyService
from app.storage.factory import get_storage

router = APIRouter(tags=["Vulnerability"])


def get_direct_dependency_service(storage=Depends(get_storage)):
    return DirectDependencyService(storage)


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}/vulnerabilities",
    response_model=VulnerabilityBreakdownResponse,
    summary="Get Transitive Vulnerability Breakdown",
    description=(
        "Queries OSV.dev for known CVEs affecting every resolved transitive dependency. "
        "Returns a dictionary mapping pkg@ver to vulnerability summaries, plus aggregate counts."
    ),
)
async def get_vulnerability_breakdown(
    ecosystem: str,
    package: str,
    version: str,
    direct_service: DirectDependencyService = Depends(get_direct_dependency_service),
):
    from app.graph.analytics import AnalyticsService
    from app.vulnerability.osv_client import query_batch_vulns

    analytics = AnalyticsService(direct_service.storage)

    try:
        # Reuse the same version-aware graph traversal used by libyears/depths
        depths = analytics.get_transitive_depths(ecosystem, package, version)

        if not depths:
            return VulnerabilityBreakdownResponse(
                breakdown={},
                totalAffected=0,
                totalVulns=0,
                severityCounts={"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0, "UNKNOWN": 0},
            )

        # Build batch query from all resolved descendants
        queries = []
        for node_id in depths.keys():
            if "@" not in node_id:
                continue
            pkg_name, ver = node_id.rsplit("@", 1)
            queries.append({
                "ecosystem": ecosystem,
                "package": pkg_name,
                "version": ver,
            })

        # Batch query OSV
        breakdown = await query_batch_vulns(queries)

        # Compute aggregates
        total_affected = len(breakdown)
        total_vulns = sum(len(v) for v in breakdown.values())

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MODERATE": 0, "LOW": 0, "UNKNOWN": 0}
        for vuln_list in breakdown.values():
            for vuln in vuln_list:
                sev = vuln.get("severity", "UNKNOWN").upper()
                if sev in severity_counts:
                    severity_counts[sev] += 1
                else:
                    severity_counts["UNKNOWN"] += 1

        return VulnerabilityBreakdownResponse(
            breakdown=breakdown,
            totalAffected=total_affected,
            totalVulns=total_vulns,
            severityCounts=severity_counts,
        )

    except Exception as e:
        import logging
        logging.error(f"Vulnerability breakdown failed: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
