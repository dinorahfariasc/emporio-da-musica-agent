import time

import jwt
import pytest

from app.auth.service_jwt import AUDIENCE, ISSUER, InvalidServiceToken, verify_service_jwt

SECRET = "test-secret-at-least-32-bytes-long!!"
USER_ID = "4c9b1a2e-0a1b-4c3d-9e4f-5a6b7c8d9e0f"


def _token(*, secret=SECRET, exp_offset=120, sub=USER_ID, iss=ISSUER, aud=AUDIENCE, **extra_claims):
    now = int(time.time())
    payload = {
        "sub": sub,
        "username": "demo",
        "iat": now,
        "exp": now + exp_offset,
        "iss": iss,
        "aud": aud,
        **extra_claims,
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def test_valid_token_round_trips():
    claims = verify_service_jwt(_token(), SECRET)
    assert claims.user_id == USER_ID
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
        {"username": "demo", "iat": now, "exp": now + 120, "iss": ISSUER, "aud": AUDIENCE},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(token, SECRET)


def test_garbage_token_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt("not-a-jwt", SECRET)


def test_wrong_issuer_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(iss="someone-else"), SECRET)


def test_wrong_audience_is_rejected():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(aud="someone-else"), SECRET)


def test_missing_issuer_or_audience_is_rejected():
    now = int(time.time())
    no_iss = jwt.encode(
        {"sub": USER_ID, "username": "demo", "iat": now, "exp": now + 120, "aud": AUDIENCE},
        SECRET,
        algorithm="HS256",
    )
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(no_iss, SECRET)


def test_lifetime_longer_than_the_max_is_rejected_even_with_a_valid_signature():
    # exp is still in the future and the signature is valid; only exp-iat is out of policy.
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(exp_offset=3600), SECRET)


def test_a_non_uuid_sub_is_a_clean_401_not_a_500():
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(_token(sub="not-a-uuid"), SECRET)


def test_alg_none_is_rejected():
    # An "unsecured" JWT (alg=none, no signature) must never be accepted even though its claims
    # would otherwise pass every other check.
    now = int(time.time())
    token = jwt.encode(
        {
            "sub": USER_ID,
            "username": "demo",
            "iat": now,
            "exp": now + 120,
            "iss": ISSUER,
            "aud": AUDIENCE,
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(InvalidServiceToken):
        verify_service_jwt(token, SECRET)
