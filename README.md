# OSCAR — Dependency Graph Observatory

Graph-based observatory for analyzing transitive dependencies, systemic
risk, and structural patterns in open-source software ecosystems.

------------------------------------------------------------------------

## 📌 Overview

The **Dependency Graph Observatory** is a core module of the OSCAR
project:

> **OSCAR — Open Supply-Chain Assurance & Resilience for Cloud-Native
> Software Ecosystems**

This module focuses on constructing and analyzing **directed dependency
graphs** across software ecosystems (e.g., npm, PyPI) to identify:

-   Transitive dependency relationships
-   High-impact (central) packages
-   Fragile dependency structures
-   Systemic risk concentrations

The goal is to provide a **data-driven, graph-based foundation** for
understanding how vulnerabilities and failures can propagate across
modern software supply chains.

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
-   Initial support for:
    -   npm
    -   PyPI
-   Deterministic ingestion and normalization
-   Emphasis on **interpretable metrics**, not complex models

Future phases will extend into:

-   Code-level (method/function) dependency analysis
-   SBOM integration
-   Provenance and trust signals
-   Chaos testing for supply-chain resilience

------------------------------------------------------------------------

## 🗂️ Project Structure

```
oscar-dependency-observatory/
├── backend/
│   └── app/
│       ├── api/                # FastAPI route handlers
│       │   ├── endpoints.py    # Dependencies & package details endpoints
│       │   ├── analytics.py    # Top-risk analytics endpoint
│       │   └── exports.py      # JSON/CSV graph export endpoint
│       ├── config/
│       │   └── settings.py     # Environment-based configuration (OSCAR_ prefix)
│       ├── exporters/
│       │   └── graph_exporter.py  # JSON and CSV export logic
│       ├── graph/
│       │   ├── analytics.py    # Fan-in, fan-out, bottleneck score computation
│       │   ├── direct.py       # Direct dependency service (with auto-ingest)
│       │   └── transitive.py   # BFS transitive graph walker
│       ├── ingestion/
│       │   ├── npm.py          # npm registry connector (httpx)
│       │   └── pypi.py         # PyPI registry connector (httpx)
│       ├── models/
│       │   ├── api.py          # Pydantic API response schemas
│       │   └── domain.py       # Internal domain models (Package, Version, Edge)
│       ├── normalization/
│       │   ├── npm_normalizer.py   # npm JSON → domain model transform
│       │   └── pypi_normalizer.py  # PyPI JSON → domain model transform (PEP 508)
│       ├── storage/
│       │   └── json_storage.py # Flat-file JSON storage implementation
│       └── main.py             # FastAPI application entry point
│
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── GraphCanvas.tsx     # Cytoscape.js graph visualization
│       │   ├── Layout.tsx          # App shell with navigation
│       │   └── TopRiskTable.tsx    # Top risk analytics table
│       ├── hooks/
│       │   ├── useAnalyticsQuery.ts  # React Query hook for top-risk
│       │   ├── useGraphQuery.ts      # React Query hook for transitive graph
│       │   └── usePackageQuery.ts    # React Query hook for package details
│       ├── pages/
│       │   ├── GraphViewer.tsx    # Graph visualization page
│       │   ├── PackageSearch.tsx  # Package search & details page
│       │   └── TopRisk.tsx        # Top-risk analytics page
│       ├── services/
│       │   └── api.ts            # Axios API client
│       ├── types/
│       │   └── api.ts            # TypeScript API response interfaces
│       ├── App.tsx               # Router and app layout
│       ├── main.tsx              # React entry point
│       └── index.css             # Global styles
│
├── docs/
│   ├── technical-reference.md          # Comprehensive API & metrics reference
│   ├── backend-implementation-guide.md # Backend architecture design doc
│   ├── ui-implementation-guide.md      # Frontend architecture design doc
│   ├── ui-plan.md                      # UI component specifications
│   ├── knowledge-base/                 # Developer knowledge articles
│   └── internal/                       # Internal process & roadmap docs
│
├── CONTRIBUTING.md       # How to contribute
├── LICENSE               # MIT License
└── README.md             # This file
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

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Health check |
| `/dependencies/{ecosystem}/{package}/{version}` | GET | Direct dependencies |
| `/dependencies/{ecosystem}/{package}/{version}/transitive` | GET | Full transitive dependency graph (BFS) |
| `/packages/{ecosystem}/{package}/{version}` | GET | Package details with computed metrics |
| `/analytics/top-risk?ecosystem=npm&limit=10` | GET | Top risk packages ranked by bottleneck score |
| `/export/{ecosystem}/graph?format=json` | GET | Full graph export (JSON or CSV) |

See [docs/technical-reference.md](docs/technical-reference.md) for complete request/response schemas and metric formulas.

------------------------------------------------------------------------

## 📊 Metrics

| Metric | Formula | Interpretation |
|---|---|---|
| **Fan-In** | Count of unique packages that depend on P | How widely adopted is this package? |
| **Fan-Out** | Count of all dependency edges from P (across versions) | How many external risks does this package introduce? |
| **Bottleneck Score** | `fan_in × fan_out` | How central is this package in the dependency highway? |

> Fan-in is **deduplicated by unique package name** — if `next` appears as a dependent 113 times across versions, it counts as 1.

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
| [Technical Reference](docs/technical-reference.md) | Complete API specs, metric formulas, data model, architecture |
| [Knowledge Base](docs/knowledge-base/README.md) | Developer-friendly explanations of key concepts |
| [Backend Guide](docs/backend-implementation-guide.md) | Backend architecture design decisions |
| [UI Guide](docs/ui-implementation-guide.md) | Frontend architecture and component design |
| [Contributing](CONTRIBUTING.md) | How to set up and contribute |

------------------------------------------------------------------------

## 🔜 Roadmap

### Phase A (Current — MVP)

-   ✅ Dependency graph ingestion (npm + PyPI)
-   ✅ Graph analytics (fan-in, fan-out, bottleneck score)
-   ✅ Interactive web UI (graph viewer, package search, top risk)
-   ✅ Dataset export (JSON + CSV)
-   🔲 Unit test coverage
-   🔲 SQLite storage migration ([roadmap](docs/internal/broader-ingestion-roadmap.md))

### Phase B

-   Code-level dependency mapping (methods/classes)
-   Language-specific analysis (Java, Python)
-   Broader dataset ingestion via seed crawling

### Phase C

-   Unified multi-level graph (code + package + SBOM)
-   Advanced risk modeling (betweenness centrality, blast radius)

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
