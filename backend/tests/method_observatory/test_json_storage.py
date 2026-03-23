import pytest
from app.method_observatory.storage.json_storage import JsonStorage
from app.method_observatory.models.analysis_result import AnalysisResult, AnalysisMeta
from datetime import datetime, timezone

def test_json_storage_roundtrip(tmp_path):
    storage = JsonStorage(tmp_path)
    
    meta = AnalysisMeta(
        project_slug="test_slug",
        project_path="/test",
        analyzed_at=datetime.now(timezone.utc),
        file_count=1,
        total_loc=10,
        method_count=0,
        class_count=0,
        module_count=0,
        edge_count=0,
        unresolved_call_count=0
    )
    result = AnalysisResult(meta=meta, methods=[], classes=[], modules=[], calls=[], imports=[], inheritance=[], metrics=[])
    
    storage.save("test_slug", result)
    
    loaded = storage.load("test_slug")
    assert loaded is not None
    assert loaded.meta.project_slug == "test_slug"
    
    assert "test_slug" in storage.list_projects()
