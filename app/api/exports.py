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
    description="Returns the raw exported graph data across the entire specific ecosystem in JSON, CSV, or GraphML formats."
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
        elif format_lower == "graphml":
            data = service.export_graph_graphml(ecosystem)
            return PlainTextResponse(content=data, media_type="application/xml")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}. Use 'json', 'csv', or 'graphml'.")
    except HTTPException:
        # Re-raise explicit HTTP exceptions instead of throwing 500
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/export/{ecosystem}/{package:path}/{version}/sbom",
    summary="Export Package SBOM",
    description="Generates a CycloneDX or SPDX SBOM for the resolved transitive dependency graph."
)
async def export_package_sbom(
    ecosystem: str,
    package: str,
    version: str,
    format: str = "cyclonedx",
    storage=Depends(get_storage)
):
    from app.graph.direct import DirectDependencyService
    from app.graph.transitive import TransitiveDependencyService
    from app.exporters.sbom_exporter import SBOMExporter
    from app.models.api import TransitiveDependenciesResponse
    from app.graph.analytics import AnalyticsService
    from app.vulnerability.osv_client import query_batch_vulns

    direct_service = DirectDependencyService(storage)
    transitive_service = TransitiveDependencyService(direct_service)
    
    # 1. Resolve full transitive graph by consuming the stream
    graph_data_dict = None
    try:
        async for event in transitive_service.stream_transitive_graph(ecosystem, package, version):
            if event.get("type") == "error":
                raise HTTPException(status_code=400, detail=event.get("message"))
            if event.get("type") == "complete":
                graph_data_dict = event.get("data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph resolution failed: {str(e)}")

    if not graph_data_dict:
        raise HTTPException(status_code=404, detail="Could not resolve package graph.")

    graph_data = TransitiveDependenciesResponse(**graph_data_dict)

    # 2. Fetch Vulnerability data
    analytics = AnalyticsService(storage)
    depths = analytics.get_transitive_depths(ecosystem, package, version)
    
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
        
    vulnerabilities = {"breakdown": {}}
    if queries:
        try:
            breakdown = await query_batch_vulns(queries)
            vulnerabilities["breakdown"] = breakdown
        except Exception as e:
            import logging
            logging.error(f"Vulnerability breakdown failed during SBOM generation: {e}")

    # 3. Export
    exporter = SBOMExporter()
    format_lower = format.lower()
    
    try:
        if format_lower == "cyclonedx":
            sbom_data = exporter.export_cyclonedx(ecosystem, package, version, graph_data, vulnerabilities)
            return JSONResponse(content=sbom_data)
        elif format_lower == "spdx":
            sbom_data = exporter.export_spdx(ecosystem, package, version, graph_data, vulnerabilities)
            return JSONResponse(content=sbom_data)
        else:
            raise HTTPException(status_code=400, detail="Invalid format. Use 'cyclonedx' or 'spdx'.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"SBOM generation failed: {str(e)}")

