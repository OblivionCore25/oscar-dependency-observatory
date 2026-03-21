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
    │   └── react.json          ← Package identity metadata
    ├── versions/
    │   └── react.json          ← All known versions of react
    └── edges/
        └── react.json          ← All dependency relationships for react
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
