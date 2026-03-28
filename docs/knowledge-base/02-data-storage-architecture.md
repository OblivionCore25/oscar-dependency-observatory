# Data Storage Architecture

> **Audience:** Developers wondering why there's no database setup required to run this project.

---

## Overview

The MVP backend does **not** use a traditional database (no PostgreSQL, MongoDB, or Neo4j). Instead, it uses a simple **flat-file JSON storage system** on your local filesystem.

This was a deliberate tradeoff: zero infrastructure, easy to inspect, and trivial to reset.

---

## How it's structured on disk

When data is fetched and cached, it's organized in this folder structure:

```
backend/data/
└── npm/
    ├── packages/
    │   └── react.json              ← Package identity metadata
    ├── versions/
    │   └── react.json              ← All known versions of react (array)
    └── edges/
        ├── react_18.2.0.json       ← Dependencies declared by react@18.2.0
        ├── react_18.3.1.json       ← Dependencies declared by react@18.3.1
        └── ...                     ← One file per (package, version) pair
```

Each `ecosystem` (e.g. `npm`, `pypi`) gets its own top-level folder. Inside, data is split by type: packages, versions, and edges (relationships).

---

## The three data types

| Type | What it stores | Example |
|---|---|---|
| **Package** | Identity (name + ecosystem) | `{ "name": "react", "ecosystem": "npm" }` |
| **Version** | A specific published release | `{ "version": "18.2.0", "published_at": "..." }` |
| **Edge** | A "depends on" relationship | `{ "source": "react-dom@18.2.0", "target": "react", "constraint": "^18.2.0" }` |

---

## Where this is defined in code

- **`StorageService` protocol** → `backend/app/storage/__init__.py`  
  Defines the abstract interface (what operations storage must support)

- **`JSONStorage` implementation** → `backend/app/storage/json_storage.py`  
  The concrete flat-file implementation of that interface

The rest of the app interacts only with the `StorageService` interface — meaning swapping in a real database later requires changing only the implementation, not the service layer.

---

## MVP Tradeoffs

| What we get | What we give up |
|---|---|
| Zero setup — just run the server | Slow global scans (Analytics reads every file) |
| Easy to inspect / debug | No concurrent write safety |
| Works offline after first ingest | No query language or indexing |

In a production system, `JSONStorage` would be replaced with a graph database like **Neo4j** or a relational store like **PostgreSQL**.

---

## Method Observatory: SQLite Storage

The **Method Observatory** uses a separate **SQLite database** for method-level analysis results. This is a deliberate step up from flat files because method analysis produces relational, structured data that benefits from indexing and JOIN queries.

**Location:** `data/method_observatory/method_graph.db`

**Tables:**

| Table | Contents |
|---|---|
| `analysis_runs` | One row per project analysis run (slug, timestamp, meta JSON) |
| `methods` | One row per method with id, name, module, complexity, loc |
| `calls` | One row per resolved call edge (source → target, confidence, call type) |
| `method_metrics` | One row per method with fan-in/out, centrality, blast radius, community |
| `auxiliary_data` | JSON blobs for classes, modules, imports, inheritance (for full reconstruct) |

**Key design choices:**
- `INSERT OR IGNORE` on `methods` and `method_metrics` — prevents crashes when a large package has duplicate method IDs across files
- Re-analysis of a project deletes older rows (by slug) before inserting — keeps storage clean
- The schema is initialized at startup via `CREATE TABLE IF NOT EXISTS`

**Compared to the flat-file layer:**

| | Flat-file (npm/PyPI) | SQLite (Method Observatory) |
|---|---|---|
| Setup | None | None (SQLite is stdlib) |
| Query model | Read all files and filter in Python | SQL WHERE / GROUP BY |
| Concurrent writes | Not safe | Safe (transaction-level) |
| Inspection | Open any .json in an editor | `sqlite3 data/method_observatory/method_graph.db` |

