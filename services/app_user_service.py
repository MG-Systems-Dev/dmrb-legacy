"""Admin operations on ``app_user`` (DB-backed login)."""

from __future__ import annotations

import re

from psycopg2 import errors as pg_errors

from db.repository import user_repository
from services.auth_service import PASSWORD_MIN, hash_password
from services.write_guard import check_writes_enabled

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.IGNORECASE)


class AppUserError(Exception):
    pass


def list_users() -> list[dict]:
    try:
        return user_repository.list_all_for_admin()
    except Exception as exc:
        raise AppUserError(
            "Could not load app_user. Ensure the database is migrated (table app_user)."
        ) from exc


def create_user(email: str, role: str, password: str | None = None) -> dict:
    check_writes_enabled()
    email = (email or "").strip().lower()
    if not email:
        raise AppUserError("Email is required.")
    if not _EMAIL_RE.match(email):
        raise AppUserError("Enter a valid email address.")
    if role not in ("admin", "validator"):
        raise AppUserError("Invalid role.")
    pw = (password or "").strip() or None
    if pw is not None and len(pw) < PASSWORD_MIN:
        raise AppUserError(f"Password must be at least {PASSWORD_MIN} characters.")
    ph = hash_password(pw) if pw else None
    try:
        return user_repository.insert(email, ph, role)
    except pg_errors.UniqueViolation as exc:
        raise AppUserError("That email is already registered.") from exc


def set_password(user_id: int, new_password: str) -> dict:
    check_writes_enabled()
    if not new_password:
        raise AppUserError("Password is required.")
    row = user_repository.get_by_id(user_id)
    if row is None:
        raise AppUserError("User not found.")
    updated = user_repository.update_password_hash(user_id, hash_password(new_password))
    if updated is None:
        raise AppUserError("User not found.")
    return updated


def change_role(user_id: int, role: str) -> dict:
    check_writes_enabled()
    if role not in ("admin", "validator"):
        raise AppUserError("Invalid role.")
    row = user_repository.get_by_id(user_id)
    if row is None:
        raise AppUserError("User not found.")
    updated = user_repository.update_role(user_id, role)
    if updated is None:
        raise AppUserError("User not found.")
    return updated


def set_active(user_id: int, is_active: bool) -> dict:
    check_writes_enabled()
    row = user_repository.get_by_id(user_id)
    if row is None:
        raise AppUserError("User not found.")
    updated = user_repository.set_active(user_id, is_active)
    if updated is None:
        raise AppUserError("User not found.")
    return updated
