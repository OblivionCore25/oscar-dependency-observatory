"""
OSCAR Dependency Graph Observatory — FastAPI Application Entry Point

This module creates and configures the FastAPI application instance.
Run with:
    uvicorn app.main:app --reload
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.models.api import HealthResponse

# ─── Logging Setup ──────────────────────────────────────────────────

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("oscar")

# ─── FastAPI Application ────────────────────────────────────────────

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Graph-based observatory for analyzing transitive dependencies, "
        "systemic risk, and structural patterns in open-source software ecosystems."
    ),
)

# ─── CORS (allow frontend dev server) ───────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints import router as dependencies_router
from app.api.analytics import router as analytics_router
from app.api.exports import router as exports_router
from app.api.packages import router as packages_router

# ─── Health Endpoint ────────────────────────────────────────────────


@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check",
    description="Returns the operational status of the backend.",
)
async def health_check() -> HealthResponse:
    """Return a simple health status."""
    return HealthResponse(status="ok")


# ─── API Routers ────────────────────────────────────────────────────

app.include_router(dependencies_router)
app.include_router(analytics_router)
app.include_router(exports_router)
app.include_router(packages_router)



from contextlib import asynccontextmanager

# ─── Startup / Shutdown Events ──────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(
        "🚀 %s v%s starting — storage_mode=%s, debug=%s",
        settings.app_name,
        settings.app_version,
        settings.storage_mode,
        settings.debug,
    )
    yield
    # Shutdown
    logger.info("🛑 %s shutting down", settings.app_name)
    
app.router.lifespan_context = lifespan
