import base64
import json

import httpx
import pytest

from game.supabase_repository import (
    SupabaseGameRepository,
    _as_scalar,
    _server_headers,
)


def test_as_scalar_unwraps_single_rpc_result():
    assert _as_scalar(["ready"]) == "ready"
    assert _as_scalar("open") == "open"
    assert _as_scalar([]) == []


def test_repository_requires_server_credentials():
    with pytest.raises(ValueError, match="required"):
        SupabaseGameRepository("", "")


def test_new_secret_key_is_sent_only_as_apikey():
    headers = _server_headers("sb_secret_test")
    assert headers["apikey"] == "sb_secret_test"
    assert "Authorization" not in headers


def test_publishable_key_is_rejected_for_server_repository():
    with pytest.raises(ValueError, match="publishable"):
        _server_headers("sb_publishable_test")


def test_legacy_service_role_jwt_keeps_bearer_header():
    payload = base64.urlsafe_b64encode(json.dumps({"role": "service_role"}).encode()).decode().rstrip("=")
    token = f"e30.{payload}.signature"
    headers = _server_headers(token)
    assert headers["apikey"] == token
    assert headers["Authorization"] == f"Bearer {token}"


def test_secret_key_rpc_does_not_send_bearer_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["apikey"] = request.headers.get("apikey")
        seen["authorization"] = request.headers.get("authorization")
        seen["path"] = request.url.path
        return httpx.Response(204)

    repo = SupabaseGameRepository(
        "https://example.supabase.co",
        "sb_secret_test",
        transport=httpx.MockTransport(handler),
    )
    repo.client.rpc("wod_ensure_game", {"x": 1})

    assert seen["apikey"] == "sb_secret_test"
    assert seen["authorization"] is None
    assert seen["path"].endswith("/rest/v1/rpc/wod_ensure_game")
