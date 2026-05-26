"""Application configuration resolver."""

from __future__ import annotations

import logging
import os
import sys
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _load_streamlit_secrets() -> dict[str, Any]:
    try:
        secrets_path = Path(".streamlit/secrets.toml")
        if not secrets_path.exists():
            return {}
        with secrets_path.open("rb") as fh:
            return tomllib.load(fh)
    except Exception:
        return {}


def get_setting(key: str, default: Any = None) -> Any:
    value = os.getenv(key)
    if value is not None:
        return value
    return _load_streamlit_secrets().get(key, default)


def is_truthy_setting(key: str) -> bool:
    v = get_setting(key, "")
    if v is None:
        return False
    s = str(v).strip().lower()
    return s in ("1", "true", "yes", "on")


# Load .env before evaluating settings — local/dev only; Railway injects vars natively.
# override=False means already-set env vars (e.g. from shell) take precedence.
if not (os.getenv("RAILWAY_ENVIRONMENT_NAME") or os.getenv("RAILWAY_ENVIRONMENT")):
    try:
        from dotenv import load_dotenv

        load_dotenv(override=False)
    except ImportError:
        pass  # python-dotenv not installed; rely on env vars being set manually

DATABASE_URL = get_setting("DATABASE_URL", "")
SUPABASE_URL = get_setting("SUPABASE_URL", "")
SUPABASE_KEY = get_setting("SUPABASE_KEY", "")
APP_USERNAME = get_setting("APP_USERNAME", "")
APP_PASSWORD = get_setting("APP_PASSWORD", "")
VALIDATOR_USERNAME = get_setting("VALIDATOR_USERNAME", "")
VALIDATOR_PASSWORD = get_setting("VALIDATOR_PASSWORD", "")

_DEFAULT_SECRET_KEY = "dev-secret-key-change-me-in-production"
# Accept SESSION_SECRET as an alias for SECRET_KEY (parity with spec wording).
SECRET_KEY = get_setting("SESSION_SECRET", "") or get_setting("SECRET_KEY", _DEFAULT_SECRET_KEY)

IS_PRODUCTION = bool(
    os.getenv("RAILWAY_ENVIRONMENT_NAME")
    or os.getenv("RAILWAY_ENVIRONMENT")
    or is_truthy_setting("PRODUCTION")
)
# Normalized app environment label; defaults to `development` when unset.
APP_ENV = (os.getenv("ENV") or "development").strip().lower()
SESSION_COOKIE_SECURE = IS_PRODUCTION or is_truthy_setting("SESSION_COOKIE_SECURE")

SETUP_KEY = get_setting("SETUP_KEY", "")

# API auth uses public.app_user only. Kept for Streamlit / legacy: "env" = APP_*, "db" = app_user.
_LEGACY_AUTH_SRC = (get_setting("LEGACY_AUTH_SOURCE", "db") or "db").strip().lower()
LEGACY_AUTH_SOURCE = _LEGACY_AUTH_SRC if _LEGACY_AUTH_SRC in ("env", "db") else "db"
AUTH_DISABLED = is_truthy_setting("AUTH_DISABLED")

OPENAI_API_KEY = get_setting("OPENAI_API_KEY", "") or ""
OPENAI_CHAT_MODEL = get_setting("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"

FEATURE_FLAGS = {
    "example": get_setting("FEATURE_FLAG_EXAMPLE", False),
}

# ── Startup validation ────────────────────────────────────────────────────────
# These run at import time so misconfigured apps fail loudly before serving traffic.

if not SETUP_KEY:
    sys.exit(
        "[auth] SETUP_KEY env var is required. "
        "Set it in .env (local) or Railway Variables (prod). "
        'Generate one with: python3 -c "import secrets; print(secrets.token_urlsafe(32))"'
    )

if IS_PRODUCTION and AUTH_DISABLED:
    sys.exit(
        "[auth] AUTH_DISABLED is incompatible with IS_PRODUCTION. "
        "Remove AUTH_DISABLED from Railway Variables."
    )

if IS_PRODUCTION and SECRET_KEY == _DEFAULT_SECRET_KEY:
    sys.exit(
        "[auth] SECRET_KEY (or SESSION_SECRET) must be set to a strong random value in production. "
        'Generate one with: python3 -c "import secrets; print(secrets.token_urlsafe(64))"'
    )

logger.info(
    "Auth env: SETUP_KEY=%s SECRET_KEY=%s DATABASE_URL=%s",
    "set" if SETUP_KEY else "missing",
    "default" if SECRET_KEY == _DEFAULT_SECRET_KEY else "set",
    "set" if DATABASE_URL else "missing",
)


def allow_dev_reset_admin_endpoint() -> bool:
    """Allow POST /api/dev/reset-admin only in a non-production development process."""
    if IS_PRODUCTION:
        return False
    if APP_ENV in ("production", "prod", "staging", "stg"):
        return False
    return APP_ENV in ("development", "dev", "local")


def cors_allowed_origins() -> list[str] | None:
    """Origins for FastAPI CORSMiddleware. None = do not register CORS (same-origin SPA).

    Set ``CORS_ORIGINS`` to a comma-separated list to allow browser clients on other
    origins (e.g. Vite on :5173). In non-production, sensible localhost defaults apply
    when ``CORS_ORIGINS`` is unset so local ``npm run dev`` can call the API on :8000.
    """
    raw = (get_setting("CORS_ORIGINS", "") or "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    if IS_PRODUCTION:
        return None
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://0.0.0.0:8000",
    ]
