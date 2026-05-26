from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from api.session_store import get_session_user
from services import auth_service

_API_PUBLIC_PREFIXES = (
    "/api/login",
    "/api/logout",
    # new claim/recovery endpoints
    "/api/auth/setup-status",
    "/api/auth/setup",
    "/api/auth/recovery",
    # deprecated bootstrap aliases (return 410 in the router)
    "/api/auth/bootstrap-status",
    "/api/auth/bootstrap",
    # dev utility
    "/api/dev/reset-admin",
    # health probes
    "/api/health",
    "/healthz",
)


def _is_public_api_path(path: str) -> bool:
    return any(path == p or path.startswith(p + "/") for p in _API_PUBLIC_PREFIXES)


_PUBLIC_PATHS = frozenset(
    {
        "/",
        "/login",
        "/logout",
        "/setup",
        "/recovery",
        "/docs",
        "/openapi.json",
        "/api/docs",
        "/api/openapi.json",
        "/favicon.ico",
        "/vite.svg",
    }
)


def _is_htmx(request: Request) -> bool:
    return request.headers.get("HX-Request") == "true"


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        if (
            path in _PUBLIC_PATHS
            or path.startswith("/static/")
            or path.startswith("/assets/")
            or not path.startswith("/api/")
        ):
            return await call_next(request)

        if _is_public_api_path(path):
            return await call_next(request)

        if auth_service.should_auto_auth():
            request.state.user = auth_service.build_bypass_user()
            return await call_next(request)

        user = get_session_user(request)
        if user is None:
            return self._unauthenticated(request)

        request.state.user = user
        return await call_next(request)

    @staticmethod
    def _unauthenticated(request: Request) -> Response:
        if _is_htmx(request):
            return Response(status_code=401, headers={"HX-Redirect": "/login"})
        return JSONResponse(status_code=401, content={"detail": "Not authenticated"})
