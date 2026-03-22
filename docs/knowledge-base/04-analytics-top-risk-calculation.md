# How Top-Risk Analytics Are Calculated

> **Audience:** Developers or researchers curious about the math behind `GET /analytics/top-risk`.

---

## Overview

The `top-risk` endpoint ranks packages by how structurally central they are in the dependency graph. It does this by scanning **all locally stored data** for a given ecosystem — no live registry calls are made.

The logic lives in `backend/app/graph/analytics.py` inside `AnalyticsService`.

---

## Step-by-Step Pipeline

### Step 1 — Global Scan
Two storage-level methods scan every JSON file on disk for the requested ecosystem:
- `get_all_versions(ecosystem)` → all known packages + versions
- `get_all_edges(ecosystem)` → all stored dependency relationships

> Only data that has already been ingested (auto or explicit) is included in the calculation. The score is relative to the local cache, not the entire npm/PyPI universe.

---

### Step 2 — Compute Fan-In (Deduplicated)
For every edge `A@v → B`, B's **fan-in set** gains A's package name. Multiple versions of A count as **one** unique dependent.

```
Edges in storage:
  react@18.2.0     → loose-envify
  react@18.3.1     → loose-envify
  react-dom@18.2.0 → loose-envify

Fan-in set for loose-envify: { react, react-dom }
Result:
  loose-envify.fan_in = 2  (not 3 — react counted once)
```

**What it answers:** *"How many unique packages in our dataset depend on this one?"*

A high fan-in means many distinct packages rely on this one — so if it has a vulnerability, the blast radius is large.

---

### Step 3 — Compute Fan-Out
For every edge `A → B`, A's **fan-out counter** is incremented by 1.

**What it answers:** *"How many packages does this one directly pull in?"*

A high fan-out means this package introduces many indirect risks of its own.

---

### Step 4 — Compute Bottleneck Score

```
bottleneck_score = fan_in × fan_out
```

This is a simple **degree-centrality proxy**. A package scores high if it is:
- Widely depended upon (high fan-in) **AND**
- Itself depends on many others (high fan-out)

| Package | Fan-In | Fan-Out | Bottleneck Score |
|---|---|---|---|
| `loose-envify` | 50 | 1 | 50 |
| `express` | 20 | 30 | 600 |
| `lodash` | 100 | 0 | 0 |

> `lodash` has zero dependencies itself, so despite being widely used, its bottleneck score is 0. `express` is the bigger structural risk.

---

### Step 5 — Sort and Return
All packages are sorted **descending by `bottleneck_score`**, then trimmed to the requested `limit` (default: 10).

---

## Analogy

Think of a city's road network:
- **Fan-in** = roads coming *into* an intersection
- **Fan-out** = roads going *out of* an intersection
- **Bottleneck score** = total traffic load at that intersection

The busiest intersections are the ones that, if they broke down (e.g. a critical vulnerability was disclosed), would cause the most total disruption across the network.

---

## Limitations (MVP)

- Scores are **relative to local cache** — the more packages you ingest, the more accurate the ranking becomes.
- Fan-in is **deduplicated by package name** (e.g. 113 versions of `next` depending on `styled-jsx` counts as 1). This aligns with npm's "dependents" count but means the absolute number depends on dataset breadth.
- The `bottleneck_score` formula is a naive proxy. A production system might use more sophisticated centrality algorithms (e.g. betweenness centrality via NetworkX or Neo4j).
- Diamond patterns and transitive depth are not factored into the current score.
