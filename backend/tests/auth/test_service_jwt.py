import time

import jwt
import pytest

from app.auth.service_jwt import InvalidServiceToken, verify_service_jwt

SECRET = "test-secret-at-least-32-bytes-long!!"


def _token(*, secret=SECRET, exp_offset=120, **extra_claims):
    now = int(time.time())
    payload = {
        "sub": "user-1",
        "username": "demo",
        "iat": now,
        "exp": now + exp_offset,
        **extra_claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_round_trips():
    claims = verify_service_jwt(_token(), SECRET)
    assert claims.user_id == "user-1"
    assert claims.username == "demo"


def test_expired_token_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(exp_offset=-60), SECRET)


def test_token_just_past_the_30s_leeway_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(exp_offset=-31), SECRET)


def test_token_within_the_30s_leeway_is_accepted():
    verify_service_jwt(_token(exp_offset=-29), SECRET)


def test_tampered_signature_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(secret="wrong-secret"), SECRET)


def test_missing_sub_is_rejected():
    now = int(time.time())
    token = jwt.encode(
        {"username": "demo", "iat": now, "exp": now + 120}, SECRET, algorithm="HS256"
    )
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(token, SECRET)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt("not-a-jwt", SECRET)
