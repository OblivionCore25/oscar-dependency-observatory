import pytest
import json
from datetime import datetime, timezone
import uuid
import os

from app.storage.json_storage import JSONStorage
from app.models.domain import Package, Version, DependencyEdge, Snapshot

@pytest.fixture
def storage(tmp_path):
    # Use tmp_path fixture provided by pytest for safe, isolated file operations
    return JSONStorage(base_dir=str(tmp_path))

def test_save_and_get_package(storage):
    pkg = Package(ecosystem="npm", name="react")
    storage.save_package(pkg)
    
    fetched = storage.get_package("npm", "react")
    assert fetched is not None
    assert fetched.name == "react"

    # Not found
    assert storage.get_package("npm", "unknown") is None

def test_save_and_get_versions(storage):
    # Empty list
    storage.save_versions([])

    now = datetime.now(timezone.utc)
    v1 = Version(ecosystem="npm", package_name="react", version="16.0.0", published_at=now)
    v2 = Version(ecosystem="npm", package_name="react", version="17.0.0", published_at=now)

    storage.save_versions([v1, v2])
    
    # Update existing
    v1_updated = Version(ecosystem="npm", package_name="react", version="16.0.0", published_at=now)
    storage.save_versions([v1_updated])

    versions = storage.get_versions("npm", "react")
    assert len(versions) == 2
    assert any(v.version == "16.0.0" for v in versions)

    all_versions = storage.get_all_versions("npm")
    assert len(all_versions) == 2

    # Not found
    assert storage.get_versions("npm", "unknown") == []

def test_save_and_get_edges(storage):
    # Empty list
    storage.save_edges([])

    now = datetime.now(timezone.utc)
    e1 = DependencyEdge(
        ecosystem="npm", source_package="react", source_version="16.0.0",
        target_package="loose-envify", version_constraint="^1.1.0",
        resolved_target_version="1.4.0", dependency_type="runtime",
        ingestion_timestamp=now
    )
    storage.save_edges([e1])

    # Overwrite
    storage.save_edges([e1])

    edges = storage.get_edges_for_version("npm", "react", "16.0.0")
    assert len(edges) == 1
    assert edges[0].resolved_target_version == "1.4.0"

    all_edges = storage.get_all_edges("npm")
    assert len(all_edges) == 1

    # Not found
    assert storage.get_edges_for_version("npm", "unknown", "1.0.0") == []

def test_snapshots(storage):
    # Setup some edges first
    now = datetime.now(timezone.utc)
    e1 = DependencyEdge(
        ecosystem="npm", source_package="react", source_version="16.0.0",
        target_package="loose-envify", version_constraint="^1.1.0",
        resolved_target_version="1.4.0", dependency_type="runtime",
        ingestion_timestamp=now
    )
    storage.save_edges([e1])

    # Create snapshot
    snap = storage.create_snapshot("npm", "Initial State")
    assert snap.snapshot_id is not None
    assert snap.description == "Initial State"

    snapshots = storage.list_snapshots("npm")
    assert len(snapshots) == 1
    assert snapshots[0].snapshot_id == snap.snapshot_id

    # Get snapshot edges
    snap_edges = storage.get_snapshot_edges(snap.snapshot_id)
    assert len(snap_edges) == 1
    assert snap_edges[0].source_package == "react"
    assert snap_edges[0].target_package == "loose-envify"

    # List snapshots none
    assert storage.list_snapshots("pypi") == []
    
    # Get snapshot edges none
    assert storage.get_snapshot_edges("invalid-id") == []

def test_get_all_non_existent_directories(storage):
    assert storage.get_all_versions("npm") == []
    assert storage.get_all_edges("npm") == []

def test_corrupt_files(storage, tmp_path):
    # Create corrupt files to trigger the ValueError / JSONDecodeError handlers
    now = datetime.now(timezone.utc)
    
    v1 = Version(ecosystem="npm", package_name="react", version="16.0.0", published_at=now)
    storage.save_versions([v1])
    e1 = DependencyEdge(
        ecosystem="npm", source_package="react", source_version="16.0.0",
        target_package="loose-envify", version_constraint="^1.1.0",
        resolved_target_version="1.4.0", dependency_type="runtime",
        ingestion_timestamp=now
    )
    storage.save_edges([e1])
    snap = storage.create_snapshot("npm", "Initial State")
    
    # Corrupt version file
    v_path = storage._get_path("npm", "versions", "react")
    v_path.write_text("{corrupt-json")
    
    # Exception handled gracefully
    assert len(storage.get_all_versions("npm")) == 0
    # Also save_versions merging shouldn't crash if corrupt
    storage.save_versions([v1])
    
    # Corrupt edge file
    e_path = storage._get_path("npm", "edges", "react_16.0.0")
    e_path.write_text("{corrupt-json")
    assert len(storage.get_all_edges("npm")) == 0
    
    # Corrupt snapshot file
    s_path = storage.base_dir / "npm" / "snapshots" / f"{snap.snapshot_id}.json"
    s_path.write_text("{corrupt-json")
    assert len(storage.list_snapshots("npm")) == 0
    assert len(storage.get_snapshot_edges(snap.snapshot_id)) == 0
