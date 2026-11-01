"""Verifies the short-lived HS256 JWT the Next.js BFF mints after login.

Contract: specs/004-auth-limits-deploy/contracts/service-jwt.md. The backend never checks a
password or looks at the `users` table; this token is the only authentication surface of
POST /api/chat.
"""

import uuid
from dataclasses import dataclass

import jwt

ALGORITHM = "HS256"
CLOCK_SKEW_LEEWAY_S = 30
# Defense in depth against a compromised/buggy minting process issuing a long-lived token: even a
# signature-valid token is rejected if its own exp-iat exceeds this, regardless of "now".
MAX_LIFETIME_S = 300
ISSUER = "emporio-da-musica-bff"
AUDIENCE = "emporio-da-musica-backend"


class InvalidServiceToken(Exception):
    """Missing, malformed, expired-beyond-leeway, or badly signed token."""


@dataclass(frozen=True)
class AccountClaims:
    user_id: str
    username: str


def verify_service_jwt(token: str, secret: str) -> AccountClaims:
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            leeway=CLOCK_SKEW_LEEWAY_S,
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["sub", "username", "exp", "iat", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidServiceToken(str(exc)) from exc

    exp, iat = payload["exp"], payload["iat"]
    if exp - iat > MAX_LIFETIME_S:
        raise InvalidServiceToken("token lifetime exceeds the maximum allowed")

    sub = payload["sub"]
    try:
        uuid.UUID(str(sub))
    except ValueError as exc:
        # A malformed sub must be a clean 401, never a 500 from a downstream UUID cast.
        raise InvalidServiceToken("sub is not a valid UUID") from exc

    return AccountClaims(user_id=sub, username=payload["username"])
