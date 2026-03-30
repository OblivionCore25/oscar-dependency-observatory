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
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API server starts at `http://localhost:8000`.  
Interactive Swagger docs: `http://localhost:8000/docs`

### 2. Start the Frontend (React + Vite)

```bash
cd frontend
npm install
npm run dev
```

The web UI starts at `http://localhost:5173`.

### 3. Verify

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

### 4. Run Frontend Tests

```bash
cd frontend
npx vitest run --coverage
# ≥90% branch coverage enforced by vitest.config.ts
```

------------------------------------------------------------------------

## 📡 API Endpoints

All endpoints are served from `http://localhost:8000`. Full schemas are available at `/docs`.

### System

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check — returns `{"status": "ok"}` |

---

### Package Observatory

| Endpoint | Method | Query Params | Description |
|---|---|---|---|
| `/packages/{ecosystem}/{package}/{version}` | GET | — | Package details + full metric set. Auto-ingests if not cached. |
| `/dependencies/{ecosystem}/{package}/{version}` | GET | — | Direct (immediate) dependencies |
| `/dependencies/{ecosystem}/{package}/{version}/transitive` | GET | — | Full transitive dependency graph (BFS) |
| `/analytics/top-risk` | GET | `ecosystem`, `limit` | Packages ranked by bottleneck score with percentile |
| `/analytics/coverage` | GET | `ecosystem` | Ingestion coverage vs. estimated ecosystem size |
| `/export/{ecosystem}/graph` | GET | `format=json\|csv\|graphml` | Raw graph export for downstream analysis |

**Supported ecosystems:** `npm`, `pypi`

---

### Temporal Snapshots

| Endpoint | Method | Body / Params | Description |
|---|---|---|---|
| `/snapshots/{ecosystem}` | POST | `{"description": "..."}` (optional) | Capture current graph state as a named snapshot |
| `/snapshots/{ecosystem}` | GET | — | List all snapshots for the ecosystem |
| `/snapshots/{ecosystem}/compare` | GET | `snapshot_1`, `snapshot_2` | Count added/removed edges between two snapshots |

---

### Method Observatory

| Endpoint | Method | Query Params / Body | Description |
|---|---|---|---|
| `/methods/analyze` | POST | `{package_name, package_version, exclude_tests}` | Download package from PyPI, run full AST analysis pipeline |
| `/methods/projects` | GET | — | List all analyzed project slugs |
| `/methods/{slug}` | GET | — | Analysis metadata (file count, method count, resolution rate, etc.) |
| `/methods/{slug}/graph` | GET | `format=json\|csv`, `min_confidence` | Full method call graph export |
| `/methods/{slug}/top-risk` | GET | `limit` | Methods ranked by bottleneck score (`fan_in × fan_out`) |
| `/methods/{slug}/hotspots` | GET | `limit` | Methods ranked by composite risk (`complexity × centrality × blast_radius`) |
| `/methods/{slug}/communities` | GET | — | Methods grouped by Louvain community cluster |
| `/methods/{slug}/orphans` | GET | — | Methods with `fan_in = 0` (dead code candidates) |
| `/methods/{slug}/method/{id}` | GET | — | Full method detail: metrics, callers, callees |
| `/methods/{slug}/method/{id}/blast-radius` | GET | — | Transitive callee closure subgraph for a specific method |

------------------------------------------------------------------------

## 📊 Metrics

### Package-Level Metrics

Returned by `/packages/{ecosystem}/{package}/{version}` and `/analytics/top-risk`.

| Metric | Formula / Source | Interpretation |
|---|---|---|
| **Fan-In** | Unique package *names* depending on P (deduped across versions) | How widely adopted is this package? |
| **Fan-Out** | Dependency edges from this package version | How many external risks does this package introduce? |
| **Bottleneck Score** | `fan_in × fan_out` | High = critical junction in the ecosystem graph |
| **Bottleneck Percentile** | Rank position vs. all ingested packages (0–100) | Where does this package sit in the risk distribution? |
| **PageRank** | Google PageRank (α=0.85) on the full dependency graph | Recursive importance — accounts for who depends on your dependents |
| **Betweenness Centrality** | Fraction of shortest paths between all pairs passing through P (sampled k=50) | Bridge role between sub-ecosystems |
| **Closeness Centrality** | Inverse average shortest-path distance to all reachable nodes | How quickly can a failure in P spread? |
| **Blast Radius** | `len(ancestors(G, P))` — unique packages that transitively depend on P | How many packages are exposed if P is compromised? |
| **Diamond Count** | Downstream nodes reachable via >1 distinct path | Potential version resolution conflicts |

> Fan-in is **deduplicated by package name** — react@18.0 and react@18.1 as dependents count as one unique dependent.

### Method-Level Metrics

Returned by `/methods/{slug}/hotspots`, `/methods/{slug}/graph`, and `/methods/{slug}/method/{id}`.

| Metric | Description | UI Visible? |
|---|---|---|
| **Cyclomatic Complexity** | McCabe control-flow branch count | ✅ HotspotDashboard, MethodGraphViewer panel |
| **Fan-In** | Internal callers within the project | ✅ MethodGraphViewer panel |
| **Fan-Out** | Internal callees within the project | ✅ MethodGraphViewer panel |
| **Fan-Out External** | Calls to functions outside the project | API only † |
| **Bottleneck Score** | `fan_in × fan_out` | API only (used for `/top-risk` ranking) |
| **Betweenness Centrality** | Fraction of call-graph shortest paths through this method | ✅ HotspotDashboard, MethodGraphViewer panel |
| **Blast Radius** | Transitive downstream callees affected by a change to this method | ✅ HotspotDashboard, MethodGraphViewer panel |
| **Community ID** | Louvain cluster assignment | ✅ CommunityView, MethodGraphViewer panel |
| **Composite Risk** | `complexity × betweenness_centrality × blast_radius` | ✅ HotspotDashboard (Risk Score column) |
| **PageRank** | Method-level recursive importance propagation | API only † |
| **LOC** | Physical lines of code in the method body | API only † |
| **Is Orphan** | `fan_in = 0` and not an entry point — dead code candidate | API only (via `/orphans` endpoint) † |
| **Is Leaf** | `fan_out = 0` — terminal method with no internal callees | API only † |
| **Resolution Rate** | `resolved_calls / total_calls` — confidence of static analysis | ✅ Analysis metadata |

> † *Available via REST API; UI visualization planned for v1.1.*

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

- ✅ Dependency graph ingestion (npm + PyPI)
- ✅ Graph analytics (fan-in, fan-out, bottleneck score, PageRank, betweenness, closeness, blast radius, diamond count)
- ✅ Bottleneck percentile ranking across all ingested packages
- ✅ Interactive web UI (graph viewer, package search, top risk table)
- ✅ Dataset export (JSON / CSV / GraphML)
- ✅ Temporal snapshots & edge-delta comparison

### Phase B — Method Observatory ✅

- ✅ Automated PyPI package download and extraction
- ✅ Static AST analysis pipeline (functions, classes, modules, imports, inheritance)
- ✅ Method call graph construction with confidence scoring
- ✅ Graph metrics: betweenness centrality, PageRank, Louvain communities, blast radius
- ✅ Interactive Sigma.js WebGL call graph viewer with node detail panel
- ✅ Hotspot dashboard (composite risk ranking)
- ✅ Community cluster explorer (Louvain detection)
- ✅ Orphan detection (dead code candidates)
- ✅ Per-method blast radius traversal
- ✅ SQLite persistence (`method_graph.db`)

### Phase C — Quality & Testing ✅

- ✅ Vitest + React Testing Library test suite
- ✅ ≥90% branch coverage enforced via `vitest.config.ts` thresholds
- ✅ 99%+ statement coverage across all frontend pages, components, and hooks

### Phase D — Future

- 🔲 OSV.dev vulnerability enrichment → `vuln_weighted_risk` score
- 🔲 Broader ecosystem coverage (Maven, Cargo, Go modules)
- 🔲 Scheduled automated snapshots with drift alerting
- 🔲 Cross-version method metric tracking
- 🔲 GitHub / CI integration (risk reports as PR comments)
- 🔲 Unified multi-level graph (code + package + SBOM)
- 🔲 Supply chain attack simulation via blast radius propagation

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
