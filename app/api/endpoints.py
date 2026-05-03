"""
OSCAR Dependency Graph Observatory — API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import json
from app.models.api import DirectDependenciesResponse, TransitiveDependenciesResponse
from app.graph.direct import DirectDependencyService
from app.storage.factory import get_storage
from app.ingestion.npm import PackageNotFoundError

router = APIRouter(tags=["Dependencies"])


def get_direct_dependency_service(storage=Depends(get_storage)):
    return DirectDependencyService(storage)

def get_transitive_dependency_service(direct_service=Depends(get_direct_dependency_service)):
    from app.graph.transitive import TransitiveDependencyService
    return TransitiveDependencyService(direct_service)


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}/transitive",
    summary="Get Transitive Dependencies (Stream)",
    description="Streams Server-Sent Events (SSE) detailing graph resolution progress. Ends with a 'complete' event containing the graph."
)
async def get_transitive_dependencies(
    ecosystem: str,
    package: str,
    version: str,
    service=Depends(get_transitive_dependency_service)
):
    """
    Retrieve the full transitive dependency graph via BFS stream.
    Yields progress events and ends with a complete event.
    """
    async def event_publisher():
        try:
            async for event in service.stream_transitive_graph(ecosystem, package, version):
                # Using model_dump_json if it's a Pydantic model is handled by the service yielding dicts
                yield f"data: {json.dumps(event)}\n\n"
        except PackageNotFoundError as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': f'Internal error: {str(e)}'})}\n\n"

    return StreamingResponse(event_publisher(), media_type="text/event-stream")


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}/depths",
    summary="Get Transitive Depths",
    description="Returns a dictionary mapping node IDs to their depth from the root."
)
async def get_package_depths(
    ecosystem: str,
    package: str,
    version: str,
    direct_service: DirectDependencyService = Depends(get_direct_dependency_service)
):
    from app.graph.analytics import AnalyticsService
    analytics_service = AnalyticsService(direct_service.storage)
    
    try:
        depths = analytics_service.get_transitive_depths(ecosystem, package, version)
        return depths
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}/libyears",
    summary="Get Transitive Libyears Breakdown",
    description="Returns a dictionary mapping node IDs to their libyears debt."
)
async def get_package_libyears_breakdown(
    ecosystem: str,
    package: str,
    version: str,
    direct_service: DirectDependencyService = Depends(get_direct_dependency_service)
):
    from app.graph.analytics import AnalyticsService
    analytics_service = AnalyticsService(direct_service.storage)
    
    try:
        libyears = analytics_service.get_libyears_breakdown(ecosystem, package, version)
        return libyears
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}",
    response_model=DirectDependenciesResponse,
    summary="Get Direct Dependencies",
    description="Returns the immediate dependencies of a specific package version."
)
async def get_direct_dependencies(
    ecosystem: str,
    package: str,
    version: str,
    service: DirectDependencyService = Depends(get_direct_dependency_service)
):
    """
    Retrieve direct dependencies.
    Note: The 'package:path' syntax allows packages with slashes (e.g. '@types/node').
    """
    try:
        deps = await service.get_direct_dependencies(ecosystem, package, version)
        return DirectDependenciesResponse(
            package=package,
            version=version,
            ecosystem=ecosystem,
            dependencies=deps
        )
    except PackageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch unexpected errors (like RegistryConnectionError) and return 500
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/packages/{ecosystem}/{package:path}/{version}",
    summary="Get Package Details",
    description="Returns package metadata and central metrics."
)
async def get_package_details(
    ecosystem: str,
    package: str,
    version: str,
    direct_service: DirectDependencyService = Depends(get_direct_dependency_service)
):
    """
    Retrieve package details including metrics.
    """
    from app.models.api import PackageDetailsResponse
    from app.graph.analytics import AnalyticsService
    analytics_service = AnalyticsService(direct_service.storage)
    
    try:
        versions = direct_service.storage.get_versions(ecosystem, package)
        version_exists = any(v.version == version for v in versions)

        if not version_exists:
            # Auto-ingest the specific version if it isn't stored yet
            await direct_service._ingest_package(ecosystem, package, version)
            versions = direct_service.storage.get_versions(ecosystem, package)
            version_exists = any(v.version == version for v in versions)

        if not version_exists:
            raise HTTPException(status_code=404, detail=f"Version {version} not found for package {package}")
            
        # Guarantee local cache warming mathematically by fully pulling the transitive graph into local Postgres
        # This pays a one-time ~3-8 second penalty, which fulfills the required constraints for true Libyear calculation.
        from app.graph.transitive import TransitiveDependencyService
        t_service = TransitiveDependencyService(direct_service)
        try:
            async for _ in t_service.stream_transitive_graph(ecosystem, package, version):
                pass # Unroll the BFS stream exclusively to trigger the backend ingestion
        except Exception as e:
            import logging
            logging.error(f"Transitive cache mapping failed in detail-view: {e}")
            
        metrics = await analytics_service.get_package_metrics(ecosystem, package, version)
        
        return PackageDetailsResponse(
            id=f"{ecosystem}:{package}@{version}",
            ecosystem=ecosystem,
            name=package,
            version=version,
            metrics=metrics
        )
    except PackageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
