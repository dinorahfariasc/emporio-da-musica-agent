"""FastAPI dependency that is the only authentication surface of POST /api/chat.

A misconfigured secret fails closed (500), never silently accepts every token
(specs/004-auth-limits-deploy/contracts/service-jwt.md, FR-015). The two exceptions below are
mapped to responses by handlers registered in app.main, so the 401 body matches the existing
chat-stream error contract exactly (fixture http-401.json).
"""

from typing import Annotated

from fastapi import Depends, Request

from app.auth.service_jwt import AccountClaims, InvalidServiceToken, verify_service_jwt
from app.config import Settings, check_fail_closed_config, get_settings


class ServiceAuthMisconfigured(Exception):
    """A required production secret is missing/weak; a deploy mistake, never "accept any token"."""


class ServiceAuthUnauthorized(Exception):
    """Missing, malformed, or invalid Authorization header/token."""


async def require_service_account(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> AccountClaims:
    # Re-checked on every request, not only at startup: a FastAPI lifespan is not guaranteed to
    # run the same way on every Vercel Services deployment target (research.md R7).
    try:
        check_fail_closed_config(settings)
    except RuntimeError as exc:
        raise ServiceAuthMisconfigured(str(exc)) from exc
    if not settings.service_jwt_secret:
        raise ServiceAuthMisconfigured("SERVICE_JWT_SECRET is not configured")

    header = request.headers.get("authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ServiceAuthUnauthorized("missing or malformed Authorization header")

    try:
        return verify_service_jwt(token, settings.service_jwt_secret)
    except InvalidServiceToken as exc:
        raise ServiceAuthUnauthorized(str(exc)) from exc
