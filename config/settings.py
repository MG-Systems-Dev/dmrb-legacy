"""Application configuration resolver."""

from __future__ import annotations

import logging
import os
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

IS_PRODUCTION = bool(
    os.getenv("RAILWAY_ENVIRONMENT_NAME")
    or os.getenv("RAILWAY_ENVIRONMENT")
    or is_truthy_setting("PRODUCTION")
)
# Normalized app environment label; defaults to `development` when unset.
APP_ENV = (os.getenv("ENV") or "development").strip().lower()

OPENAI_API_KEY = get_setting("OPENAI_API_KEY", "") or ""
OPENAI_CHAT_MODEL = get_setting("OPENAI_CHAT_MODEL", "gpt-4o-mini") or "gpt-4o-mini"

FEATURE_FLAGS = {
    "example": get_setting("FEATURE_FLAG_EXAMPLE", False),
}

logger.info(
    "Runtime env: DATABASE_URL=%s",
    "SET" if DATABASE_URL else "MISSING",
)


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
