"""
OSCAR Dependency Graph Observatory — Export API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse, PlainTextResponse

from app.storage.factory import get_storage
from app.exporters.graph_exporter import ExportService

router = APIRouter(tags=["Export"])

def get_export_service(storage=Depends(get_storage)):
    return ExportService(storage)


@router.get(
    "/export/{ecosystem}/graph",
    summary="Export Complete Graph Dataset",
    description="Returns the raw exported graph data across the entire specific ecosystem in JSON or CSV formats."
)
async def export_graph(
    ecosystem: str,
    format: str = "json",
    service: ExportService = Depends(get_export_service)
):
    """
    Exports the stored repository dependency edges to basic flat data formats.
    """
    try:
        format_lower = format.lower()
        if format_lower == "json":
            data = service.export_graph_json(ecosystem)
            return JSONResponse(content=data)
        elif format_lower == "csv":
            data = service.export_graph_csv(ecosystem)
            # Use PlainTextResponse to avoid typical JSON wrapping that FastAPI does for strings natively
            return PlainTextResponse(content=data, media_type="text/csv")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'json' or 'csv'.")
    except HTTPException:
        # Re-raise explicit HTTP exceptions instead of throwing 500
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
