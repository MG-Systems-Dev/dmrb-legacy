from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api.deps import get_current_user
from api.rate_limit import limiter
from api.schemas.auth import ClaimRequest, RecoveryRequest, SetupRequest, SetupStatusResponse
from api.session_store import create_session
from services import auth_service
from services.auth_service import PASSWORD_MAX, PASSWORD_MIN

router = APIRouter()


# ── Setup status ───────────────────────────────────────────────────────────────


@router.get("/auth/setup-status", response_model=SetupStatusResponse)
async def setup_status():
    """Public: whether first-admin setup still needs to be completed."""
    if auth_service.needs_setup():
        return JSONResponse(
            content={"needs_setup": True, "reason": "no_claimed_admin"},
            headers={"Cache-Control": "no-store"},
        )
    return JSONResponse(
        content={"needs_setup": False, "reason": "claimed"},
        headers={"Cache-Control": "no-store"},
    )


# ── First-admin claim ──────────────────────────────────────────────────────────


@router.post("/auth/setup")
@limiter.limit("10/15minutes")
async def claim_setup(request: Request, body: SetupRequest, response: Response):
    """Claim first-admin: verify SETUP_KEY, create admin, start session."""
    if not auth_service.verify_setup_key(body.setup_key):
        raise HTTPException(status_code=403, detail="Invalid setup key.")

    if not auth_service.needs_setup():
        raise HTTPException(status_code=400, detail="Setup has already been completed.")

    if body.password != body.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if len(body.password) < PASSWORD_MIN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN} characters.",
        )

    if len(body.password) > PASSWORD_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {PASSWORD_MAX} characters.",
        )

    try:
        result = auth_service.setup_claim_admin(str(body.email), body.password)
    except ValueError as exc:
        code = str(exc)
        if code == "already_claimed":
            raise HTTPException(status_code=400, detail="Setup has already been completed.") from exc
        if code == "invalid_email_format":
            raise HTTPException(status_code=400, detail="Enter a valid email address.") from exc
        raise HTTPException(status_code=400, detail="Could not create admin account.") from exc

    create_session(response, result)
    return {"status": "ok", "email": result["username"]}


# ── New-user account claim ─────────────────────────────────────────────────────


@router.post("/auth/claim")
@limiter.limit("10/15minutes")
async def claim_account(request: Request, body: ClaimRequest, response: Response):
    """Let an admin-created user (no password yet) set their own password and sign in."""
    if body.password != body.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if len(body.password) < PASSWORD_MIN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN} characters.",
        )

    if len(body.password) > PASSWORD_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {PASSWORD_MAX} characters.",
        )

    try:
        result = auth_service.claim_account(str(body.email), body.password)
    except ValueError as exc:
        code = str(exc)
        if code == "no_unclaimed_account":
            raise HTTPException(
                status_code=404,
                detail="No pending account found for that email. Contact your admin.",
            ) from exc
        if code == "password_too_short":
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at least {PASSWORD_MIN} characters.",
            ) from exc
        if code == "password_too_long":
            raise HTTPException(
                status_code=400,
                detail=f"Password must be at most {PASSWORD_MAX} characters.",
            ) from exc
        raise HTTPException(status_code=400, detail="Could not claim account.") from exc

    create_session(response, result)
    return {"status": "ok", "email": result["username"]}


# ── Recovery ───────────────────────────────────────────────────────────────────


@router.post("/auth/recovery")
@limiter.limit("10/15minutes")
async def recovery_reset(request: Request, body: RecoveryRequest, response: Response):
    """Reset the claimed admin's password using the SETUP_KEY."""
    if body.password != body.password_confirm:
        raise HTTPException(status_code=400, detail="Passwords do not match.")

    if len(body.password) < PASSWORD_MIN:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at least {PASSWORD_MIN} characters.",
        )

    if len(body.password) > PASSWORD_MAX:
        raise HTTPException(
            status_code=400,
            detail=f"Password must be at most {PASSWORD_MAX} characters.",
        )

    try:
        auth_service.recovery_reset_admin_password(body.setup_key, body.password)
    except ValueError as exc:
        code = str(exc)
        if code == "invalid_setup_key":
            raise HTTPException(status_code=403, detail="Invalid setup key.") from exc
        if code == "no_claimed_admin":
            raise HTTPException(
                status_code=400,
                detail="No claimed admin found. Complete setup first.",
            ) from exc
        raise HTTPException(status_code=400, detail="Password reset failed.") from exc

    return {"status": "ok"}


# ── Current user ───────────────────────────────────────────────────────────────


@router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return {
        "user_id": user.get("user_id"),
        "username": user.get("username"),
        "role": user.get("role"),
        "access_mode": user.get("access_mode", "full"),
    }


# ── Deprecated bootstrap aliases (410 Gone) ───────────────────────────────────


@router.get("/auth/bootstrap-status")
async def bootstrap_status_gone():
    """Deprecated — use GET /api/auth/setup-status."""
    return JSONResponse(
        status_code=410,
        content={"detail": "This endpoint is gone. Use /api/auth/setup-status instead."},
    )


@router.post("/auth/bootstrap")
async def bootstrap_gone():
    """Deprecated — use POST /api/auth/setup."""
    return JSONResponse(
        status_code=410,
        content={"detail": "This endpoint is gone. Use /api/auth/setup instead."},
    )
