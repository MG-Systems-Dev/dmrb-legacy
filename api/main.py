from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from api.middleware.auth import AuthMiddleware
from api.middleware.request_id import RequestIDMiddleware
from api.rate_limit import limiter
from api.routers import (
    auth,
    board,
    dev,
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
from api.schemas.auth import LoginRequest
from api.session_store import clear_session, create_session
from config import settings
from services import auth_service

logger = logging.getLogger(__name__)

app = FastAPI(title="DMRB Legacy API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


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
    from db.repository import session_repository

    try:
        ensure_database_ready()
        logger.info("Database migrations applied successfully")
        deleted = session_repository.delete_expired()
        if deleted:
            logger.info("Cleaned up %d expired sessions", deleted)
    except Exception as exc:
        logger.error(
            "Database migration on startup failed (app will start anyway "
            "so /healthz responds; set DATABASE_URL and redeploy): %s",
            exc,
        )


@app.get("/healthz", tags=["health"])
async def healthz():
    """Public, unauthenticated liveness probe for Railway health checks."""
    return {"status": "ok"}


app.add_middleware(RequestIDMiddleware)
app.add_middleware(AuthMiddleware)

_cors_origins = settings.cors_allowed_origins()
if _cors_origins:
    # Outermost: answer OPTIONS and attach ACAO before auth runs.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# JSON API routes
app.include_router(auth.router, prefix="/api", tags=["auth"])

if settings.allow_dev_reset_admin_endpoint():
    app.include_router(dev.router, prefix="/api")

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
if not frontend_dist.exists():
    raise RuntimeError(
        "Missing React build at frontend/dist. Run the frontend build before starting FastAPI."
    )

FRONTEND_INDEX = frontend_dist / "index.html"
ASSETS_DIR = frontend_dist / "assets"
if ASSETS_DIR.is_dir():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="static-assets")


def _is_safe_file_under_dist(candidate: Path) -> bool:
    dist = frontend_dist.resolve()
    try:
        candidate.resolve().relative_to(dist)
    except ValueError:
        return False
    return candidate.is_file()


@app.get("/")
def serve_spa_index() -> FileResponse:
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


@app.get("/{full_path:path}")
def serve_spa_routes(full_path: str) -> FileResponse:
    if full_path == "api" or full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not found")
    candidate = frontend_dist / full_path
    if _is_safe_file_under_dist(candidate):
        return FileResponse(candidate)
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


@app.post("/api/login", tags=["auth"])
@limiter.limit("20/15minutes")
async def api_login(request: Request, body: LoginRequest, response: Response):
    """JSON login endpoint for the SPA."""
    try:
        result = auth_service.authenticate(body.email, body.password)
    except ValueError as exc:
        if str(exc) == "password_not_set":
            raise HTTPException(
                status_code=401,
                detail="Password has not been set yet. Ask an admin or use the recovery flow.",
            ) from exc
        raise HTTPException(status_code=401, detail="Invalid email or password.") from exc

    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    create_session(response, result)
    return {"status": "ok"}


@app.post("/api/logout", tags=["auth"])
async def api_logout(request: Request, response: Response):
    """JSON logout endpoint for the SPA."""
    clear_session(request, response)
    return {"status": "ok"}


@app.exception_handler(404)
async def _404_handler(request: Request, exc: HTTPException):
    if request.url.path.startswith("/api/"):
        return JSONResponse(status_code=404, content={"detail": "Not found"})
    return FileResponse(FRONTEND_INDEX, media_type="text/html")


if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
