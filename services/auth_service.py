from __future__ import annotations

import hmac
import logging
import re

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from config.settings import AUTH_DISABLED, SETUP_KEY
from db.connection import transaction
from db.repository import user_repository

logger = logging.getLogger(__name__)
_hasher = PasswordHasher()

PASSWORD_MIN = 12
PASSWORD_MAX = 128

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)


def hash_password(plain: str) -> str:
    return _hasher.hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    try:
        _hasher.verify(password_hash, plain)
        return True
    except VerifyMismatchError:
        return False


def build_bypass_user() -> dict:
    return {
        "user_id": 0,
        "username": "dev",
        "role": "admin",
        "access_mode": "full",
    }


def should_auto_auth() -> bool:
    """Only AUTH_DISABLED enables unauthenticated API access."""
    return bool(AUTH_DISABLED)


# ── Setup / claim ─────────────────────────────────────────────────────────────


def needs_setup() -> bool:
    """True when no admin has completed first-time setup via /setup."""
    return not user_repository.has_claimed_admin()


def verify_setup_key(key: str) -> bool:
    """Timing-safe comparison against the configured SETUP_KEY."""
    if not SETUP_KEY:
        return False
    return hmac.compare_digest(key.encode(), SETUP_KEY.encode())


def setup_claim_admin(email: str, password: str) -> dict:
    """Create the first admin and mark it as claimed. Raises ValueError on conflict."""
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValueError("invalid_email_format")
    if len(password) < PASSWORD_MIN:
        raise ValueError("password_too_short")
    if len(password) > PASSWORD_MAX:
        raise ValueError("password_too_long")
    with transaction():
        user_repository.acquire_bootstrap_advisory_lock()
        if user_repository.has_claimed_admin():
            raise ValueError("already_claimed")
        ph = hash_password(password)
        row = user_repository.insert(email, ph, "admin")
        user_repository.set_claimed_at(row["user_id"])
    logger.info("setup_success email=%s", email)
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "access_mode": "full",
    }


def recovery_reset_admin_password(setup_key: str, password: str) -> None:
    """Reset the claimed admin's password using the SETUP_KEY. Raises ValueError on failure."""
    if not verify_setup_key(setup_key):
        logger.warning("recovery_failed reason=invalid_setup_key")
        raise ValueError("invalid_setup_key")
    if len(password) < PASSWORD_MIN:
        raise ValueError("password_too_short")
    if len(password) > PASSWORD_MAX:
        raise ValueError("password_too_long")
    with transaction():
        # Find the first claimed admin
        from psycopg2.extras import RealDictCursor

        from db.connection import get_connection

        with get_connection() as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT user_id FROM app_user
                WHERE role = 'admin' AND claimed_at IS NOT NULL
                ORDER BY claimed_at
                LIMIT 1
                """,
            )
            row = cur.fetchone()
        if row is None:
            raise ValueError("no_claimed_admin")
        ph = hash_password(password)
        user_repository.update_password_hash(row["user_id"], ph)
    logger.info("recovery_success")


# ── New-user account claim ────────────────────────────────────────────────────


def claim_account(email: str, password: str) -> dict:
    """Let an admin-created user (no password yet) set their own password.

    Gate: user must exist, be active, and have password_hash IS NULL.
    Raises ValueError on any validation or state failure.
    """
    norm = email.strip().lower()
    if len(password) < PASSWORD_MIN:
        raise ValueError("password_too_short")
    if len(password) > PASSWORD_MAX:
        raise ValueError("password_too_long")
    row = user_repository.get_unclaimed_by_email(norm)
    if row is None:
        raise ValueError("no_unclaimed_account")
    ph = hash_password(password)
    updated = user_repository.update_password_hash(row["user_id"], ph)
    logger.info("claim_success email=%s role=%s", norm, row["role"])
    role = updated["role"]
    return {
        "user_id": updated["user_id"],
        "username": updated["username"],
        "role": role,
        "access_mode": "validator_only" if role == "validator" else "full",
    }


# ── Authentication ─────────────────────────────────────────────────────────────


def authenticate(email: str, password: str) -> dict | None:
    """Authenticate against app_user (Argon2). Returns user dict or None.

    Raises ValueError("password_not_set") when the user exists but has no password hash,
    so the caller can return an actionable error to the client.
    """
    if AUTH_DISABLED:
        return build_bypass_user()

    norm = email.strip().lower()
    row = user_repository.get_active_by_email(norm)
    if row is None:
        logger.warning("login_failure reason=user_not_found")
        return None

    if row["password_hash"] is None:
        logger.warning("login_failure reason=password_not_set email=%s", norm)
        raise ValueError("password_not_set")

    if not verify_password(row["password_hash"], password):
        logger.warning("login_failure reason=wrong_password")
        return None

    role = row["role"]
    logger.info("login_success email=%s role=%s", norm, role)
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": role,
        "access_mode": "validator_only" if role == "validator" else "full",
    }


# ── Dev / test utilities ───────────────────────────────────────────────────────


def reset_all_users() -> int:
    """Delete all rows in ``app_user``. Returns the number of rows removed."""
    with transaction():
        return user_repository.delete_all()


def dev_reset_to_single_admin(username: str, password: str) -> dict:
    """Remove every app_user row and create one active admin. Dev/test only.

    Password is hashed with Argon2. Atomic single transaction.
    """
    u = (username or "").strip()
    if not u:
        raise ValueError("username_required")
    if not (password or "").strip():
        raise ValueError("password_required")
    if len(password) < PASSWORD_MIN:
        raise ValueError("password_too_short")
    with transaction():
        user_repository.delete_all()
        ph = hash_password(password)
        row = user_repository.insert(u, ph, "admin")
        user_repository.set_claimed_at(row["user_id"])
    return {
        "user_id": row["user_id"],
        "username": row["username"],
        "role": row["role"],
        "is_active": row["is_active"],
        "access_mode": "full",
    }
