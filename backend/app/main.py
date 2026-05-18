from pathlib import Path
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routers import (
    auth,
    users,
    projects,
    queries,
    results,
    datasources,
    api_keys,
    alerts,
    exports,
    websocket,
    admin,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("geoanalytica_starting", env=settings.APP_ENV)
    await init_db()
    logger.info("database_ready")
    yield
    logger.info("geoanalytica_shutdown")


app = FastAPI(
    title="GeoAnalytica API",
    description="Global data, decoded — Geospatial analysis platform API",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────
app.include_router(auth.router,        prefix="/api/auth",        tags=["Authentication"])
app.include_router(users.router,       prefix="/api/users",       tags=["Users"])
app.include_router(projects.router,    prefix="/api/projects",    tags=["Projects"])
app.include_router(queries.router,     prefix="/api/queries",     tags=["Queries"])
app.include_router(results.router,     prefix="/api/results",     tags=["Results"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["Datasources"])
app.include_router(api_keys.router,    prefix="/api/api-keys",    tags=["API Keys"])
app.include_router(alerts.router,      prefix="/api/alerts",      tags=["Alerts"])
app.include_router(exports.router,     prefix="/api/exports",     tags=["Exports"])
app.include_router(websocket.router,   prefix="/api/ws",          tags=["WebSocket"])
app.include_router(admin.router,       prefix="/api/admin",       tags=["Admin"])


# ── Health Check ─────────────────────────────────────────────
@app.get("/api/health", tags=["Health"])
async def health_check():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0",
        "env": settings.APP_ENV,
    }


# ── Global Exception Handler ─────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )


# ── Serve Static Frontend ────────────────────────────────────
import os as _os

_app_dir = Path(__file__).resolve().parent

# Allow override via env var for non-standard deployments
_frontend_dir = Path(_os.environ.get("FRONTEND_DIR", "")) if _os.environ.get("FRONTEND_DIR") else None

if _frontend_dir is None or not _frontend_dir.exists():
    # Auto-detect: walk up from app dir to project root then into frontend/
    _frontend_dir = _app_dir.parent.parent / "frontend"

if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
    logger.info("frontend_mounted", path=str(_frontend_dir))
else:
    logger.warning(
        "frontend_not_found",
        searched=str(_frontend_dir),
        hint="Set FRONTEND_DIR env var to the absolute path of the frontend directory",
    )
