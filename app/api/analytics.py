"""
OSCAR Dependency Graph Observatory — Analytics Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.api import TopRiskResponse, CoverageResponse, EnrichmentResponse
from app.graph.analytics import AnalyticsService
from app.enrichment.enrichment_service import EnrichmentService
from app.storage.factory import get_storage

router = APIRouter(tags=["Analytics"])


def get_analytics_service(storage=Depends(get_storage)):
    return AnalyticsService(storage)


def get_enrichment_service():
    return EnrichmentService()


@router.get(
    "/analytics/top-risk",
    response_model=TopRiskResponse,
    summary="Get Top Risk Packages",
    description="Returns packages sorted by their ecosystem-wide bottleneck risk score."
)
async def get_top_risk(
    ecosystem: str = "npm",
    limit: int = 100,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Retrieves the most central generic risk packages.
    Capped at 100 items with local-only metrics for fast response.
    Enrichment is deferred to the per-item /analytics/enrich endpoint.
    """
    try:
        # Cap limit to 100 for performance
        capped_limit = min(limit, 100)
        response = await service.get_top_risk(ecosystem, capped_limit)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/analytics/coverage",
    response_model=CoverageResponse,
    summary="Get Graph Coverage",
    description="Returns how many unique packages are ingested vs. the estimated ecosystem total."
)
async def get_coverage(
    ecosystem: str = "npm",
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Returns graph coverage statistics to assess fan-in metric confidence.
    """
    try:
        return await service.get_coverage(ecosystem)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/analytics/enrich/{ecosystem}/{package:path}/{version}",
    response_model=EnrichmentResponse,
    summary="Enrich Package with External Data",
    description="Fetches ground-truth metrics from deps.dev, OpenSSF Scorecard, and registry downloads for a single package."
)
async def enrich_package(
    ecosystem: str,
    package: str,
    version: str,
    enrichment: EnrichmentService = Depends(get_enrichment_service)
):
    """
    On-demand enrichment for a single package.
    Called lazily by the frontend for visible table rows and search results.
    All results are TTL-cached server-side (1 hour for deps.dev, 6 hours for Scorecard, 24 hours for downloads).
    """
    try:
        data = await enrichment.enrich_package(ecosystem, package, version)
        return EnrichmentResponse(
            ecosystem=ecosystem,
            package=package,
            version=version,
            global_fan_in=data.global_fan_in,
            global_direct_dependents=data.global_direct_dependents,
            global_indirect_dependents=data.global_indirect_dependents,
            monthly_downloads=data.monthly_downloads,
            scorecard_score=data.scorecard_score,
            scorecard_checks=data.scorecard_checks,
            source_repo_url=data.source_repo_url,
            licenses=data.licenses,
            is_deprecated=data.is_deprecated,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Enrichment failed: {str(e)}")
