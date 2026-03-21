from fastapi.testclient import TestClient
from app.main import app
from app.api.endpoints import get_storage
from app.api.analytics import get_storage as get_analytics_storage
from app.models.domain import Package, Version, DependencyEdge
from app.storage.json_storage import JSONStorage
import pytest
from tempfile import TemporaryDirectory

@pytest.fixture
def mock_storage():
    """Provides a temporary JSONStorage with a pre-seeded fan-in graph."""
    with TemporaryDirectory() as tmpdir:
        storage = JSONStorage(base_dir=tmpdir)
        
        # Central Package (High Fan-In)
        storage.save_package(Package(ecosystem="npm", name="lodash"))
        storage.save_versions([Version(package_name="lodash", ecosystem="npm", version="4.17.21")])
        
        # Low risk leaf packages
        for pkg in ["app1", "app2", "app3"]:
            storage.save_package(Package(ecosystem="npm", name=pkg))
            storage.save_versions([Version(package_name=pkg, ecosystem="npm", version="1.0.0")])
            # Everyone depends on lodash explicitly
            storage.save_edges([
                DependencyEdge(source_package=pkg, source_version="1.0.0", target_package="lodash", version_constraint="^4.0.0", ecosystem="npm")
            ])
            
        # Lodash depends on something itself
        storage.save_package(Package(ecosystem="npm", name="lodash-dependency"))
        storage.save_versions([Version(package_name="lodash-dependency", ecosystem="npm", version="1.0.0")])
        storage.save_edges([
            DependencyEdge(source_package="lodash", source_version="4.17.21", target_package="lodash-dependency", version_constraint="1.0.0", ecosystem="npm")
        ])
        
        yield storage

@pytest.fixture
def client(mock_storage):
    """Override the get_storage dependencies for both routers."""
    app.dependency_overrides[get_storage] = lambda: mock_storage
    app.dependency_overrides[get_analytics_storage] = lambda: mock_storage
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_get_top_risk(client):
    """Test retrieving top-risk analytics sorting."""
    response = client.get("/analytics/top-risk?ecosystem=npm&limit=5")
    assert response.status_code == 200
    
    data = response.json()
    items = data["items"]
    
    assert len(items) > 0
    # The top risk should be lodash with FanIn = 3
    top_risk_pkg = items[0]
    assert top_risk_pkg["name"] == "lodash"
    assert top_risk_pkg["fanIn"] == 3
    assert top_risk_pkg["bottleneckScore"] == 3.0
    
    # lodash-dependency should be second with FanIn = 1
    second_risk_pkg = items[1]
    assert second_risk_pkg["name"] == "lodash-dependency"
    assert second_risk_pkg["fanIn"] == 1


def test_get_package_details(client):
    """Test retrieving metrics inside a single package details query."""
    response = client.get("/packages/npm/lodash/4.17.21")
    assert response.status_code == 200
    
    data = response.json()
    assert data["name"] == "lodash"
    assert data["version"] == "4.17.21"
    
    metrics = data["metrics"]
    assert metrics["fanIn"] == 3
    assert metrics["fanOut"] == 1
    # bottleneck is fan_in * fan_out (3 * 1 = 3)
    assert metrics["bottleneckScore"] == 3.0
