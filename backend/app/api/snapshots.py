"""
OSCAR Dependency Graph Observatory — Snapshot Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from app.storage.factory import get_storage
from app.storage import StorageService
from app.models.domain import Snapshot

router = APIRouter(tags=["Snapshots"])

class CreateSnapshotRequest(BaseModel):
    description: Optional[str] = Field(default=None, description="Optional description for the snapshot")

class SnapshotComparisonResponse(BaseModel):
    snapshot_1_id: str
    snapshot_2_id: str
    ecosystem: str
    added_edges: int = Field(description="Edges present in snapshot 2 but not in snapshot 1")
    removed_edges: int = Field(description="Edges present in snapshot 1 but not in snapshot 2")
    # In a full implementation, we'd return lists of actual edges or changes,
    # but for this MVP metric returning counts is sufficient

def get_storage_service(storage=Depends(get_storage)) -> StorageService:
    return storage

@router.post(
    "/snapshots/{ecosystem}",
    response_model=Snapshot,
    summary="Create Snapshot",
    description="Captures the current dependency graph state for an ecosystem."
)
async def create_snapshot(
    ecosystem: str,
    request: CreateSnapshotRequest,
    storage: StorageService = Depends(get_storage_service)
):
    try:
        return storage.create_snapshot(ecosystem, request.description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/snapshots/{ecosystem}",
    response_model=List[Snapshot],
    summary="List Snapshots",
    description="Lists all historical snapshots for an ecosystem."
)
async def list_snapshots(
    ecosystem: str,
    storage: StorageService = Depends(get_storage_service)
):
    try:
        return storage.list_snapshots(ecosystem)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/snapshots/{ecosystem}/compare",
    response_model=SnapshotComparisonResponse,
    summary="Compare Snapshots",
    description="Compares two snapshots and returns edge delta counts."
)
async def compare_snapshots(
    ecosystem: str,
    snapshot_1: str,
    snapshot_2: str,
    storage: StorageService = Depends(get_storage_service)
):
    try:
        edges_1 = storage.get_snapshot_edges(snapshot_1)
        edges_2 = storage.get_snapshot_edges(snapshot_2)

        # Determine uniqueness by source/target pair
        set_1 = {f"{e.source_package}@{e.source_version}->{e.target_package}" for e in edges_1}
        set_2 = {f"{e.source_package}@{e.source_version}->{e.target_package}" for e in edges_2}

        added = len(set_2 - set_1)
        removed = len(set_1 - set_2)

        return SnapshotComparisonResponse(
            snapshot_1_id=snapshot_1,
            snapshot_2_id=snapshot_2,
            ecosystem=ecosystem,
            added_edges=added,
            removed_edges=removed
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
