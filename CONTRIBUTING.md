# Contributing to OSCAR Dependency Graph Observatory

Thank you for your interest in contributing! This project is an early-stage research prototype, and we welcome contributions of all kinds.

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Git**

### Local Setup

```bash
# Clone the repository
git clone https://github.com/OblivionCore25/oscar-dependency-observatory.git
cd oscar-dependency-observatory

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install fastapi uvicorn pydantic pydantic-settings httpx
uvicorn app.main:app --reload

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173` and proxies API calls to the backend at `http://localhost:8000`.

### Verify It Works

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

---

## Project Structure

```
backend/
  app/
    api/            # FastAPI route handlers
    config/         # Environment-based settings
    exporters/      # JSON/CSV graph export
    graph/          # Analytics, direct, and transitive services
    ingestion/      # npm and PyPI registry connectors
    models/         # Pydantic domain + API schemas
    normalization/  # Registry-specific data normalizers
    storage/        # JSON flat-file storage layer
  data/             # Local data files (gitignored)

frontend/
  src/
    components/     # React UI components
    hooks/          # Custom React Query hooks
    pages/          # Page-level route components
    services/       # API client (axios)
    types/          # TypeScript interfaces

docs/               # Project documentation
```

---

## How to Contribute

### Reporting Issues

- Use GitHub Issues for bugs, feature requests, or questions
- Include steps to reproduce if reporting a bug
- Label your issue appropriately (`bug`, `enhancement`, `question`)

### Submitting Changes

1. **Fork** the repository
2. **Create a branch** from `main`: `git checkout -b feature/your-feature`
3. **Make your changes** with clear, descriptive commits
4. **Test locally** — verify the backend starts and the frontend renders correctly
5. **Open a Pull Request** against `main` with a description of what you changed and why

### Commit Messages

Use concise, descriptive messages:

```
feat: add diamond dependency detection to analytics service
fix: correct fan-in deduplication for cross-version edges
docs: update technical reference with new endpoint
```

---

## Code Style

### Python (Backend)

- Follow PEP 8
- Use type hints on all function signatures
- Docstrings on all public classes and methods
- Pydantic models for all API schemas

### TypeScript (Frontend)

- Use TypeScript strict mode
- Define interfaces in `types/api.ts` for all API responses
- Use React Query hooks for data fetching

---

## Good First Issues

Look for issues labeled `good first issue` — these are scoped for newcomers:

- Adding unit tests for existing services
- Implementing the `diamondCount` metric
- Creating a `requirements.txt` from the current environment
- Adding `.env.example` with documented variables

---

## Research Contributions

This is a research-oriented project. We especially welcome:

- New graph metrics or risk scoring formulas
- Ecosystem coverage improvements (e.g., Maven, Cargo)
- Visualization enhancements
- Academic references and related work citations

---

## Questions?

Open an issue or reach out to the maintainer. We're happy to help you get started.
