from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from pathlib import Path
from ..services.analysis_service import AnalysisService
from ..models.analysis_result import AnalysisResult, AnalysisMeta, MethodMetrics

router = APIRouter(prefix="/methods", tags=["Method Observatory"])


# ── Request/Response schemas ──────────────────────────────────────────────── #

class AnalyzeRequest(BaseModel):
    project_path: str | None = None  # Optional: Absolute path on filesystem
    project_slug: str | None = None  # Optional: Short identifier (derived if not provided)
    package_name: str | None = None  # Optional: PyPI package name to download
    package_version: str | None = None # Optional: PyPI package version to download
    exclude_tests: bool = True  # Default True: skip test files for cleaner metrics


class AnalyzeSummaryResponse(BaseModel):
    project_slug: str
    meta: AnalysisMeta
    top_risk: list[MethodMetrics]  # Top 10 by bottleneck score


class MethodDetailResponse(BaseModel):
    method: dict                   # Full MethodNode serialized
    metrics: MethodMetrics
    callers: list[dict]            # List of {method_node, edge_info}
    callees: list[dict]            # List of {method_node, edge_info}


# ── Dependency injection ──────────────────────────────────────────────────── #

def get_service() -> AnalysisService:
    from app.config.settings import settings
    return AnalysisService(
        data_directory=Path(settings.data_directory),
        oscar_version=settings.app_version,
        max_file_size_kb=settings.method_max_file_size_kb
    )


# ── Endpoints ─────────────────────────────────────────────────────────────── #

import tempfile
import shutil

from ..ingestion.package_downloader import PackageDownloader


@router.post("/analyze", response_model=AnalyzeSummaryResponse)
async def analyze_project(request: AnalyzeRequest, service: AnalysisService = Depends(get_service)):
    """
    Trigger analysis of a Python project directory.
    Can either use an existing local path or automatically download a package from PyPI.
    Runs the full ingestion → AST parsing → call resolution → metrics pipeline.
    Returns a summary with top-risk methods on completion.
    """
    if not request.project_path and not (request.package_name and request.package_version):
        raise HTTPException(status_code=400, detail="Must provide either project_path or both package_name and package_version")

    project_slug = request.project_slug
    if not project_slug:
        if request.package_name and request.package_version:
            project_slug = f"{request.package_name}-{request.package_version}"
        else:
             project_slug = Path(request.project_path).name

    temp_dir = None
    try:
        project_path = request.project_path
        if not project_path:
            temp_dir = tempfile.mkdtemp(prefix="oscar_method_download_")
            downloader = PackageDownloader()
            extracted_path = await downloader.download_and_extract(
                request.package_name, request.package_version, Path(temp_dir)
            )
            project_path = str(extracted_path)

        result = service.analyze(
            project_path=project_path,
            project_slug=project_slug,
            exclude_tests=request.exclude_tests,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if temp_dir and Path(temp_dir).exists():
            shutil.rmtree(temp_dir)

    top_risk = sorted(result.metrics, key=lambda m: m.bottleneck_score, reverse=True)[:10]
    return AnalyzeSummaryResponse(
        project_slug=project_slug,
        meta=result.meta,
        top_risk=top_risk,
    )


@router.get("/projects", response_model=list[str])
async def list_projects(service: AnalysisService = Depends(get_service)):
    """List all previously analyzed projects."""
    return service.list_projects()


@router.get("/{project_slug}", response_model=AnalysisMeta)
async def get_project_meta(project_slug: str, service: AnalysisService = Depends(get_service)):
    """Return analysis metadata for a project (summary statistics)."""
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")
    return result.meta


@router.get("/{project_slug}/top-risk", response_model=list[MethodMetrics])
async def get_top_risk(
    project_slug: str,
    limit: int = Query(default=10, ge=1, le=100),
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods ranked by bottleneck score (fan_in × fan_out).
    Mirrors OSCAR's /analytics/top-risk endpoint at the method level.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")
    ranked = sorted(result.metrics, key=lambda m: m.bottleneck_score, reverse=True)
    return ranked[:limit]


@router.get("/{project_slug}/orphans", response_model=list[dict])
async def get_orphans(
    project_slug: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods with fan_in=0 (never called within the project).
    Candidates for dead code removal.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    orphans = [m for m in result.metrics if m.is_orphan]
    return [{"method": method_map[m.method_id].model_dump(), "metrics": m.model_dump()}
            for m in orphans if m.method_id in method_map]


@router.get("/{project_slug}/hotspots", response_model=list[dict])
async def get_hotspots(
    project_slug: str,
    limit: int = Query(default=20, ge=1, le=100),
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods ranked by composite risk score (complexity * centrality * blast_radius).
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    hotspots = []
    for m in result.metrics:
        comp = m.complexity or 1
        cent = m.betweenness_centrality or 0.0
        blast = m.blast_radius or 0
        score = comp * cent * blast
        hotspots.append({
            "method": method_map[m.method_id].model_dump() if m.method_id in method_map else None,
            "metrics": m.model_dump(),
            "composite_risk": score
        })
    
    hotspots = [h for h in hotspots if h["method"]]
    ranked = sorted(hotspots, key=lambda x: x["composite_risk"], reverse=True)
    return ranked[:limit]


@router.get("/{project_slug}/communities", response_model=dict[str, list[dict]])
async def get_communities(
    project_slug: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return methods grouped by Louvain community assignment.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    communities = {}
    for m in result.metrics:
        cid = m.community_id
        if cid is None:
            continue
        cid_str = str(cid)
        if cid_str not in communities:
            communities[cid_str] = []
        if m.method_id in method_map:
            communities[cid_str].append({
                "method": method_map[m.method_id].model_dump(),
                "metrics": m.model_dump()
            })
    return communities


@router.get("/{project_slug}/method/{method_id:path}/blast-radius", response_model=dict)
async def get_blast_radius(
    project_slug: str,
    method_id: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return the transitive closure of downstream callees for a specific method.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    import networkx as nx
    G = nx.DiGraph()
    for c in result.calls:
        if c.confidence > 0:
            G.add_edge(c.source_id, c.target_id, **c.model_dump())

    if method_id not in G:
        raise HTTPException(status_code=404, detail=f"Method '{method_id}' not found in graph")

    reachable = list(nx.descendants(G, method_id))
    
    method_map = {m.id: m.model_dump() for m in result.methods}
    metrics_map = {m.method_id: m.model_dump() for m in result.metrics}

    nodes = []
    edges = []
    
    for n in [method_id] + reachable:
        if n in method_map:
            nodes.append({**method_map[n], **metrics_map.get(n, {})})
            
    subgraph = G.subgraph([method_id] + reachable)
    for u, v, data in subgraph.edges(data=True):
        edges.append(data)

    return {
        "root": method_id,
        "node_count": len(nodes),
        "nodes": nodes,
        "edges": edges,
    }


@router.get("/{project_slug}/method/{method_id:path}", response_model=MethodDetailResponse)
async def get_method_detail(
    project_slug: str,
    method_id: str,
    service: AnalysisService = Depends(get_service),
):
    """
    Return full detail for one method: its node data, metrics, and immediate callers/callees.
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    metrics_map = {m.method_id: m for m in result.metrics}

    if method_id not in method_map:
        raise HTTPException(status_code=404, detail=f"Method '{method_id}' not found")

    method = method_map[method_id]
    metrics = metrics_map.get(method_id)

    # Collect callers (edges where target == method_id)
    callers = []
    for call in result.calls:
        if call.target_id == method_id and call.source_id in method_map:
            callers.append({
                "method": method_map[call.source_id].model_dump(),
                "edge": call.model_dump(),
            })

    # Collect callees (edges where source == method_id)
    callees = []
    for call in result.calls:
        if call.source_id == method_id and call.target_id in method_map:
            callees.append({
                "method": method_map[call.target_id].model_dump(),
                "edge": call.model_dump(),
            })

    return MethodDetailResponse(
        method=method.model_dump(),
        metrics=metrics,
        callers=callers,
        callees=callees,
    )


@router.get("/{project_slug}/graph", response_model=dict)
async def export_graph(
    project_slug: str,
    format: str = Query(default="json", enum=["json", "csv"]),
    min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
    service: AnalysisService = Depends(get_service),
):
    """
    Export the full method call graph for downstream analysis (Gephi, NetworkX, etc.).
    Mirrors OSCAR's /export/{ecosystem}/graph endpoint.

    JSON format: { "project": "...", "nodes": [...], "edges": [...] }
    CSV format: source,target,call_type,confidence
    """
    result = service.load(project_slug)
    if not result:
        raise HTTPException(status_code=404, detail=f"Project '{project_slug}' not found")

    method_map = {m.id: m for m in result.methods}
    metrics_map = {m.method_id: m for m in result.metrics}

    filtered_calls = [
        c for c in result.calls
        if c.confidence >= min_confidence
        and not c.target_id.startswith("unresolved:")
        and c.source_id in method_map
        and c.target_id in method_map
    ]

    if format == "csv":
        from fastapi.responses import PlainTextResponse
        lines = ["source,target,call_type,confidence"]
        for call in filtered_calls:
            lines.append(f"{call.source_id},{call.target_id},{call.call_type},{call.confidence}")
        return PlainTextResponse("\n".join(lines), media_type="text/csv")

    nodes = [
        {**method_map[mid].model_dump(), **metrics_map[mid].model_dump()}
        for mid in method_map
        if mid in metrics_map
    ]
    edges = [c.model_dump() for c in filtered_calls]

    return {
        "project": project_slug,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
    }
