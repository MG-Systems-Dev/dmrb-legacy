"""Opaque session cookie backed by the api_session DB table.

Replaces api/session_cookie.py (signed itsdangerous payload) with a
server-side store: the cookie carries only a random session_id; all
session state lives in the database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Request, Response

from config.settings import SESSION_COOKIE_SECURE
from db.repository import session_repository

COOKIE_NAME = "dmrb_session"
SESSION_MAX_AGE = 7 * 24 * 3600  # 7 days


def create_session(response: Response, user_dict: dict) -> str:
    """Create a DB session row and set the opaque cookie on response.

    Invalidates all prior sessions for the user before creating the new one.
    """
    session_repository.delete_by_user(user_dict["user_id"])
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE)
    session_id = session_repository.create(user_dict["user_id"], expires_at)
    response.set_cookie(
        key=COOKIE_NAME,
        value=session_id,
        httponly=True,
        samesite="lax",
        secure=SESSION_COOKIE_SECURE,
        max_age=SESSION_MAX_AGE,
    )
    return session_id


def get_session_user(request: Request) -> dict | None:
    """Return the authenticated user dict for this request, or None."""
    session_id = request.cookies.get(COOKIE_NAME)
    if not session_id:
        return None
    return session_repository.get_valid_user(session_id)


def clear_session(request: Request, response: Response) -> None:
    """Delete the DB session row and clear the cookie."""
    session_id = request.cookies.get(COOKIE_NAME)
    if session_id:
        session_repository.delete(session_id)
    response.delete_cookie(key=COOKIE_NAME)
