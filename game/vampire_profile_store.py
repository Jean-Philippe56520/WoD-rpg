from __future__ import annotations

import json
from typing import Any

from .vampire_profile import VampireProfile, default_profile, profile_from_dict, profile_to_dict


class VampireProfileStore:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        if not self._is_supabase:
            self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        with self.repository._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS wod_character_profiles (
                    game_id TEXT NOT NULL,
                    character_id TEXT NOT NULL,
                    profile_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (game_id, character_id),
                    FOREIGN KEY (game_id, character_id)
                        REFERENCES wod_player_characters(game_id, character_id)
                        ON DELETE CASCADE
                );
                """
            )

    def get(self, game_id: str, character_id: str) -> VampireProfile | None:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_character_profiles",
                "profile_json",
                filters={"game_id": game_id, "character_id": character_id},
                limit=1,
            )
            return profile_from_dict(rows[0]["profile_json"]) if rows else None
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT profile_json FROM wod_character_profiles WHERE game_id = ? AND character_id = ?",
                (game_id, character_id),
            ).fetchone()
        return profile_from_dict(json.loads(row["profile_json"])) if row else None

    def ensure_for_character(self, character) -> VampireProfile:
        existing = self.get(character.game_id, character.character_id)
        if existing is not None:
            return existing
        profile = default_profile(character)
        self.save(profile)
        return profile

    def save(self, profile: VampireProfile) -> VampireProfile:
        payload = profile_to_dict(profile)
        if self._is_supabase:
            raw = self.repository.client.rpc(
                "wod_upsert_character_profile",
                {
                    "p_game_id": profile.game_id,
                    "p_character_id": profile.character_id,
                    "p_profile": payload,
                },
            )
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected profile persistence response")
            return profile_from_dict(raw)
        with self.repository._connect() as con:
            con.execute(
                """
                INSERT INTO wod_character_profiles(game_id,character_id,profile_json)
                VALUES(?,?,?)
                ON CONFLICT(game_id,character_id) DO UPDATE SET
                    profile_json=excluded.profile_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (profile.game_id, profile.character_id, json.dumps(payload, ensure_ascii=False)),
            )
        return profile
