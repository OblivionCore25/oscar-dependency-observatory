# OSCAR — Dependency Graph Observatory

This repository is a core backend module of the broader **OSCAR** project:
> **OSCAR — Open Supply-Chain Assurance & Resilience for Cloud-Native Software Ecosystems**

## 🌐 The OSCAR Architecture

The OSCAR ecosystem is decoupled into three standalone repositories that work together to form a comprehensive supply-chain and risk intelligence platform:

1. **`oscar-dependency-observatory` (This Repository):** Analyzes macro-level transitive dependencies between packages (e.g., npm and PyPI) across entire software ecosystems.
2. **`oscar-method-observatory`:** Analyzes micro-level, internal source code topologies, resolving deep function-to-function abstract syntax trees and structural risks.
3. **`oscar-frontend`:** The unified React/Vite UI that bridges both backends into an interactive dashboard, visualizer, and method explorer.

---

## 📌 Overview

The **Dependency Graph Observatory** constructs and analyzes **directed dependency graphs** across major ecosystems to identify:

- Transitive dependency relationships
- High-impact (central) packages
- Fragile dependency structures
- Systemic risk concentrations

The goal is to provide a **data-driven, graph-based foundation** for understanding how vulnerabilities and failures can propagate across modern software supply chains.

---

## 🎯 Objectives (MVP)

- Ingest dependency data from **npm and PyPI**
- Construct **transitive dependency graphs**
- Compute key graph-based metrics:
  - Fan-in / Fan-out (deduplicated by unique package name)
  - Transitive reach
  - Bottleneck (centrality proxy) scores
- Provide REST APIs for querying and exploration by the OSCAR frontend

---

## 🗂️ Project Structure

This project is a standalone Python FastAPI backend. The structure is as follows:

```
oscar-dependency-observatory/
├── app/
│   ├── api/                # FastAPI route handlers
│   ├── config/             # Environment-based configuration
│   ├── exporters/          # JSON and CSV export logic
│   ├── graph/              # Transitive graph walkers and analytics
│   ├── ingestion/          # npm and PyPI registry connectors (httpx)
│   ├── models/             # Domain and pydantic API models
│   ├── normalization/      # Registry JSON transforms (PEP 508 parsing)
│   ├── storage/            # Flat-file JSON internal storage
│   └── main.py             # FastAPI application entry point
├── data/                   # Default storage path for ingested metadata
├── docs/                   # Internal backend architectural guides
├── tests/                  # Pytest automated test suites
├── requirements.txt        # Production dependencies
└── requirements-dev.txt    # Development dependencies
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- Virtual Environment

### Start the Backend Server

```bash
# 1. Create a virtual environment and source it
python3 -m venv .venv
source .venv/bin/activate

# 2. Install requirements
pip install -r requirements.txt

# 3. Start the FastAPI Uvicorn Server
uvicorn app.main:app --port 8000 --reload
```

The API server will start on `http://localhost:8000`. 
Interactive documentation (Swagger UI) is automatically available at `http://localhost:8000/docs`.

### Verify the Service

```bash
curl http://localhost:8000/health
# → {"status":"ok","service":"oscar-dependency-observatory"}
```

Before utilizing the frontend application, ensure this backend is running on `port 8000`.

---

## 🏗️ Core Metrics

| Metric | Formula | Interpretation |
|---|---|---|
| **Fan-In** | Count of unique packages that depend on P | How widely adopted is this package? |
| **Fan-Out** | Count of all dependency edges from P | How many external risks does this package introduce? |
| **Bottleneck Score** | `fan_in × fan_out` | How central is this package in the dependency highway? |

---

## 📄 License
This project is licensed under the [MIT License](LICENSE).
