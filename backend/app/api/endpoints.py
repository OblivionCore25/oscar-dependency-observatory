"""
OSCAR Dependency Graph Observatory — API Endpoints
"""

from fastapi import APIRouter, HTTPException, Depends
from app.models.api import DirectDependenciesResponse, TransitiveDependenciesResponse
from app.graph.direct import DirectDependencyService
from app.storage.factory import get_storage
from app.ingestion.npm import PackageNotFoundError

router = APIRouter(tags=["Dependencies"])

# Dependency Injection for the API
def get_direct_dependency_service(storage=Depends(get_storage)):
    return DirectDependencyService(storage)

def get_transitive_dependency_service(direct_service=Depends(get_direct_dependency_service)):
    from app.graph.transitive import TransitiveDependencyService
    return TransitiveDependencyService(direct_service)


@router.get(
    "/dependencies/{ecosystem}/{package:path}/{version}/transitive",
    response_model=TransitiveDependenciesResponse,
    summary="Get Transitive Dependencies",
    description="Returns the full transitive dependency graph."
)
async def get_transitive_dependencies(
    ecosystem: str,
    package: str,
    version: str,
    service=Depends(get_transitive_dependency_service)
):
    """
    Retrieve full graph dependencies via BFS.
    """
    try:
        graph = await service.get_transitive_graph(ecosystem, package, version)
        return graph
    except PackageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
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
