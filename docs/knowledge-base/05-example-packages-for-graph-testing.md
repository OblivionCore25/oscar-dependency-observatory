# Example Packages for Graph Testing

This document lists real-world packages with large transitive dependency graphs, ideal for testing and demonstrating the OSCAR Dependency Graph Observatory UI. All packages can be searched directly from the **Package Search** page at `http://localhost:5173`.

---

## NPM (JavaScript/Node.js)

NPM packages are well-known for having massive transitive dependency trees due to the ecosystem's philosophy of small, composable modules.

| Package | Version | Why It's Interesting |
|---|---|---|
| `express` | `4.18.2` | Most popular Node.js web framework. ~31 direct deps (`body-parser`, `cookie`, `debug`, etc.) expanding into a large transitive graph. |
| `jest` | `29.7.0` | JavaScript testing framework. Pulls in a cluster of `@jest/...` internal packages, formatters, and reporters. |
| `react-scripts` | `5.0.1` | Core of Create React App. Extremely "heavy" — bundles Webpack, Babel, ESLint, and hundreds of compiled dependencies. Good for stress-testing graph physics. |
| `next` | `14.1.0` | React meta-framework. Complex dependency tree including SWC compilers, React itself, and routing utilities. |

---

## PyPI (Python)

Python packages tend to have flatter but strictly versioned dependency trees, which produce clean, readable graphs.

| Package | Version | Why It's Interesting |
|---|---|---|
| `fastapi` | `0.109.0` | Modern async web framework. ~14 direct deps (`starlette`, `pydantic`, `typing_extensions`) with a manageable downstream graph. |
| `boto3` | `1.34.40` | AWS SDK for Python. Core chain: `botocore` → `urllib3` → `s3transfer`. Good for showing linear dependency chains. |
| `pandas` | `2.2.0` | Data analysis library. Heavy reliance on `numpy`, `pytz`, and `python-dateutil` — showcases scientific computing dependency patterns. |
| `celery` | `5.3.6` | Distributed task queue. Shows messaging infrastructure layers: `kombu`, `billiard`, `redis`, `amqp`. |

---

## How to Use These Examples

1. Start the backend: `uvicorn app.main:app --reload` inside `backend/`
2. Start the frontend: `npm run dev` inside `frontend/`
3. Navigate to `http://localhost:5173/`
4. Select the **Ecosystem** (npm or pypi)
5. Enter the **Package Name** and **Version** exactly as shown in the tables
6. Click **Search** to view metrics, then **View Graph** to load the interactive Cytoscape visualization

> **Note:** The backend will auto-ingest the package from the upstream registry on first fetch if it has not been stored locally yet. Subsequent fetches are served from local JSON files.
