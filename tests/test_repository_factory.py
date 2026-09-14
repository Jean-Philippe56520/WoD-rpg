from pathlib import Path

import pytest

import game.repository_factory as factory
from game.persistence import SQLiteGameRepository


def test_factory_uses_sqlite_without_supabase_secrets(tmp_path):
    repo, backend = factory.create_repository({}, tmp_path / "wod.sqlite3")
    assert isinstance(repo, SQLiteGameRepository)
    assert backend == "SQLite local"


def test_factory_rejects_partial_supabase_configuration(tmp_path):
    with pytest.raises(RuntimeError, match="partially configured"):
        factory.create_repository(
            {"SUPABASE_URL": "https://example.supabase.co"},
            tmp_path / "wod.sqlite3",
        )


def test_factory_uses_supabase_when_both_secrets_exist(monkeypatch, tmp_path):
    captured = {}

    class FakeSupabaseRepository:
        def __init__(self, url, secret_key):
            captured["url"] = url
            captured["secret_key"] = secret_key

    monkeypatch.setattr(factory, "SupabaseGameRepository", FakeSupabaseRepository)
    repo, backend = factory.create_repository(
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_SECRET_KEY": "server-secret",
        },
        tmp_path / "wod.sqlite3",
    )

    assert isinstance(repo, FakeSupabaseRepository)
    assert backend == "Supabase"
    assert captured == {
        "url": "https://example.supabase.co",
        "secret_key": "server-secret",
    }


def test_factory_treats_blank_secrets_as_missing(tmp_path):
    repo, backend = factory.create_repository(
        {"SUPABASE_URL": "  ", "SUPABASE_SECRET_KEY": "  "},
        Path(tmp_path) / "blank.sqlite3",
    )
    assert isinstance(repo, SQLiteGameRepository)
    assert backend == "SQLite local"
