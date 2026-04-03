"""
OSCAR Dependency Graph Observatory — Packages Endpoint

GET /packages?ecosystem=npm&q=react&limit=20

Returns a list of packages already ingested in storage, optionally
filtered by a case-insensitive prefix search on the package name.
Single DB call: get_all_versions() — no metrics computation.
"""

from fastapi import APIRouter, Depends, Query
from app.models.api import IngestedPackageItem, IngestedPackagesResponse
from app.storage.json_storage import JSONStorage

router = APIRouter(tags=["Packages"])


def get_storage():
    from app.config.settings import settings
    if settings.storage_mode == "postgres":
        from app.storage.pg_storage import PgStorage
        return PgStorage(database_url=settings.database_url)
    return JSONStorage(base_dir=settings.data_directory)


@router.get(
    "/packages",
    response_model=IngestedPackagesResponse,
    summary="List Ingested Packages",
    description=(
        "Returns all packages already stored in the observatory database. "
        "Optionally filter by name prefix with ?q=. "
        "Use limit to cap the result set size."
    ),
)
async def list_ingested_packages(
    ecosystem: str = Query(default="npm", description="Ecosystem to query (npm or pypi)."),
    q: str = Query(default="", description="Optional case-insensitive name prefix filter."),
    limit: int = Query(default=50, ge=1, le=500, description="Max number of results."),
    storage=Depends(get_storage),
) -> IngestedPackagesResponse:
    """
    Lists packages already ingested into the observatory.
    A single get_all_versions() call is made — O(1) DB round-trip.
    Filtering and deduplication happen in Python on the returned rows.
    """
    all_versions = storage.get_all_versions(ecosystem)

    # Deduplicate: keep latest version seen per package name.
    # get_all_versions returns rows insertion-ordered; last write wins for version display.
    latest: dict[str, str] = {}
    for v in all_versions:
        if not q or v.package_name.lower().startswith(q.lower()):
            latest[v.package_name] = v.version  # later rows overwrite earlier

    total = len(latest)
    items = [
        IngestedPackageItem(ecosystem=ecosystem, name=name, version=version)
        for name, version in sorted(latest.items())  # alphabetical
    ][:limit]

    return IngestedPackagesResponse(ecosystem=ecosystem, packages=items, total=total)
