import pytest

from game.supabase_repository import SupabaseGameRepository, _as_scalar


def test_as_scalar_unwraps_single_rpc_result():
    assert _as_scalar(["ready"]) == "ready"
    assert _as_scalar("open") == "open"
    assert _as_scalar([]) == []


def test_repository_requires_server_credentials_before_client_import():
    with pytest.raises(ValueError, match="required"):
        SupabaseGameRepository("", "")
