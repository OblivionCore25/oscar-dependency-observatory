# OSCAR Method Observatory — Postman Testing Guide

This guide explains how to structurally test the newly implemented OSCAR Method Observatory REST API using a standard API tester like Postman. By default, the backend local server runs at `http://127.0.0.1:8000`.

## 1. Trigger an Analysis
The very first step is to tell the server to locally extract the AST logic from the project. You can test this out by pointing the analyzer at the `backend/` directory of your own repository!

- **Method:** `POST`
- **URL:** `http://127.0.0.1:8000/methods/analyze`
- **Headers:** `Content-Type: application/json`
- **Body (`raw` / `JSON`):**
  ```json
  {
    "project_path": "/Users/fabiangonzalez/Documents/oscar-dependency-observatory/oscar-dependency-observatory/backend",
    "project_slug": "oscar-backend",
    "exclude_tests": false
  }
  ```
- **Expected Success (200 OK):** The JSON response contains the project analysis statistics, saving `.json` flat files into your `data/method_observatory/oscar-backend/` workspace.

---

## 2. List Analyzed Projects
After you scan the application via the `/analyze` POST request, fetch all the project schemas properly saved to disk.

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/projects`
- **Expected Success (200 OK):** Returning a JSON array string: `["oscar-backend"]`.

---

## 3. Get Project Metadata Summary
Retrieve high-level complexity and extraction statistics matching what was created on the initial run.

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/oscar-backend`
- **Expected Success (200 OK):** A standard outline of analysis operations (`resolution_rate`, `unresolved_call_count`, `method_count`, etc.).

---

## 4. Get Top Risk Methods
Retrieve the most critical graph hub components within the codebase, graded dynamically by bottleneck score (`fan-in` multiply `fan-out`). 

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/oscar-backend/top-risk?limit=5`
- **Expected Success (200 OK):** A JSON array outlining the 5 highest bottleneck nodes.

---

## 5. Find Orphan Logic (Dead Code Components)
Access functions and methods disconnected from structural flows.

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/oscar-backend/orphans`
- **Expected Success (200 OK):** An array of methods mapping local components whose internal project `fan_in` == 0. (Useful for tracking down deprecated files).

---

## 6. Export Graph Data
Retrieve a complete structure table mapped exactly into NetworkX edges that can visually graph the data later on.

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/oscar-backend/graph?format=json&min_confidence=0.5`
- **Expected Success (200 OK):** The raw network graph payload. *(Pro-tip: switch to `?format=csv` for raw data streaming tables).*

---

## 7. Get Deep Method Drill-down
Examine the direct callers and explicit signature data of a single method function. Notice in the example below, we grab one function named `health_check` residing inside the parent module `app.main` (from the original codebase).

- **Method:** `GET`
- **URL:** `http://127.0.0.1:8000/methods/oscar-backend/method/app.main:health_check`
- **Expected Success (200 OK):** A deep payload exposing callers, receivers, cyclic complexity metrics, decorators injected locally, and full AST signatures.
