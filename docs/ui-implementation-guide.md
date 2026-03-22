# OSCAR – UI Implementation Guide
## Dependency Graph Observatory (MVP)

---

## 🎯 Purpose

This document provides a structured, implementation-focused guide for building the UI layer of the Dependency Graph Observatory.  
It is designed to be:

- Easily interpretable.
- Modular and aligned with backend architecture
- Focused on execution, not speculation

---

# 1. UI Design Principles

The UI must follow these constraints:

### Core Rules
- MUST be **API-driven**
- MUST be **read-only (MVP)**
- MUST NOT contain business logic for graph computation
- MUST NOT depend on storage/database directly
- MUST remain **replaceable without backend changes**

### Responsibilities
- Render graph data
- Enable interaction (zoom, select, filter)
- Display metrics

### Non-Responsibilities
- Dependency resolution
- Graph traversal logic
- Metric computation

---

# 2. Recommended Frontend Stack

### Required
- React
- TypeScript
- Vite

### Visualization
- Cytoscape.js (primary)

### State & Data
- React Query (for API calls + caching)

### Styling
- Tailwind CSS OR CSS Modules

### Constraints
- Avoid introducing Redux unless necessary
- Avoid heavy UI frameworks (Material UI, etc.) in MVP

---

# 3. Repository Structure

## Root
```
oscar-dependency-observatory/
  backend/
  frontend/
```

## Frontend Structure
```
frontend/src/
  components/
  pages/
  services/
  hooks/
  types/
  utils/
```

### Components Folder
Reusable UI elements

### Pages Folder
Route-level components

### Services Folder
API communication

### Hooks Folder
Data-fetching and logic abstraction

### Types Folder
TypeScript interfaces

### Utils Folder
Pure helper functions

---

# 4. MVP UI Scope

### Required Pages

#### Page 1: Package Search
- Input ecosystem (Dropdown: `npm` | `pypi`)
- Input package
- Optional version

#### Page 2: Graph Viewer
- Render dependency graph
- Node selection
- Metrics display

#### Page 3: Top Risk View
- List high-risk packages
- Display metrics

### Exclusions
- No authentication
- No editing capabilities
- No real-time updates

---

# 5. Core UI Components

### GraphCanvas
- Input: nodes + edges
- Output: rendered graph
- MUST NOT compute graph logic

### GraphControls
- Layout switching
- Reset view
- Toggle options

### NodeDetailsPanel
- Displays selected node metrics

### PackageSearchForm
- Handles input and navigation

### TopRiskTable
- Displays analytical results

---

# 6. UI API Contracts

### Graph Endpoint (Transitive)
GET /dependencies/{ecosystem}/{package}/{version}/transitive

Response:
```json
{
  "root": "npm:react@18.2.0",
  "nodes": [
    { "id": "npm:react@18.2.0", "label": "react@18.2.0", "ecosystem": "npm", "package": "react", "version": "18.2.0" }
  ],
  "edges": [
    { "source": "npm:react@18.2.0", "target": "npm:loose-envify", "constraint": "^1.1.0" }
  ]
}
```

### Direct Dependencies
GET /dependencies/{ecosystem}/{package}/{version}

### Package Details
GET /packages/{ecosystem}/{package}/{version}
*(Includes `metrics` object with `fanIn`, `fanOut`, `bottleneckScore`, `diamondCount`, etc.)*

### Analytics
GET /analytics/top-risk

### Export Graph
GET /export/{ecosystem}/graph?format={json|csv}

### Constraints
- UI MUST handle `404 Not Found` and `500 Server Error` (e.g., registry down) gracefully.
- UI MUST display a loading state for the graph (initial ingest can take seconds).
- UI MUST NOT infer missing data.
- Backend MUST provide complete data.

---

# 7. Graph Visualization Strategy

### Node Representation
- Size → bottleneck score or fan-in
- Label → package name

### Node Categories
- Root
- Direct dependency
- Transitive dependency
- High-risk node

### Edge Representation
- All edges = depends_on

### Constraints
- Avoid excessive styling
- Prioritize clarity over aesthetics

---

# 8. Concrete UI Backlog

## Phase 1 – Setup
- Initialize React app
- Setup routing
- Create API client

## Phase 2 – Graph
- Implement GraphCanvas
- Connect to backend
- Add node interaction

## Phase 3 – Analytics
- Implement TopRiskTable
- Display metrics

## Phase 4 – Polish
- Add controls (including "Download Data" linking to `/export` API)
- Improve UX states (loading spinners, error banners)

---

# 9. First Implementation Tickets

### Ticket 1
Setup React + TypeScript + Vite project

### Ticket 2
Implement routing:
- /
- /graph
- /analytics

### Ticket 3
Define TypeScript types for API responses (e.g., `TransitiveDependenciesResponse`, `GraphNode`, `GraphEdge`, `PackageMetrics`, `TopRiskItem`)

### Ticket 4
Create PackageSearchForm

### Ticket 5
Render static graph (hardcoded)

### Ticket 6
Connect graph to API

### Ticket 7
Add node details panel

---

# 10. What to Avoid

DO NOT:
- Add authentication
- Add real-time features
- Add complex dashboards
- Add frontend-side graph algorithms
- Introduce unnecessary dependencies

---

# 11. Research-Facing Benefits

The UI enables:

- Visual validation of graph structures
- Identification of central nodes
- Detection of patterns (diamonds, chains)
- Improved communication of results

---

# 12. Recommended Implementation Order

1. Backend graph API available
2. Static graph visualization
3. Dynamic graph rendering
4. Node interaction
5. Analytics page
6. UI enhancements

---

## ✅ Final Note

This UI is a **supporting layer**, not the core system.

All critical logic must remain in the backend.
