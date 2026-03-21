# OSCAR – Backend Implementation Guide
## Dependency Graph Observatory (MVP)

---

## 🎯 Purpose

This document provides a structured, implementation-focused guide for building the backend of the Dependency Graph Observatory.

It is designed to be:

- Easily interpretable.
- Modular and aligned with a research-oriented architecture
- Focused on execution, reproducibility, and future extensibility

The backend is the core system responsible for ingesting dependency data, normalizing it, constructing graph representations, computing metrics, and exposing stable APIs for downstream consumers such as the UI, notebooks, and dataset exporters.

---

# 1. Backend Purpose

The backend MUST provide the following core capabilities:

- Ingest package metadata from supported ecosystems
- Normalize dependency information into a unified internal model
- Construct directed dependency graphs
- Support graph traversal and structural analysis
- Compute interpretable risk metrics
- Expose stable APIs for graph exploration and analytics
- Export data for research, reproducibility, and downstream analysis

### Primary Outcome
A working backend that can answer:

- What are the direct dependencies of a package/version?
- What are the transitive dependencies of a package/version?
- Which packages have high downstream exposure?
- Which packages appear structurally central or risky?
- Where do diamond dependency patterns exist?
- How can graph data be exported for research use?

---

# 2. Design Principles

The backend MUST follow these constraints:

### Core Rules
- MUST be modular
- MUST be deterministic where possible
- MUST separate ingestion, graph construction, analytics, and API concerns
- MUST expose stable interfaces to consumers
- MUST support reproducible data generation
- MUST keep critical logic in backend services, not in clients

### Architectural Principles
- Prefer simple, explicit pipelines over early over-engineering
- Prefer vertical slices that work end-to-end
- Treat the storage layer as an implementation detail, not the domain model
- Keep ecosystem-specific logic isolated from core graph logic
- Keep graph analytics isolated from API presentation logic

### Non-Goals (MVP)
- No workflow orchestration platform required initially
- No event-driven architecture required initially
- No multi-service decomposition required initially
- No full production-grade scaling work required initially

---

# 3. Suggested Backend Stack

## Core Language
Choose one of the following:

### Recommended for fastest MVP
- Python

### Alternative
- Go

### Recommendation
Use Python for the MVP because it optimizes for:
- speed of experimentation
- research workflows
- simple integration with notebooks and data tooling
- lower friction for building ingestion + analytics quickly

---

## API Layer
- FastAPI

## Data Validation / Models
- Pydantic

## Storage (MVP)
Choose one of the following:

### Fastest initial option
- JSON files OR SQLite

### Better structured MVP option
- PostgreSQL

## Graph / Analytics
### Initial MVP
- In-memory graph structures
- NetworkX optional for analysis support

### Later upgrade
- Neo4j
- graph database layer
- advanced graph algorithms

## Background / Batch
### MVP
- Simple scripts or internal jobs

### Later
- Celery / RQ / Temporal only if clearly needed

## Containerization
- Docker

---

# 4. Suggested Repository Structure

## Root
```text
oscar-dependency-observatory/
  backend/
  frontend/
  docs/
  scripts/
  data/
  notebooks/
```

## Backend Structure
```text
backend/
  app/
    api/
    ingestion/
    normalization/
    graph/
    analytics/
    storage/
    exporters/
    models/
    config/
    utils/
    main.py
```

### Folder Responsibilities

#### api/
- Route definitions
- Request/response DTOs
- API dependency wiring

#### ingestion/
- Registry connectors
- Ecosystem-specific fetch logic
- Raw metadata retrieval

#### normalization/
- Transform raw registry responses
- Convert ecosystem-specific structures into unified internal models

#### graph/
- Build graph structures
- Traverse direct and transitive dependencies
- Reverse dependency mappings

#### analytics/
- Compute fan-in
- Compute fan-out
- Compute bottleneck proxies
- Detect diamond patterns

#### storage/
- Read/write persistence logic
- Abstract storage implementation

#### exporters/
- JSON export
- CSV export
- snapshot export

#### models/
- Internal domain models
- API models
- shared schemas

#### config/
- environment settings
- constants
- application configuration

#### utils/
- pure helper functions
- shared generic utilities

---

# 5. MVP Scope

The MVP backend MUST support the following:

## Ecosystems
- npm
- PyPI (after npm is working end-to-end)

## Graph Level
- package/version dependency graph only

## Required Capabilities
- ingest package metadata
- parse direct dependencies
- recursively build transitive dependency graph
- store normalized data
- expose graph retrieval APIs
- compute core structural metrics
- export graph data

## Explicit Exclusions
- code-level method/function dependency mapping
- SBOM ingestion
- provenance analysis
- chaos testing
- cross-ecosystem unified risk scoring beyond simple normalized metrics
- real-time streaming pipelines

---

# 6. Core Backend Components

## 6.1 Registry Connector
Responsible for:
- calling external package registries
- retrieving package metadata
- handling ecosystem-specific formats

Example:
- npm registry connector
- PyPI connector

Constraint:
- MUST isolate registry-specific logic from the rest of the system

---

## 6.2 Normalization Layer
Responsible for:
- converting raw metadata into unified internal structures
- standardizing package/version identifiers
- standardizing dependency edges

Example normalized package ID:
```text
npm:react@18.2.0
```

Constraint:
- MUST produce deterministic normalized outputs for the same input

---

## 6.3 Graph Builder
Responsible for:
- building nodes and edges
- constructing dependency DAGs/graphs
- supporting direct and transitive traversal
- supporting reverse dependency lookup

Constraint:
- MUST remain independent from visualization concerns

---

## 6.4 Analytics Engine
Responsible for:
- fan-in
- fan-out
- transitive dependency count
- bottleneck score
- diamond dependency detection

Constraint:
- MUST expose metrics as backend outputs, not frontend-derived values

---

## 6.5 Storage Layer
Responsible for:
- raw metadata persistence
- normalized graph persistence
- snapshot storage
- reloading data for analysis

Constraint:
- MUST be abstracted behind clear interfaces

---

## 6.6 Export Layer
Responsible for:
- JSON export
- CSV export
- snapshot output for reproducibility

---

## 6.7 API Layer
Responsible for:
- serving graph data
- serving package details
- serving analytics results
- returning stable response contracts

---

# 7. Data Model (Minimum)

The MVP SHOULD define the following core entities:

## Package
Fields:
- ecosystem
- name

## Version
Fields:
- package_name
- ecosystem
- version
- published_at (optional if available)

## DependencyEdge
Fields:
- source_package
- source_version
- target_package
- version_constraint
- resolved_target_version (optional)
- dependency_type (optional)
- ingestion_timestamp

## Snapshot
Fields:
- snapshot_id
- created_at
- ecosystem
- description (optional)

---

# 8. API Contracts

The backend SHOULD expose the following APIs.

## 8.1 Health Check
```http
GET /health
```

Response:
```json
{
  "status": "ok"
}
```

---

## 8.2 Ingest Package
```http
POST /ingest/{ecosystem}/{package}
```

Optional query params:
- version
- depth

Response:
```json
{
  "status": "accepted",
  "ecosystem": "npm",
  "package": "react",
  "version": "18.2.0"
}
```

---

## 8.3 Get Direct Dependencies
```http
GET /dependencies/{ecosystem}/{package}/{version}
```

Response:
```json
{
  "package": "react",
  "version": "18.2.0",
  "dependencies": [
    {
      "name": "loose-envify",
      "constraint": "^1.1.0"
    }
  ]
}
```

---

## 8.4 Get Transitive Dependencies
```http
GET /dependencies/{ecosystem}/{package}/{version}/transitive
```

Response:
```json
{
  "root": "npm:react@18.2.0",
  "nodes": [],
  "edges": []
}
```

---

## 8.5 Get Package Details
```http
GET /packages/{ecosystem}/{package}/{version}
```

Response:
```json
{
  "id": "npm:react@18.2.0",
  "ecosystem": "npm",
  "name": "react",
  "version": "18.2.0",
  "metrics": {
    "directDependencies": 3,
    "transitiveDependencies": 12,
    "fanIn": 3500,
    "fanOut": 12,
    "bottleneckScore": 8.2,
    "diamondCount": 1
  }
}
```

---

## 8.6 Get Top Risk Packages
```http
GET /analytics/top-risk?ecosystem=npm&limit=20
```

Response:
```json
{
  "items": [
    {
      "id": "npm:example@1.0.0",
      "ecosystem": "npm",
      "name": "example",
      "version": "1.0.0",
      "fanIn": 999,
      "fanOut": 55,
      "bottleneckScore": 10.4
    }
  ]
}
```

---

## 8.7 Export Graph Dataset
```http
GET /export/{ecosystem}/graph?format=json
```

Supported formats:
- json
- csv

Constraint:
- backend MUST return fully prepared export data
- clients MUST NOT reconstruct exports

---

# 9. Concrete Backend Backlog

## Phase 1 – Foundation
- Initialize backend project
- Setup FastAPI
- Define domain models
- Define normalized schema
- Implement config and environment loading

## Phase 2 – npm Ingestion
- Implement npm registry connector
- Parse raw metadata
- Normalize package/version/dependency records
- Persist raw and normalized outputs

## Phase 3 – Graph Construction
- Build in-memory graph model
- Support direct dependency lookup
- Support transitive traversal
- Build reverse dependency map

## Phase 4 – Analytics
- Implement direct dependency count
- Implement transitive dependency count
- Implement fan-in
- Implement fan-out
- Implement bottleneck score
- Implement diamond detection

## Phase 5 – API
- Implement dependency endpoints
- Implement package detail endpoint
- Implement analytics endpoint
- Implement export endpoint

## Phase 6 – Persistence Improvement
- Move from file-based storage to SQLite/PostgreSQL if needed
- Add snapshot support
- Improve reload/reuse of prior ingestions

## Phase 7 – PyPI Support
- Implement PyPI connector
- Normalize to same schema
- Reuse existing graph/analytics pipeline

---

# 10. Exact First Implementation Tickets

## Ticket 1
Initialize backend project structure

Deliverables:
- backend/app/ folders created
- dependency management initialized
- FastAPI app boots locally

---

## Ticket 2
Implement `/health` endpoint

Deliverables:
- health route available
- local server confirms running state

---

## Ticket 3
Define normalized domain models

Deliverables:
- Package model
- Version model
- DependencyEdge model
- API response schemas

---

## Ticket 4
Implement npm registry connector

Deliverables:
- fetch raw metadata from npm registry
- handle package lookup errors
- return raw JSON response safely

---

## Ticket 5
Implement normalization for npm metadata

Deliverables:
- convert raw npm package metadata into normalized records
- standard package/version IDs generated

---

## Ticket 6
Persist normalized outputs

Deliverables:
- file-based or SQLite storage
- package graph data can be saved and reloaded

---

## Ticket 7
Build direct dependency query service

Deliverables:
- retrieve direct dependencies for package/version
- service layer separated from API route

---

## Ticket 8
Build transitive traversal service

Deliverables:
- BFS or DFS traversal
- return nodes + edges structure

---

## Ticket 9
Implement fan-out metric

Deliverables:
- direct + transitive dependency counts available

---

## Ticket 10
Implement reverse graph and fan-in metric

Deliverables:
- reverse dependency lookup
- dependent counts available

---

## Ticket 11
Implement bottleneck score

Suggested MVP formula:
```text
score = fan_in * log(transitive_dependents + 1)
```

Deliverables:
- bottleneck score computed per node

---

## Ticket 12
Implement diamond dependency detection

Deliverables:
- detect repeated convergence pattern
- count diamond structures for selected root graph

---

## Ticket 13
Expose dependency APIs

Deliverables:
- `/dependencies/...`
- `/packages/...`
- `/analytics/top-risk`

---

## Ticket 14
Implement graph export

Deliverables:
- JSON export
- CSV edge list export

---

## Ticket 15
Add PyPI connector

Deliverables:
- second ecosystem supported
- shared normalization reused

---

# 11. Recommended Implementation Order

The implementation SHOULD follow this order:

1. backend scaffold
2. health endpoint
3. domain models
4. npm connector
5. normalization
6. persistence
7. direct dependency service
8. transitive traversal
9. fan-out
10. reverse graph / fan-in
11. bottleneck score
12. diamond detection
13. API routes
14. export layer
15. PyPI support

### Rationale
This order minimizes risk and ensures:
- working vertical slices early
- rapid validation of data model decisions
- low coupling between components
- easier debugging and iteration

---

# 12. What to Avoid in the Backend MVP

DO NOT:
- build microservices too early
- introduce message queues prematurely
- over-optimize for scale before correctness
- mix registry-specific parsing into core graph logic
- place analytics logic in API handlers
- make frontend responsible for metric derivation
- attempt code-level dependency mapping in the first backend MVP
- attempt all ecosystems at once

---

# 13. Testing Strategy

The backend SHOULD include the following test types:

## Unit Tests
- normalization functions
- graph traversal functions
- metric computations

## Integration Tests
- npm connector
- storage read/write
- API route responses

## Snapshot / Fixture Tests
- fixed package inputs
- stable expected normalized outputs

Constraint:
- tests SHOULD prefer deterministic fixtures where possible

---

# 14. Observability and Logging

The MVP SHOULD include minimal operational visibility:

- structured logs for ingestion start/end
- warning logs for missing or malformed dependency data
- error logs for failed registry calls
- basic timing logs for ingestion/traversal

This is useful even in a research MVP because it improves reproducibility and debugging.

---

# 15. Suggested Missing Items to Include

The following items are useful additions beyond the requested sections:

## 15.1 Data Validation Rules
Define:
- required fields
- version parsing expectations
- null handling rules
- unsupported dependency format handling

## 15.2 Error Handling Policy
Define:
- how API errors are returned
- how partial ingestion failures are reported
- how missing versions are handled

## 15.3 Snapshot Strategy
Even if simple, define:
- when snapshots are created
- how they are named
- how they support reproducibility

## 15.4 Configuration Strategy
Define:
- registry base URLs
- storage mode
- ingestion depth defaults
- timeout/retry values

These items reduce ambiguity and make the backend much easier to implement consistently.

---

# 16. Final Note

This backend is the core of the Dependency Graph Observatory.

The backend MUST remain the authoritative source for:
- dependency data
- graph structure
- structural metrics
- exported research artifacts

All clients, including the UI, notebooks, and future modules, should depend on stable backend outputs rather than re-implementing backend logic.
