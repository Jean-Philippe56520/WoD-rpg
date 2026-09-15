from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from .editable_repository import EditableSQLiteGameRepository, EditableSupabaseGameRepository
from .persistence import GameRepository


# Noms conservés comme points d'extension/test historiques de la factory.
SQLiteGameRepository = EditableSQLiteGameRepository
SupabaseGameRepository = EditableSupabaseGameRepository

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
    """Utilise Supabase en production et SQLite comme repli local explicite."""

    supabase_url = _read_secret(secrets, SUPABASE_URL_SECRET)
    supabase_key = _read_secret(secrets, SUPABASE_KEY_SECRET)

    if bool(supabase_url) != bool(supabase_key):
        raise RuntimeError(
            "Supabase persistence is partially configured: both SUPABASE_URL "
            "and SUPABASE_SECRET_KEY are required."
        )

    if supabase_url and supabase_key:
        return SupabaseGameRepository(supabase_url, supabase_key), "Supabase"

    # Le dépôt SQLite peut être mis en cache par Streamlit alors que le cwd change
    # (tests AppTest, redémarrages locaux). Conserver un chemin absolu évite qu'un
    # dépôt déjà construit pointe ensuite vers un autre répertoire relatif.
    resolved_path = Path(sqlite_path).expanduser().resolve()
    return SQLiteGameRepository(resolved_path), "SQLite local"
