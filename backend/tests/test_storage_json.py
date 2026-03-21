import os
import pytest
from tempfile import TemporaryDirectory
from pathlib import Path

from app.models.domain import Package, Version, DependencyEdge
from app.storage.json_storage import JSONStorage

@pytest.fixture
def temp_storage():
    """Provides an isolated JSONStorage instance in a temp directory."""
    with TemporaryDirectory() as tmpdir:
        storage = JSONStorage(base_dir=tmpdir)
        yield storage

def test_save_and_get_package(temp_storage):
    pkg = Package(ecosystem="npm", name="react")
    
    # Assert not found initially
    assert temp_storage.get_package("npm", "react") is None
    
    # Save package
    temp_storage.save_package(pkg)
    
    # Retrieve and assert
    loaded_pkg = temp_storage.get_package("npm", "react")
    assert loaded_pkg is not None
    assert loaded_pkg.name == "react"
    assert loaded_pkg.ecosystem == "npm"


def test_save_and_get_versions(temp_storage):
    v1 = Version(package_name="react", ecosystem="npm", version="18.2.0")
    v2 = Version(package_name="react", ecosystem="npm", version="18.2.1")
    
    # Assert empty initially
    assert temp_storage.get_versions("npm", "react") == []
    
    # Save multiple
    temp_storage.save_versions([v1, v2])
    
    loaded_versions = temp_storage.get_versions("npm", "react")
    assert len(loaded_versions) == 2
    
    versions = [v.version for v in loaded_versions]
    assert "18.2.0" in versions
    assert "18.2.1" in versions
    
    # Test merge/upsert behavior by saving v3
    v3 = Version(package_name="react", ecosystem="npm", version="19.0.0")
    temp_storage.save_versions([v3])
    
    loaded_merged = temp_storage.get_versions("npm", "react")
    assert len(loaded_merged) == 3


def test_save_and_get_edges(temp_storage):
    edge1 = DependencyEdge(
        source_package="react",
        source_version="18.2.0",
        target_package="loose-envify",
        version_constraint="^1.1.0",
        ecosystem="npm"
    )
    edge2 = DependencyEdge(
        source_package="react",
        source_version="18.2.0",
        target_package="object-assign",
        version_constraint="^4.1.1",
        ecosystem="npm"
    )
    
    # Assert empty
    assert temp_storage.get_edges_for_version("npm", "react", "18.2.0") == []
    
    temp_storage.save_edges([edge1, edge2])
    
    loaded_edges = temp_storage.get_edges_for_version("npm", "react", "18.2.0")
    assert len(loaded_edges) == 2
    
    targets = [e.target_package for e in loaded_edges]
    assert "loose-envify" in targets
    assert "object-assign" in targets


def test_scoped_package_paths(temp_storage):
    """Test that packages with slashes handle perfectly inside get_path."""
    pkg = Package(ecosystem="npm", name="@types/node")
    temp_storage.save_package(pkg)
    
    loaded = temp_storage.get_package("npm", "@types/node")
    assert loaded is not None
    assert loaded.name == "@types/node"
