"""
OSCAR Dependency Graph Observatory — Analytics Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.api import TopRiskResponse
from app.graph.analytics import AnalyticsService
from app.storage.json_storage import JSONStorage

router = APIRouter(tags=["Analytics"])

def get_storage():
    return JSONStorage(base_dir="data")

def get_analytics_service(storage=Depends(get_storage)):
    return AnalyticsService(storage)


@router.get(
    "/analytics/top-risk",
    response_model=TopRiskResponse,
    summary="Get Top Risk Packages",
    description="Returns packages sorted by their ecosystem-wide bottleneck risk score."
)
async def get_top_risk(
    ecosystem: str = "npm",
    limit: int = 10,
    service: AnalyticsService = Depends(get_analytics_service)
):
    """
    Retrieves the most central generic risk packages.
    """
    try:
        response = await service.get_top_risk(ecosystem, limit)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
