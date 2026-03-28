import pytest
from datetime import datetime, timezone

from app.storage.postgres_storage import PostgresStorage
from app.storage.postgres_models import Base
from app.models.domain import Package, Version, DependencyEdge, Snapshot

# Fixture to initialize an in-memory SQLite DB wrapped by PostgresStorage
@pytest.fixture
def storage():
    # Using sqlite:///:memory: for testing to avoid needing a real PG instance
    storage = PostgresStorage("sqlite:///:memory:")
    # Ensure tables are created
    Base.metadata.create_all(bind=storage.engine)
    yield storage
    Base.metadata.drop_all(bind=storage.engine)

def test_url_conversion():
    from unittest.mock import patch
    with patch("app.storage.postgres_storage.create_engine") as mock_engine:
        with patch("app.storage.postgres_storage.Base.metadata.create_all"):
            storage = PostgresStorage("postgres://user:pass@localhost/db")
            mock_engine.assert_called_once()
            called_url = mock_engine.call_args[0][0]
            assert "postgresql://" in str(called_url)

def test_save_and_get_package(storage):
    pkg = Package(ecosystem="npm", name="react")
    storage.save_package(pkg)
    
    # Save again should hit existing logic
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
    v1_updated = Version(ecosystem="npm", package_name="react", version="16.0.0", published_at=datetime.now(timezone.utc))
    storage.save_versions([v1_updated])

    versions = storage.get_versions("npm", "react")
    assert len(versions) == 2
    assert any(v.version == "16.0.0" for v in versions)

    all_versions = storage.get_all_versions("npm")
    assert len(all_versions) == 2

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

    # Update existing
    e1_updated = DependencyEdge(
        ecosystem="npm", source_package="react", source_version="16.0.0",
        target_package="loose-envify", version_constraint="^1.1.0",
        resolved_target_version="1.5.0", dependency_type="runtime",
        ingestion_timestamp=datetime.now(timezone.utc)
    )
    storage.save_edges([e1_updated])

    edges = storage.get_edges_for_version("npm", "react", "16.0.0")
    assert len(edges) == 1
    assert edges[0].resolved_target_version == "1.5.0"

    all_edges = storage.get_all_edges("npm")
    assert len(all_edges) == 1

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
