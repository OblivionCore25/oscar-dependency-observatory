# API Endpoints Explained

> **Audience:** Developers familiar with REST APIs but new to dependency trees and software security concepts.

---

## 1. `GET /health` — Is the server running?

The simplest endpoint of all. You call it, the server says "I'm alive." This is standard practice in every production API — monitoring tools ping this continuously to detect outages.

```
GET http://127.0.0.1:8000/health
→ { "status": "ok" }
```

---

## 2. `GET /dependencies/{ecosystem}/{package}/{version}` — What does this package need directly?

When a developer publishes a package (like `react` on `npm` or `fastapi` on `pypi`), they list the other packages they relied upon to build it. Those are called **direct dependencies** — one level deep, no recursion.

**Analogy:** Like reading the ingredients list on the back of a food box. You see what's in it, but not what went into making each ingredient.

> **Note:** The API supports both `npm` and `pypi` via the `{ecosystem}` variable.

```
GET http://127.0.0.1:8000/dependencies/npm/react/18.2.0
```

```json
{
  "package": "react",
  "version": "18.2.0",
  "ecosystem": "npm",
  "dependencies": [
    { "name": "loose-envify", "constraint": "^1.1.0" }
  ]
}
```

---

## 3. `GET /dependencies/{ecosystem}/{package}/{version}/transitive` — What does it ACTUALLY need, all the way down?

Your app uses `react` → which needs `loose-envify` → which needs `js-tokens`. The chain keeps going many levels deep. **Transitive dependencies** are the complete family tree of everything a package needs — including what *its* dependencies need.

This endpoint walks the **entire tree** using Breadth-First Search and returns it as a graph:
- **Nodes** = individual packages at specific versions
- **Edges** = "depends on" arrows connecting them

**Why this matters for security:** A known vulnerability in `js-tokens` (3 levels deep) can still affect your app. If you can't see the full tree, you can't protect yourself.

```
GET http://127.0.0.1:8000/dependencies/npm/express/4.18.2/transitive
```

```json
{
  "root": "npm:express@4.18.2",
  "nodes": [ ... ],
  "edges": [
    { "source": "npm:express@4.18.2", "target": "npm:accepts@1.3.8", "constraint": "~1.3.8" }
  ]
}
```

---

## 4. `GET /packages/{ecosystem}/{package}/{version}` — How important is this package?

Beyond just listing dependencies, this endpoint computes **centrality metrics** for a package — its role in the broader ecosystem:

| Metric | What it means |
|---|---|
| **Fan-Out** | How many packages does *this one* depend on? High = relies heavily on others |
| **Fan-In** | How many packages in our local DB depend on *this one*? High = widely adopted |
| **Bottleneck Score** | `fan_in × fan_out`. High = a risky central intersection in the dependency highway |

**Analogy:** Think of a heavily trafficked highway interchange. Many roads lead into it and out of it. If it's compromised, traffic everywhere is disrupted.

```
GET http://127.0.0.1:8000/packages/npm/react/18.2.0
```

```json
{
  "id": "npm:react@18.2.0",
  "metrics": {
    "fanIn": 5,
    "fanOut": 1,
    "bottleneckScore": 5.0
  }
}
```

---

## 5. `GET /analytics/top-risk` — Which packages should we worry about most?

Scans **everything** in local storage and ranks packages by how many others depend on them (`fan-in`). The result is a prioritized watchlist.

**Analogy:** Finding the single bridge that 10,000 cars cross every day. If it has a structural crack (security vulnerability), the impact is enormous. Security teams use this list to know *where to look first* when a new vulnerability is disclosed.

```
GET http://127.0.0.1:8000/analytics/top-risk?ecosystem=npm&limit=5
```

```json
{
  "items": [
    {
      "name": "loose-envify",
      "fanIn": 12,
      "bottleneckScore": 12.0
    }
  ]
}
```

---

## 6. `GET /export/{ecosystem}/graph` — Give me everything!

Sometimes security researchers or data scientists just want the raw dataset to analyze in their own external tools like Pandas, Gephi, or Jupyter Notebooks.

This endpoint dumps the **entire local database** for a given ecosystem (e.g. `npm` or `pypi`) globally.

**Format Options:** 
- `?format=json` (Returns a structured `{ "nodes": [...], "edges": [...] }` payload)
- `?format=csv` (Returns a flat spreadsheet mapping `source` to `target`)

```
GET http://127.0.0.1:8000/export/pypi/graph?format=csv
```

```csv
source,target,constraint,ecosystem
pypi:fastapi@0.103.1,pypi:pydantic,>=1.7.4,pypi
pypi:fastapi@0.103.1,pypi:starlette,>=0.27.0,<0.28.0,pypi
```
