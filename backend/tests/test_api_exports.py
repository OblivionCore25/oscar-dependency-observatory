import pytest
from fastapi.testclient import TestClient
from tempfile import TemporaryDirectory

from app.main import app
from app.api.exports import get_storage as get_exports_storage
from app.storage.json_storage import JSONStorage
from app.models.domain import Package, Version, DependencyEdge


@pytest.fixture
def mock_storage():
    """Sets up an isolated flat-file environment simulating a simple resolved graph."""
    with TemporaryDirectory() as tmpdir:
        storage = JSONStorage(base_dir=tmpdir)
        
        # We need target packages and edge links
        storage.save_package(Package(ecosystem="npm", name="parent"))
        storage.save_package(Package(ecosystem="npm", name="child1"))
        storage.save_package(Package(ecosystem="npm", name="child2"))
        
        storage.save_versions([
            Version(package_name="parent", ecosystem="npm", version="1.0.0"),
            Version(package_name="child1", ecosystem="npm", version="2.0.0"),
            Version(package_name="child2", ecosystem="npm", version="3.0.0")
        ])
        
        storage.save_edges([
            DependencyEdge(
                source_package="parent", source_version="1.0.0", 
                target_package="child1", version_constraint="^2.0.0", ecosystem="npm"
            ),
            DependencyEdge(
                source_package="parent", source_version="1.0.0", 
                target_package="child2", version_constraint="~3.0.0", ecosystem="npm"
            )
        ])
        
        yield storage


@pytest.fixture
def client(mock_storage):
    app.dependency_overrides[get_exports_storage] = lambda: mock_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_export_json(client):
    """Test retrieving the JSON generic dataset."""
    response = client.get("/export/npm/graph?format=json")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ecosystem"] == "npm"
    assert len(data["nodes"]) == 3
    assert len(data["edges"]) == 2
    
    # Asserting correct mapping on edges
    edge_targets = [e["target"] for e in data["edges"]]
    assert "npm:child1" in edge_targets
    assert "npm:child2" in edge_targets


def test_export_csv(client):
    """Test retrieving the CSV spreadsheet representation of the graph."""
    response = client.get("/export/npm/graph?format=csv")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    
    csv_text = response.text
    lines = csv_text.strip().split("\r\n")
    
    # Header + 2 data rows
    assert len(lines) == 3
    assert lines[0] == "source,target,constraint,ecosystem"
    assert "npm:parent@1.0.0,npm:child1,^2.0.0,npm" in lines
    assert "npm:parent@1.0.0,npm:child2,~3.0.0,npm" in lines


def test_export_invalid_format(client):
    """Test error handler gracefully blocks unsupported file formats."""
    response = client.get("/export/npm/graph?format=xml")
    assert response.status_code == 400
    assert "Unsupported format" in response.text
