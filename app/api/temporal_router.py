from fastapi import APIRouter, HTTPException, Query
from app.analytics.temporal_analysis import TemporalAnalyzer
from app.models.temporal import TemporalReport

router = APIRouter(prefix="/analytics", tags=["Temporal Analytics"])
analyzer = TemporalAnalyzer()

@router.get("/{ecosystem}/{package}/temporal", response_model=TemporalReport)
async def get_temporal_analysis(
    ecosystem: str, 
    package: str, 
    versions: int = Query(15, ge=1, le=50, description="Number of historical versions to sample")
):
    """
    Returns a longitudinal structural analysis of a package over multiple versions,
    including blast radius and vulnerability accumulation.
    """
    try:
        report = await analyzer.analyze_temporal(ecosystem, package, num_versions=versions)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
