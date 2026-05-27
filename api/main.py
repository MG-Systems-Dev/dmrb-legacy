from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from api.middleware.request_id import RequestIDMiddleware
from api.routers import (
    board,
    health,
    imports,
    notes,
    operations,
    phase_scope,
    properties,
    tasks,
    turnovers,
    unit_master,
    units,
)
from config import settings

logger = logging.getLogger(__name__)

app = FastAPI(title="DMRB Legacy API")


@app.on_event("startup")
async def _apply_migrations() -> None:
    """Run idempotent schema + incremental migrations before serving traffic.

    Failures are logged loudly but do NOT crash the app — this ensures the
    public /healthz endpoint stays reachable so Railway's deploy can finish
    and surface the real error in logs (usually a missing/invalid
    DATABASE_URL). Real request handlers will still fail fast if the DB is
    unreachable.
    """
    from db.migration_runner import ensure_database_ready

    db_url = os.getenv("DATABASE_URL", "")
    if db_url:
        try:
            from urllib.parse import urlparse

            parsed = urlparse(db_url)
            safe_url = f"{parsed.scheme}://***@{parsed.hostname}:{parsed.port}{parsed.path}"
        except Exception:
            safe_url = "<unparseable>"
        logger.info("DATABASE_URL is set — connecting to: %s", safe_url)
    else:
        logger.error(
            "DATABASE_URL is not set — database operations will fail. "
            "Add the DATABASE_URL environment variable and redeploy."
        )

    started = time.monotonic()
    try:
        ensure_database_ready()
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info("Database migrations applied successfully (%.0f ms)", elapsed_ms)
    except Exception as exc:
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.error(
            "Database migration on startup failed after %.0f ms "
            "(app will start anyway so /healthz responds; set DATABASE_URL "
            "and redeploy): [%s] %s",
            elapsed_ms,
            type(exc).__name__,
            exc,
        )


@app.on_event("startup")
async def _check_frontend_dist() -> None:
    frontend_dist = Path("frontend/dist")
    if not frontend_dist.exists():
        logger.error(
            "Frontend dist directory does not exist at '%s' (cwd: %s). "
            "The SPA will not be served. Run the frontend build step.",
            frontend_dist.resolve(),
            Path.cwd(),
        )
        return

    files = list(frontend_dist.rglob("*"))
    html_files = [f for f in files if f.suffix == ".html"]
    js_files = [f for f in files if f.suffix == ".js"]
    logger.info(
        "Frontend dist directory found at '%s': %d total files, %d HTML, %d JS",
        frontend_dist.resolve(),
        len(files),
        len(html_files),
        len(js_files),
    )
    index_html = frontend_dist / "index.html"
    if not index_html.exists():
        logger.error(
            "index.html is missing from '%s' — the SPA will not load correctly.",
            frontend_dist.resolve(),
        )


@app.get("/healthz", tags=["health"])
async def healthz():
    """Public, unauthenticated liveness probe for Railway health checks."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "-")
    logger.error(
        "Unhandled exception during %s %s (request_id=%s): [%s] %s",
        request.method,
        request.url.path,
        request_id,
        type(exc).__name__,
        exc,
        exc_info=True,
    )
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )


app.add_middleware(RequestIDMiddleware)

_cors_origins = settings.cors_allowed_origins()
if _cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(board.router, prefix="/api", tags=["board"])
app.include_router(imports.router, prefix="/api", tags=["imports"])
app.include_router(operations.router, prefix="/api", tags=["operations"])
app.include_router(properties.router, prefix="/api", tags=["properties"])
app.include_router(turnovers.router, prefix="/api", tags=["turnovers"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(notes.router, prefix="/api", tags=["notes"])
app.include_router(units.router, prefix="/api", tags=["units"])
app.include_router(phase_scope.router, prefix="/api", tags=["phase-scope"])
app.include_router(unit_master.router, prefix="/api")

frontend_dist = Path("frontend/dist")
FRONTEND_INDEX = frontend_dist / "index.html"
ASSETS_DIR = frontend_dist / "assets"
# Former auth routes — permanent redirect so /login never serves the SPA shell.
_LEGACY_AUTH_PATHS = frozenset({"login", "setup", "claim", "recovery"})
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="static-assets")
elif not frontend_dist.exists():
    logger.warning(
        "Frontend build not found at frontend/dist — serving API only. "
        "Check build logs for TypeScript/Vite errors."
    )


def _is_safe_file_under_dist(candidate: Path) -> bool:
    dist = frontend_dist.resolve()
    try:
        candidate.resolve().relative_to(dist)
    except ValueError:
        return False
    return candidate.is_file()


def _frontend_status() -> dict[str, bool]:
    return {
        "frontend_dist_exists": frontend_dist.exists(),
        "index_html_exists": FRONTEND_INDEX.is_file(),
    }


@app.get("/", response_model=None)
def serve_spa_index() -> Response:
    if not FRONTEND_INDEX.is_file():
        return JSONResponse({"status": "ok", **_frontend_status()})
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


@app.get("/{full_path:path}")
def serve_spa_routes(full_path: str) -> FileResponse | RedirectResponse:
    first_segment = full_path.split("/", 1)[0]
    if first_segment in _LEGACY_AUTH_PATHS:
        return RedirectResponse(url="/board", status_code=308)
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = frontend_dist / full_path
    if _is_safe_file_under_dist(candidate):
        return FileResponse(candidate)
    if not FRONTEND_INDEX.is_file():
        raise HTTPException(status_code=404, detail="Frontend build not available")
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


@app.exception_handler(404)
async def _404_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    if not FRONTEND_INDEX.is_file():
        return JSONResponse(status_code=404, content={"detail": "Frontend build not available"})
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
