# API Testing Guide: OSCAR Dependency Graph Observatory

This guide provides step-by-step instructions on how to test the MVP backend API endpoints using a REST client (like Postman, Insomnia, or cURL).

## Prerequisites

Before testing, ensure the FastAPI server is running locally:

```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload
```
The server will be available at `http://127.0.0.1:8000`.

---

## 1. Health Check
Verify the server is actively listening.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/health`
- **Expected Status**: `200 OK`
- **Expected Output**:
```json
{
  "status": "ok"
}
```

---

## 2. Direct Dependencies Endpoint
Retrieves the immediate dependencies of a specific package version. If the package has not been ingested yet, the backend will gracefully auto-ingest it.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/dependencies/npm/react/18.2.0`
- **Inputs**:
  - `ecosystem`: `npm`
  - `package`: `react` (or scoped like `@types/node`)
  - `version`: `18.2.0`
- **Expected Status**: `200 OK`
- **Expected Output**:
```json
{
  "package": "react",
  "version": "18.2.0",
  "ecosystem": "npm",
  "dependencies": [
    {
      "name": "loose-envify",
      "constraint": "^1.1.0"
    }
  ]
}
```

---

## 3. Transitive Graph Endpoint
Retrieves the full transitive dependency graph using Breadth-First Search. This will trigger auto-ingestion for all unexplored descendant elements.
*(Warning: The first request on a deep package might take a few seconds due to recursive NPM HTTP lookups. Subsequent runs will be instant from local JSON storage).*

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/dependencies/npm/express/4.18.2/transitive`
- **Inputs**:
  - `ecosystem`: `npm`
  - `package`: `express` 
  - `version`: `4.18.2`
- **Expected Status**: `200 OK`
- **Expected Output** (Truncated for brevity):
```json
{
  "root": "npm:express@4.18.2",
  "nodes": [
    {
      "id": "npm:express@4.18.2",
      "label": "express@4.18.2",
      "ecosystem": "npm",
      "package": "express",
      "version": "4.18.2"
    },
    {
      "id": "npm:accepts@1.3.8",
      "label": "accepts@1.3.8",
      ...
    }
  ],
  "edges": [
    {
      "source": "npm:express@4.18.2",
      "target": "npm:accepts@1.3.8",
      "constraint": "~1.3.8"
    }
  ]
}
```

---

## 4. Package Details (with Fan-In / Fan-Out Centrality)
Retrieves the basic metadata and analytic computations for a specific queried package version based on the *current known storage state*.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/packages/npm/react/18.2.0`
- **Inputs**:
  - `ecosystem`: `npm`
  - `package`: `react`
  - `version`: `18.2.0`
- **Expected Status**: `200 OK`
- **Expected Output**:
*(FanIn and Bottleneck scores will vary dynamically based on how many other packages in your local storage rely on `react`)*

```json
{
  "id": "npm:react@18.2.0",
  "ecosystem": "npm",
  "name": "react",
  "version": "18.2.0",
  "metrics": {
    "directDependencies": 1,
    "transitiveDependencies": 0,
    "fanIn": 0,   // Number of ingested packages that consider this a dependency
    "fanOut": 1, 
    "bottleneckScore": 0.0,
    "diamondCount": 0
  }
}
```

---

## 5. Analytics Top-Risk Endpoint
Returns a globally computed array estimating the most trusted natively queried dependencies (highest Fan-In) across your entire system.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/analytics/top-risk?ecosystem=npm&limit=5`
- **Inputs** (Query Parameters):
  - `ecosystem`: `npm` (default)
  - `limit`: `5` (default: 10)
- **Expected Status**: `200 OK`
- **Expected Output**:
```json
{
  "items": [
    {
      "id": "npm:loose-envify@1.4.0",
      "ecosystem": "npm",
      "name": "loose-envify",
      "version": "1.4.0",
      "fanIn": 2, // 2 different packages in your local DB depend on loose-envify
      "fanOut": 0,
      "bottleneckScore": 2.0
    }
  ]
}
```

## 6. Graph Export Endpoint (JSON)
Exports the entire local dependency graph for an ecosystem as a structured JSON payload. Useful for external analysis tools or research pipelines.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/export/npm/graph?format=json`
- **Inputs** (Path + Query Parameters):
  - `ecosystem`: `npm` or `pypi`
  - `format`: `json` (default)
- **Expected Status**: `200 OK`
- **Expected Output**:
```json
{
  "ecosystem": "npm",
  "nodes": [
    { "id": "npm:react@18.2.0", "ecosystem": "npm", "package": "react", "version": "18.2.0" }
  ],
  "edges": [
    { "source": "npm:react@18.2.0", "target": "npm:loose-envify", "constraint": "^1.1.0" }
  ]
}
```

---

## 7. Graph Export Endpoint (CSV)
Same as above, but returns a flat CSV edge-list suitable for import into Gephi, Pandas, or R for network analysis.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/export/pypi/graph?format=csv`
- **Inputs** (Path + Query Parameters):
  - `ecosystem`: `npm` or `pypi`
  - `format`: `csv`
- **Expected Status**: `200 OK`
- **Content-Type**: `text/csv`
- **Expected Output**:
```csv
source,target,constraint,ecosystem
pypi:fastapi@0.103.1,pypi:pydantic,>=1.7.4,pypi
pypi:fastapi@0.103.1,pypi:starlette,>=0.27.0,pypi
```

> **Note:** The CSV export only lists relationships (edges). To get node metadata, use the JSON format instead.

---

## 8. PyPI Ecosystem — Direct Dependencies
All dependency endpoints work with `pypi` as the ecosystem, not just `npm`. The backend auto-ingests by calling `pypi.org` on first request.

- **Method**: `GET`
- **URL**: `http://127.0.0.1:8000/dependencies/pypi/fastapi/0.103.1`
- **Inputs**:
  - `ecosystem`: `pypi`
  - `package`: `fastapi`
  - `version`: `0.103.1`
- **Expected Status**: `200 OK`
- **Expected Output**:
```json
{
  "package": "fastapi",
  "version": "0.103.1",
  "ecosystem": "pypi",
  "dependencies": [
    { "name": "pydantic", "constraint": "!=1.8,!=1.8.1,<3.0.0,>=1.7.4" },
    { "name": "starlette", "constraint": ">=0.27.0,<0.28.0" },
    { "name": "typing-extensions", "constraint": ">=4.5.0" }
  ]
}
```

> **Note:** Test and dev-only dependencies (e.g. `pytest`) are automatically filtered out by the PyPI normalizer.

---

## Troubleshooting
- **`404 Not Found`**: The requested package doesn't exist on the npm or PyPI public registry, or you made a typo.
- **`400 Bad Request`**: An unsupported ecosystem (e.g. `cargo`) or unsupported export format (e.g. `xml`) was requested.
- **`500 Internal Server Error`**: Usually implies a network failure while contacting `registry.npmjs.org` or `pypi.org` during auto-ingestion. Ensure your internet connection is active.
