"""Verifies the short-lived HS256 JWT the Next.js BFF mints after login.

Contract: specs/004-auth-limits-deploy/contracts/service-jwt.md. The backend never checks a
password or looks at the `users` table; this token is the only authentication surface of
POST /api/chat.
"""

from dataclasses import dataclass

import jwt

ALGORITHM = "HS256"
CLOCK_SKEW_LEEWAY_S = 30


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
            options={"require": ["sub", "username", "exp", "iat"]},
        )
    except jwt.PyJWTError as exc:
        raise InvalidServiceToken(str(exc)) from exc
    return AccountClaims(user_id=payload["sub"], username=payload["username"])
