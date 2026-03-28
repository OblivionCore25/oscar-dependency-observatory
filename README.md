# OSCAR — Dependency Graph Observatory

Graph-based observatory for analyzing transitive dependencies, systemic
risk, and structural patterns in open-source software ecosystems.

------------------------------------------------------------------------

## 📌 Overview

The **Dependency Graph Observatory** is a core module of the OSCAR
project:

> **OSCAR — Open Supply-Chain Assurance & Resilience for Cloud-Native
> Software Ecosystems**

This module operates at **two resolutions**:

1. **Package Level** — Constructs transitive dependency graphs across npm and PyPI ecosystems to identify high-impact packages, fragile structures, and systemic risk concentrations.
2. **Method Level** — Analyzes the internal call graph of individual Python projects via static AST analysis to surface architectural hotspots, blast radii, and community clusters within a codebase.

The goal is to provide a **data-driven, graph-based foundation** for
understanding how vulnerabilities and failures can propagate across
modern software supply chains — at both the ecosystem and code level.

------------------------------------------------------------------------

## 🧪 Research Motivation

Modern software systems depend heavily on open-source ecosystems with
deeply nested dependency chains. However, existing tools primarily focus
on:

-   Vulnerability scanning (CVE-based)
-   Static SBOM generation

There is limited capability to:

-   Model **dependency topology at scale**
-   Quantify **structural risk propagation**
-   Identify **systemic concentration risks**

This project aims to address that gap using **graph-based analysis and
reproducible datasets**.

------------------------------------------------------------------------

## 🎯 Objectives (MVP)

The initial prototype aims to:

-   Ingest dependency data from **npm and PyPI**
-   Construct **transitive dependency graphs**
-   Compute key graph-based metrics:
    -   Fan-in / Fan-out (deduplicated by unique package name)
    -   Transitive reach
    -   Diamond dependency patterns
    -   Bottleneck (centrality proxy) scores
-   Provide REST APIs for querying and exploration
-   Visualize dependency graphs via an interactive web UI
-   Export datasets for research and analysis

------------------------------------------------------------------------

## ❓ Research Questions

This work explores the following questions:

1.  Do software ecosystems exhibit **centralization patterns** that
    increase systemic risk?
2.  Can graph metrics serve as proxies for **blast radius estimation**?
3.  How prevalent are **diamond dependency structures**, and how do they
    affect failure propagation?
4.  Can dependency snapshots reveal **emerging risk concentrations over
    time**?

------------------------------------------------------------------------

## 🧠 Hypothesis

> A small subset of packages within major ecosystems exhibits
> disproportionately high centrality and downstream exposure, making
> them critical points of systemic vulnerability.

------------------------------------------------------------------------

## 🏗️ MVP Scope

To ensure feasibility and reproducibility, the MVP is intentionally
scoped:

-   Focus on **package/version-level dependency graphs**
-   Initial support for npm and PyPI
-   Deterministic ingestion and normalization
-   Emphasis on **interpretable metrics**, not complex models
-   **Method Observatory** — static AST-based call graph analysis for Python projects

Future phases will extend into:

-   SBOM integration and provenance signals
-   Chaos testing for supply-chain resilience
-   Broader ecosystem coverage (Maven, Cargo, Go modules)

------------------------------------------------------------------------

## 🗂️ Project Structure

```
oscar-dependency-observatory/
├── backend/
│   └── app/
│       ├── api/                     # Package-level FastAPI route handlers
│       ├── config/settings.py       # Environment-based configuration (OSCAR_ prefix)
│       ├── exporters/               # JSON/CSV graph export logic
│       ├── graph/                   # Fan-in, fan-out, bottleneck, BFS services
│       ├── ingestion/               # npm + PyPI registry connectors (httpx)
│       ├── models/                  # Pydantic domain + API schemas
│       ├── normalization/           # Registry-specific data normalizers
│       ├── storage/                 # JSON flat-file storage implementation
│       ├── method_observatory/      # ★ Method-level analysis subsystem
│       │   ├── api/router.py        # 10 REST endpoints under /methods
│       │   ├── analysis/            # AST visitor, call resolver, graph builder,
│       │   │                        #   symbol table, complexity, scope tracker
│       │   ├── ingestion/           # Python file scanner + AST parser
│       │   ├── metrics/             # Fan-in/out, centrality, Louvain, blast radius
│       │   ├── models/              # MethodNode, CallEdge, AnalysisResult
│       │   ├── services/            # AnalysisService (orchestrates full pipeline)
│       │   └── storage/             # SQLite persistence (method_graph.db)
│       └── main.py                  # FastAPI entry point — mounts 4 routers
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── GraphCanvas.tsx      # Cytoscape.js — package dependency graphs
│       │   ├── MethodCallGraph.tsx  # Sigma.js v3 WebGL — method call graphs
│       │   ├── Layout.tsx           # App shell with sidebar navigation
│       │   └── TopRiskTable.tsx     # Risk ranking table
│       ├── hooks/                   # React Query hooks (graph, analytics, package)
│       ├── pages/
│       │   ├── PackageSearch.tsx    # Package search & ingestion
│       │   ├── GraphViewer.tsx      # Package dependency visualization
│       │   ├── TopRisk.tsx          # Ecosystem risk + Method Hotspots tabs
│       │   ├── MethodExplorer.tsx   # Browse analyzed Python projects
│       │   ├── MethodGraphViewer.tsx # Method call graph + detail panel
│       │   ├── HotspotDashboard.tsx # Composite method risk table
│       │   └── CommunityView.tsx    # Louvain cluster explorer
│       ├── services/api.ts          # Axios API client
│       ├── types/                   # TypeScript interfaces
│       ├── App.tsx                  # Router — 7 routes
│       └── main.tsx                 # React entry point
│
├── data/
│   ├── npm/                         # Package-level flat-file data
│   ├── pypi/
│   └── method_observatory/
│       └── method_graph.db          # SQLite database for method analysis
│
├── docs/
│   ├── technical-reference.md       # Complete API, metrics, and architecture reference
│   ├── knowledge-base/              # Developer-friendly concept explanations
│   └── internal/                    # Internal design docs and roadmaps
│
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

------------------------------------------------------------------------

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+

### 1. Start the Backend (FastAPI)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn pydantic pydantic-settings httpx
uvicorn app.main:app --reload
```

The API server starts at `http://localhost:8000`. Swagger docs are available at `http://localhost:8000/docs`.

### 2. Start the Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

The web UI starts at `http://localhost:5173` and proxies API calls to the backend automatically.

### 3. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

------------------------------------------------------------------------

## 📡 API Endpoints

### Package Level

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/dependencies/{ecosystem}/{package}/{version}` | GET | Direct dependencies |
| `/dependencies/{ecosystem}/{package}/{version}/transitive` | GET | Full transitive dependency graph (BFS) |
| `/packages/{ecosystem}/{package}/{version}` | GET | Package details with computed metrics |
| `/analytics/top-risk` | GET | Top risk packages ranked by bottleneck score |
| `/export/{ecosystem}/graph` | GET | Full graph export (JSON or CSV) |

### Method Observatory

| Endpoint | Method | Description |
|---|---|---|
| `/methods/analyze` | POST | Analyze a Python project directory |
| `/methods/projects` | GET | List all analyzed projects |
| `/methods/{slug}` | GET | Analysis metadata for a project |
| `/methods/{slug}/graph` | GET | Full method call graph export (JSON or CSV) |
| `/methods/{slug}/top-risk` | GET | Methods ranked by bottleneck score |
| `/methods/{slug}/hotspots` | GET | Methods ranked by composite risk (complexity × centrality × blast radius) |
| `/methods/{slug}/communities` | GET | Methods grouped by Louvain community |
| `/methods/{slug}/orphans` | GET | Uncalled methods (dead code candidates) |
| `/methods/{slug}/method/{id}/blast-radius` | GET | Transitive downstream callee closure |
| `/methods/{slug}/method/{id}` | GET | Full method detail (callers, callees, metrics) |

See [docs/technical-reference.md](docs/technical-reference.md) for complete request/response schemas and metric formulas.

------------------------------------------------------------------------

## 📊 Metrics

### Package Level

| Metric | Formula | Interpretation |
|---|---|---|
| **Fan-In** | Unique packages depending on P | How widely adopted? |
| **Fan-Out** | Dependency edges from all versions of P | How many external risks introduced? |
| **Bottleneck Score** | `fan_in × fan_out` | Centrality proxy — high = critical junction |

> Fan-in is **deduplicated by package name** — multiple versions of the same dependent count as 1.

### Method Level

| Metric | Description |
|---|---|
| **Complexity** | Cyclomatic complexity (control-flow branches) |
| **Betweenness Centrality** | Fraction of call-graph shortest paths through this method |
| **Blast Radius** | Transitive downstream methods affected if this one changes |
| **Community ID** | Louvain cluster — methods that call each other frequently |
| **Composite Risk** | `complexity × centrality × blast_radius` (used by Hotspots) |

------------------------------------------------------------------------

## 📦 Dataset Outputs

The observatory produces:

-   Dependency graph datasets (JSON / CSV) via the export endpoint
-   Snapshot-based graph states (planned)
-   Derived metrics for analysis

These datasets are intended for:

-   Research experiments
-   Visualization (Gephi, NetworkX, Jupyter)
-   Risk modeling

------------------------------------------------------------------------

## 📚 Documentation

| Document | Description |
|---|---|
| [Technical Reference](docs/technical-reference.md) | Complete API specs, metric formulas, data models, architecture |
| [Knowledge Base](docs/knowledge-base/README.md) | Developer-friendly explanations of key concepts |
| [Method Observatory API Guide](docs/knowledge-base/postman-testing-guide-method-observatory.md) | Postman/curl testing guide for Method Observatory endpoints |
| [Contributing](CONTRIBUTING.md) | How to set up and contribute |

------------------------------------------------------------------------

## 🔜 Roadmap

### Phase A — Package Observatory ✅

-   ✅ Dependency graph ingestion (npm + PyPI)
-   ✅ Graph analytics (fan-in, fan-out, bottleneck score)
-   ✅ Interactive web UI (graph viewer, package search, top risk)
-   ✅ Dataset export (JSON + CSV)

### Phase B — Method Observatory ✅

-   ✅ Static AST analysis pipeline for Python projects
-   ✅ Method call graph construction + resolution
-   ✅ Graph metrics: centrality, PageRank, Louvain communities, blast radius
-   ✅ Interactive Sigma.js WebGL call graph viewer
-   ✅ Hotspot dashboard (composite risk ranking)
-   ✅ Community cluster exploration
-   ✅ SQLite storage for method analysis results

### Phase C — Future

-   🔲 Broader ecosystem coverage (Maven, Cargo, Go modules)
-   🔲 Unified multi-level graph (code + package + SBOM)
-   🔲 Temporal snapshots and risk drift detection
-   🔲 CI/CD integration for continuous analysis

------------------------------------------------------------------------

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and guidelines.

This repository is an **early-stage working prototype** intended to
facilitate collaboration and research discussion.

> ⚠️ The architecture, scope, and implementation are expected to evolve.

Feedback is highly encouraged, especially on:

-   Research direction
-   Metric definitions
-   Data modeling
-   Ecosystem coverage

------------------------------------------------------------------------

## 📄 License

This project is licensed under the [MIT License](LICENSE).

------------------------------------------------------------------------

## 👤 Author

Fabian Gonzalez  
Software Engineer | Distributed Systems | Cloud Infrastructure

------------------------------------------------------------------------

## 🌐 Related Work (to be expanded)

-   Software dependency networks research
-   Supply-chain security (Log4j, SolarWinds)
-   Graph-based risk analysis
-   SBOM standards (SPDX, CycloneDX)
