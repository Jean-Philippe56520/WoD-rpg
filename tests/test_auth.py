import json
import time

import httpx
import pytest

from game.auth import AuthError, AuthSession, SupabaseAuthClient


PUBLISHABLE = "sb_publishable_test"
URL = "https://example.supabase.co"
USER_ID = "11111111-1111-4111-8111-111111111111"


def _session_payload(email="a@example.com"):
    return {
        "access_token": "access",
        "refresh_token": "refresh",
        "expires_in": 3600,
        "user": {"id": USER_ID, "email": email},
    }


def test_sign_in_uses_publishable_key_and_returns_auth_identity():
    def handler(request: httpx.Request):
        assert request.url.path == "/auth/v1/token"
        assert request.url.params["grant_type"] == "password"
        assert request.headers["apikey"] == PUBLISHABLE
        body = json.loads(request.content)
        assert body["email"] == "a@example.com"
        return httpx.Response(200, json=_session_payload())

    client = SupabaseAuthClient(URL, PUBLISHABLE, transport=httpx.MockTransport(handler))
    session = client.sign_in("A@EXAMPLE.COM", "abcdefgh")
    assert session.user_id == USER_ID
    assert session.email == "a@example.com"


def test_signup_without_session_requires_email_confirmation():
    def handler(request: httpx.Request):
        assert request.url.path == "/auth/v1/signup"
        return httpx.Response(200, json={"user": {"id": USER_ID, "email": "a@example.com"}})

    client = SupabaseAuthClient(URL, PUBLISHABLE, transport=httpx.MockTransport(handler))
    assert client.sign_up("a@example.com", "abcdefgh") is None


def test_validate_refreshes_expiring_session_then_checks_user():
    calls = []

    def handler(request: httpx.Request):
        calls.append(request.url.path)
        if request.url.path == "/auth/v1/token":
            return httpx.Response(200, json=_session_payload())
        if request.url.path == "/auth/v1/user":
            assert request.headers["authorization"] == "Bearer access"
            return httpx.Response(200, json={"id": USER_ID, "email": "a@example.com"})
        return httpx.Response(404)

    client = SupabaseAuthClient(URL, PUBLISHABLE, transport=httpx.MockTransport(handler))
    expired = AuthSession(
        user_id=USER_ID,
        email="a@example.com",
        access_token="old-access",
        refresh_token="refresh",
        expires_at=int(time.time()) - 1,
    )
    current = client.validate(expired)
    assert current.access_token == "access"
    assert calls == ["/auth/v1/token", "/auth/v1/user"]


def test_invalid_login_returns_auth_error():
    def handler(request: httpx.Request):
        return httpx.Response(400, json={"error_description": "Invalid login credentials"})

    client = SupabaseAuthClient(URL, PUBLISHABLE, transport=httpx.MockTransport(handler))
    with pytest.raises(AuthError, match="Invalid login credentials"):
        client.sign_in("a@example.com", "abcdefgh")


def test_signup_enforces_password_minimum_before_network_call():
    client = SupabaseAuthClient(
        URL,
        PUBLISHABLE,
        transport=httpx.MockTransport(lambda request: pytest.fail("network should not be called")),
    )
    with pytest.raises(ValueError, match="8 caracteres"):
        client.sign_up("a@example.com", "short")
