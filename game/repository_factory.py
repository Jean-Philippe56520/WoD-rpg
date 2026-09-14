from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .persistence import GameRepository, SQLiteGameRepository
from .supabase_repository import SupabaseGameRepository


SUPABASE_URL_SECRET = "SUPABASE_URL"
SUPABASE_KEY_SECRET = "SUPABASE_SECRET_KEY"


def _read_secret(secrets: Mapping[str, Any] | Any, name: str) -> str | None:
    if secrets is None:
        return None
    try:
        value = secrets.get(name)
    except (AttributeError, FileNotFoundError, KeyError):
        return None
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def create_repository(
    secrets: Mapping[str, Any] | Any = None,
    sqlite_path: str | Path = Path("data") / "wod_rpg.sqlite3",
) -> tuple[GameRepository, str]:
    """Select durable Supabase persistence when both server secrets exist.

    SQLite remains the explicit local-development fallback. A partial Supabase
    configuration is treated as an error so production never silently writes to
    ephemeral local storage.
    """

    supabase_url = _read_secret(secrets, SUPABASE_URL_SECRET)
    supabase_key = _read_secret(secrets, SUPABASE_KEY_SECRET)

    if bool(supabase_url) != bool(supabase_key):
        raise RuntimeError(
            "Supabase persistence is partially configured: both SUPABASE_URL "
            "and SUPABASE_SECRET_KEY are required."
        )

    if supabase_url and supabase_key:
        return SupabaseGameRepository(supabase_url, supabase_key), "Supabase"

    return SQLiteGameRepository(sqlite_path), "SQLite local"
