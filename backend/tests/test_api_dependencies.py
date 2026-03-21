from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints import get_storage
from app.models.domain import Package, Version, DependencyEdge
from app.storage.json_storage import JSONStorage
import pytest
from tempfile import TemporaryDirectory

@pytest.fixture
def mock_storage():
    """Provides a temporary JSONStorage to the API as a dependency override."""
    with TemporaryDirectory() as tmpdir:
        storage = JSONStorage(base_dir=tmpdir)
        
        # Pre-seed some mock data
        storage.save_package(Package(ecosystem="npm", name="react"))
        storage.save_versions([Version(package_name="react", ecosystem="npm", version="18.2.0")])
        storage.save_edges([
            DependencyEdge(source_package="react", source_version="18.2.0", target_package="loose-envify", version_constraint="^1.1.0", ecosystem="npm"),
            DependencyEdge(source_package="react", source_version="18.2.0", target_package="object-assign", version_constraint="^4.1.1", ecosystem="npm"),
        ])
        yield storage

@pytest.fixture
def client(mock_storage):
    """Override the get_storage dependency so endpoints hit our mock storage."""
    app.dependency_overrides[get_storage] = lambda: mock_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_direct_dependencies_success(client):
    """Test retrieving direct dependencies for a pre-ingested package."""
    response = client.get("/dependencies/npm/react/18.2.0")
    assert response.status_code == 200
    
    data = response.json()
    assert data["ecosystem"] == "npm"
    assert data["package"] == "react"
    assert data["version"] == "18.2.0"
    
    deps = data["dependencies"]
    assert len(deps) == 2
    
    targets = [d["name"] for d in deps]
    assert "loose-envify" in targets
    assert "object-assign" in targets


def test_get_direct_dependencies_scoped(client, mock_storage):
    """Test that scoped packages handle well in the URL routing."""
    mock_storage.save_package(Package(ecosystem="npm", name="@types/node"))
    mock_storage.save_versions([Version(package_name="@types/node", ecosystem="npm", version="20.0.0")])
    mock_storage.save_edges([])
    
    # Path parameter package should correctly parse @types/node
    response = client.get("/dependencies/npm/@types/node/20.0.0")
    assert response.status_code == 200
    
    data = response.json()
    assert data["package"] == "@types/node"
    assert len(data["dependencies"]) == 0


def test_get_direct_dependencies_invalid_ecosystem(client):
    """Test using an unsupported ecosystem returns 400."""
    response = client.get("/dependencies/pypi/requests/2.28.0")
    assert response.status_code == 400
    assert "not currently supported" in response.json()["detail"]
