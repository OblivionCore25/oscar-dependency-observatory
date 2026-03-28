import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.main import app
from app.method_observatory.api.router import get_service, AnalyzeRequest
from app.method_observatory.models.analysis_result import AnalysisResult, AnalysisMeta, MethodMetrics, MethodNode
from app.method_observatory.models.call_edge import CallEdge

# --- Mock Data ---
mock_meta = AnalysisMeta(
    project_slug="test-project",
    project_path="/tmp/test-project",
    method_count=2,
    file_count=1,
    analysis_approach="AST",
    analyzed_at="2024-01-01T00:00:00Z",
    total_loc=100,
    class_count=1,
    module_count=1,
    edge_count=1,
    unresolved_call_count=0,
)

mock_methods = [
    MethodNode(
        id="app.main:funcA",
        file_path="app/main.py",
        name="funcA",
        qualified_name="app.main.funcA",
        kind="function",
        line_start=1,
        line_end=5,
        module="app.main"
    ),
    MethodNode(
        id="app.main:funcB",
        file_path="app/main.py",
        name="funcB",
        qualified_name="app.main.funcB",
        kind="function",
        line_start=7,
        line_end=10,
        module="app.main"
    ),
]

mock_metrics = [
    MethodMetrics(
        method_id="app.main:funcA",
        fan_in=2, fan_out=1, bottleneck_score=2.0, complexity=5, is_orphan=False,
        betweenness_centrality=0.5, blast_radius=2, community_id=1
    ),
    MethodMetrics(
        method_id="app.main:funcB",
        fan_in=0, fan_out=0, bottleneck_score=0.0, complexity=1, is_orphan=True,
        betweenness_centrality=0.0, blast_radius=0, community_id=None
    ),
]

mock_calls = [
    CallEdge(source_id="app.main:funcA", target_id="app.main:funcB", call_type="direct", confidence=1.0, line=3)
]

mock_result = AnalysisResult(
    meta=mock_meta,
    methods=mock_methods,
    calls=mock_calls,
    metrics=mock_metrics,
    classes=[],
    modules=[],
    imports=[],
    inheritance=[]
)

# --- Fixtures ---
@pytest.fixture
def mock_service():
    service = MagicMock()
    service.list_projects.return_value = ["test-project"]
    service.load.return_value = mock_result
    service.analyze.return_value = mock_result
    return service

@pytest.fixture
def client(mock_service):
    app.dependency_overrides[get_service] = lambda: mock_service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()

# --- Tests ---

def test_analyze_project_success(client, mock_service):
    from unittest.mock import AsyncMock
    with patch("app.method_observatory.api.router.PackageDownloader") as mock_downloader:
        mock_downloader.return_value.download_and_extract = AsyncMock(return_value="/tmp/fake-dir")
        
        response = client.post(
            "/methods/analyze", 
            json={"package_name": "pytest", "package_version": "7.0.0"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["project_slug"] == "pytest-7.0.0"
        assert len(data["top_risk"]) == 2

def test_analyze_project_missing_args(client):
    response = client.post("/methods/analyze", json={})
    assert response.status_code == 400

def test_analyze_project_server_error(client, mock_service):
    mock_service.analyze.side_effect = Exception("Mock Error")
    response = client.post("/methods/analyze", json={"project_path": "/path/to/project"})
    assert response.status_code == 500

def test_list_projects(client):
    response = client.get("/methods/projects")
    assert response.status_code == 200
    assert response.json() == ["test-project"]

def test_get_project_meta(client):
    response = client.get("/methods/test-project")
    assert response.status_code == 200
    assert response.json()["project_slug"] == "test-project"

def test_get_project_meta_not_found(client, mock_service):
    mock_service.load.return_value = None
    response = client.get("/methods/unknown")
    assert response.status_code == 404

def test_get_top_risk(client):
    response = client.get("/methods/test-project/top-risk?limit=1")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["method_id"] == "app.main:funcA"

def test_get_orphans(client):
    response = client.get("/methods/test-project/orphans")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["metrics"]["method_id"] == "app.main:funcB"

def test_get_hotspots(client):
    response = client.get("/methods/test-project/hotspots")
    assert response.status_code == 200
    assert len(response.json()) == 2
    # funcA score = 5 * 0.5 * 2 = 5
    # funcB score = 1 * 0.0 * 0 = 0
    assert response.json()[0]["metrics"]["method_id"] == "app.main:funcA"

def test_get_communities(client):
    response = client.get("/methods/test-project/communities")
    assert response.status_code == 200
    data = response.json()
    assert "1" in data
    assert data["1"][0]["method"]["id"] == "app.main:funcA"

def test_get_blast_radius(client):
    response = client.get("/methods/test-project/method/app.main:funcA/blast-radius")
    assert response.status_code == 200
    data = response.json()
    assert data["root"] == "app.main:funcA"
    assert data["node_count"] == 2
    assert len(data["edges"]) == 1

def test_get_blast_radius_not_found(client):
    response = client.get("/methods/test-project/method/unknown/blast-radius")
    assert response.status_code == 404

def test_get_method_detail(client):
    response = client.get("/methods/test-project/method/app.main:funcB")
    assert response.status_code == 200
    data = response.json()
    assert data["method"]["id"] == "app.main:funcB"
    assert len(data["callers"]) == 1
    assert len(data["callees"]) == 0

def test_export_graph_json(client):
    response = client.get("/methods/test-project/graph?format=json")
    assert response.status_code == 200
    assert response.json()["node_count"] == 2

def test_export_graph_csv(client):
    response = client.get("/methods/test-project/graph?format=csv")
    assert response.status_code == 200
    assert "source,target" in response.text
