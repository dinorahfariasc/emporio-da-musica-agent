import time

import jwt
import pytest
from fastapi import Request

from app.auth.dependency import (
    ServiceAuthMisconfigured,
    ServiceAuthUnauthorized,
    require_service_account,
)
from app.config import Settings

SECRET = "test-secret-at-least-32-bytes-long!!"


def _request(authorization: str | None) -> Request:
    headers = [(b"authorization", authorization.encode())] if authorization else []
    scope = {"type": "http", "headers": headers}
    return Request(scope)


def _token(secret=SECRET, exp_offset=120):
    now = int(time.time())
    payload = {"sub": "user-1", "username": "demo", "iat": now, "exp": now + exp_offset}
    return jwt.encode(payload, secret, algorithm="HS256")


async def test_missing_secret_is_a_misconfiguration():
    settings = Settings(_env_file=None, service_jwt_secret=None)
    with pytest.raises(ServiceAuthMisconfigured):
        await require_service_account(_request(f"Bearer {_token()}"), settings)


async def test_missing_header_is_unauthorized():
    settings = Settings(_env_file=None, service_jwt_secret=SECRET)
    with pytest.raises(ServiceAuthUnauthorized):
        await require_service_account(_request(None), settings)


async def test_bad_bearer_format_is_unauthorized():
    settings = Settings(_env_file=None, service_jwt_secret=SECRET)
    with pytest.raises(ServiceAuthUnauthorized):
        await require_service_account(_request("Token abc"), settings)


async def test_valid_token_returns_claims():
    settings = Settings(_env_file=None, service_jwt_secret=SECRET)
    claims = await require_service_account(_request(f"Bearer {_token()}"), settings)
    assert claims.user_id == "user-1"
    assert claims.username == "demo"


async def test_wrong_secret_is_unauthorized():
    settings = Settings(_env_file=None, service_jwt_secret=SECRET)
    with pytest.raises(ServiceAuthUnauthorized):
        await require_service_account(_request(f"Bearer {_token(secret='other')}"), settings)
