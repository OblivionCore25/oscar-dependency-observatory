# Auto-Ingest on Read

> **Audience:** Developers wondering why they don't need to pre-load data before querying the API.

---

## What is "Auto-Ingest on Read"?

It's a design pattern where the system **automatically fetches and caches missing data** the first time you ask for it — instead of requiring you to manually populate a database beforehand.

In practice: you don't need to do anything special. Just call an endpoint with a package name, and if it's not in local storage, the backend goes and gets it for you.

---

## The Full Flow

```
Request: GET /dependencies/npm/lodash/4.17.21
                     │
                     ▼
       Check local data/ for lodash
                     │
         ┌─── Exists? ──────────────────┐
         │ NO                           │ YES
         ▼                              ▼
 Fetch from npm registry         Return from disk
 registry.npmjs.org/lodash       immediately ⚡
         │
         ▼
 Normalize raw JSON response
 → Package, Versions, Edges
         │
         ▼
 Save to local data/ folder
 (cached for all future calls)
         │
         ▼
 Return response ✅
```

---

## Where this lives in code

The logic lives inside `DirectDependencyService` in `backend/app/graph/direct.py`:

1. `get_direct_dependencies()` is called by the API endpoint
2. It calls `storage.get_versions()` to check local storage
3. If nothing is found → it calls `_ingest_npm_package()` internally
4. `_ingest_npm_package()` hits the npm registry, normalizes the data, and saves it
5. Then proceeds normally with the now-populated storage

---

## Error Scenarios

| Situation | What happens |
|---|---|
| Package doesn't exist on npm | `HTTP 404` — "Package not found on npm registry" |
| npm registry is unreachable | `HTTP 500` — "Internal server error" |
| Package exists but version not found | `HTTP 404` — "Version X not found for package Y" |

---

## Performance Note

- **First request** on a new package: slower (network round-trips to npm)
- **Subsequent requests**: instant (reads from local JSON file)
- **Transitive graph** (`/transitive` endpoint): the first call can be significantly slower for large packages like `express`, since it must recursively ingest every ancestor in the dependency tree. All of those are cached after the first run.
