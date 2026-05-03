"""
OSCAR — Cross-Level Risk Propagation API Router
"""

from fastapi import APIRouter, HTTPException, Query

from app.analytics.cross_level import CrossLevelAnalyzer
from app.models.cross_level import CrossLevelReport

router = APIRouter(prefix="/analytics", tags=["Cross-Level Analytics"])
analyzer = CrossLevelAnalyzer()


@router.get(
    "/{ecosystem}/{package:path}/{version}/cross-level",
    response_model=CrossLevelReport,
    summary="Cross-Level Risk Analysis",
    description=(
        "Synthesizes ecosystem-level dependency metrics with method-level "
        "internal architecture metrics to produce a unified cross-level risk "
        "ranking across the supply chain."
    ),
)
async def get_cross_level_analysis(
    ecosystem: str,
    package: str,
    version: str,
    top_n: int = Query(
        5,
        ge=1,
        le=20,
        description="Number of top-bottleneck dependencies to analyze at the method level.",
    ),
):
    """
    Performs cross-level risk analysis for the top-N most structurally
    important transitive dependencies of the given package.

    This is the crown jewel endpoint: it bridges both observatories to find
    the single most dangerous method in the entire supply chain.
    """
    try:
        report = await analyzer.analyze(
            ecosystem=ecosystem,
            package_name=package,
            version=version,
            top_n=top_n,
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cross-level analysis failed: {str(e)}")
