"""Server-side session store backed by the api_session table."""

from __future__ import annotations

import secrets
from datetime import datetime

from db.connection import get_connection


def create(user_id: int, expires_at: datetime) -> str:
    """Insert a new session row and return the opaque session_id."""
    session_id = secrets.token_urlsafe(32)
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO api_session (session_id, user_id, expires_at) VALUES (%s, %s, %s)",
            (session_id, user_id, expires_at),
        )
    return session_id


def get_valid_user(session_id: str) -> dict | None:
    """Return the user dict for a non-expired session, or None."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT u.user_id, u.username, u.role
              FROM api_session s
              JOIN app_user u ON u.user_id = s.user_id
             WHERE s.session_id = %s
               AND s.expires_at > NOW()
               AND u.is_active = TRUE
            """,
            (session_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    user_id, username, role = row
    return {
        "user_id": user_id,
        "username": username,
        "role": role,
        "access_mode": "validator_only" if role == "validator" else "full",
    }


def delete(session_id: str) -> None:
    """Delete a single session row (logout)."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM api_session WHERE session_id = %s", (session_id,))


def delete_expired() -> int:
    """Delete all expired sessions and return the count removed."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM api_session WHERE expires_at <= NOW()")
        return cur.rowcount
