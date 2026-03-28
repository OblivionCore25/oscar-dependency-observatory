import pytest
from pathlib import Path

from app.method_observatory.storage.json_storage import JsonStorage
from app.method_observatory.models.analysis_result import AnalysisResult, AnalysisMeta, MethodMetrics, MethodNode
from app.method_observatory.models.call_edge import CallEdge
from app.models.domain import DependencyEdge

@pytest.fixture
def storage(tmp_path):
    return JsonStorage(data_directory=tmp_path)

@pytest.fixture
def dummy_result():
    meta = AnalysisMeta(
        project_slug="test-proj",
        project_path="/tmp/test",
        method_count=1, file_count=1,
        analysis_approach="AST",
        analyzed_at="2024-01-01T00:00:00Z",
        total_loc=10, class_count=0, module_count=1, edge_count=0, unresolved_call_count=0
    )
    methods = [
        MethodNode(id="app:func", file_path="app.py", name="func", qualified_name="app.func", kind="function", line_start=1, line_end=5, module="app")
    ]
    calls = [
        CallEdge(source_id="app:func", target_id="app:func", call_type="direct", confidence=1.0, line=2)
    ]
    metrics = [
        MethodMetrics(
            method_id="app:func", fan_in=0, fan_out=0, bottleneck_score=0.0, complexity=1,
            is_orphan=True, betweenness_centrality=0.0, blast_radius=0, community_id=None
        )
    ]
    return AnalysisResult(
        meta=meta, methods=methods, classes=[], modules=[], calls=calls, imports=[], inheritance=[], metrics=metrics
    )

def test_save_and_load(storage, dummy_result):
    # Save
    storage.save("test-proj", dummy_result)
    
    # Load
    loaded = storage.load("test-proj")
    assert loaded is not None
    assert loaded.meta.project_slug == "test-proj"
    assert len(loaded.methods) == 1
    assert loaded.methods[0].id == "app:func"
    assert len(loaded.calls) == 1
    
    # List projects
    projects = storage.list_projects()
    assert "test-proj" in projects
    
def test_load_non_existent(storage):
    assert storage.load("unknown") is None

def test_read_list_empty(storage, tmp_path):
    # Tests the edge case where a specific JSON file is missing
    proj_dir = tmp_path / "method_observatory" / "corrupted-proj"
    proj_dir.mkdir(parents=True)
    
    storage._write(proj_dir / "analysis_meta.json", {
        "project_slug": "corrupted-proj",
        "project_path": "/tmp",
        "method_count": 0,
        "file_count": 0,
        "analysis_approach": "AST",
        "analyzed_at": "2024-01-01T00:00:00Z",
        "total_loc": 0,
        "class_count": 0,
        "module_count": 0,
        "edge_count": 0,
        "unresolved_call_count": 0
    })
    
    # The others don't exist, _read_list should return []
    loaded = storage.load("corrupted-proj")
    assert loaded is not None
    assert len(loaded.methods) == 0
