from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import uuid


@dataclass(frozen=True)
class CharacterScene:
    id: str
    game_id: str
    from_character_id: str
    to_character_id: str
    chapter: int
    segment: int
    night_number: int
    title: str
    opening_text: str
    response_text: str | None
    status: str
    created_at: str | None = None
    responded_at: str | None = None


class ChronicleSceneStore:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        if not self._is_supabase:
            self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        with self.repository._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS wod_character_scenes (
                    id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    from_character_id TEXT NOT NULL,
                    to_character_id TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    segment INTEGER NOT NULL,
                    night_number INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    opening_text TEXT NOT NULL,
                    response_text TEXT,
                    status TEXT NOT NULL DEFAULT 'open',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    responded_at TEXT,
                    FOREIGN KEY (game_id, from_character_id)
                        REFERENCES wod_player_characters(game_id, character_id) ON DELETE CASCADE,
                    FOREIGN KEY (game_id, to_character_id)
                        REFERENCES wod_player_characters(game_id, character_id) ON DELETE CASCADE,
                    CHECK (from_character_id <> to_character_id),
                    CHECK (status IN ('open','responded','closed'))
                );
                CREATE INDEX IF NOT EXISTS wod_character_scenes_incoming_idx
                    ON wod_character_scenes(game_id, to_character_id, status, created_at DESC);
                CREATE INDEX IF NOT EXISTS wod_character_scenes_outgoing_idx
                    ON wod_character_scenes(game_id, from_character_id, created_at DESC);
                """
            )

    @staticmethod
    def _scene_from_row(row: dict[str, Any]) -> CharacterScene:
        return CharacterScene(
            id=str(row["id"]),
            game_id=str(row["game_id"]),
            from_character_id=str(row["from_character_id"]),
            to_character_id=str(row["to_character_id"]),
            chapter=int(row["chapter"]),
            segment=int(row["segment"]),
            night_number=int(row["night_number"]),
            title=str(row["title"]),
            opening_text=str(row["opening_text"]),
            response_text=(str(row["response_text"]) if row.get("response_text") is not None else None),
            status=str(row["status"]),
            created_at=(str(row["created_at"]) if row.get("created_at") is not None else None),
            responded_at=(str(row["responded_at"]) if row.get("responded_at") is not None else None),
        )

    def create_scene(
        self,
        *,
        game_id: str,
        from_character_id: str,
        to_character_id: str,
        chapter: int,
        segment: int,
        night_number: int,
        title: str,
        opening_text: str,
    ) -> CharacterScene:
        title = " ".join(title.strip().split())
        opening_text = opening_text.strip()
        if not title or len(title) > 160:
            raise ValueError("Scene title must be between 1 and 160 characters")
        if not opening_text or len(opening_text) > 2000:
            raise ValueError("Scene opening must be between 1 and 2000 characters")
        if from_character_id == to_character_id:
            raise ValueError("A character cannot open a scene with themselves")

        scene_id = f"scene_{uuid.uuid4().hex}"
        payload = {
            "id": scene_id,
            "game_id": game_id,
            "from_character_id": from_character_id,
            "to_character_id": to_character_id,
            "chapter": chapter,
            "segment": segment,
            "night_number": night_number,
            "title": title,
            "opening_text": opening_text,
            "status": "open",
        }
        if self._is_supabase:
            self.repository.client.insert("wod_character_scenes", payload)
        else:
            columns = tuple(payload)
            placeholders = ",".join("?" for _ in columns)
            with self.repository._connect() as con:
                con.execute(
                    f"INSERT INTO wod_character_scenes({','.join(columns)}) VALUES({placeholders})",
                    tuple(payload[column] for column in columns),
                )
        return self.get_scene(game_id, scene_id)

    def get_scene(self, game_id: str, scene_id: str) -> CharacterScene:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_character_scenes",
                "*",
                filters={"game_id": game_id, "id": scene_id},
                limit=1,
            )
            if not rows:
                raise ValueError("Unknown scene")
            return self._scene_from_row(rows[0])
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT * FROM wod_character_scenes WHERE game_id = ? AND id = ?",
                (game_id, scene_id),
            ).fetchone()
        if row is None:
            raise ValueError("Unknown scene")
        return self._scene_from_row(dict(row))

    def list_incoming(self, game_id: str, character_id: str, limit: int = 30) -> list[CharacterScene]:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_character_scenes",
                "*",
                filters={"game_id": game_id, "to_character_id": character_id},
                order="created_at.desc",
                limit=limit,
            )
            return [self._scene_from_row(row) for row in rows]
        with self.repository._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM wod_character_scenes
                WHERE game_id = ? AND to_character_id = ?
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                (game_id, character_id, limit),
            ).fetchall()
        return [self._scene_from_row(dict(row)) for row in rows]

    def list_outgoing(self, game_id: str, character_id: str, limit: int = 30) -> list[CharacterScene]:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_character_scenes",
                "*",
                filters={"game_id": game_id, "from_character_id": character_id},
                order="created_at.desc",
                limit=limit,
            )
            return [self._scene_from_row(row) for row in rows]
        with self.repository._connect() as con:
            rows = con.execute(
                """
                SELECT * FROM wod_character_scenes
                WHERE game_id = ? AND from_character_id = ?
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                (game_id, character_id, limit),
            ).fetchall()
        return [self._scene_from_row(dict(row)) for row in rows]

    def respond(self, scene: CharacterScene, *, character_id: str, response_text: str) -> CharacterScene:
        response_text = response_text.strip()
        if scene.to_character_id != character_id:
            raise ValueError("Only the targeted character may respond")
        if scene.status != "open":
            raise ValueError("Scene is no longer open")
        if not response_text or len(response_text) > 2000:
            raise ValueError("Response must be between 1 and 2000 characters")

        if self._is_supabase:
            raw = self.repository.client.rpc(
                "wod_respond_character_scene",
                {
                    "p_game_id": scene.game_id,
                    "p_scene_id": scene.id,
                    "p_character_id": character_id,
                    "p_response": response_text,
                },
            )
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected scene response")
            return self._scene_from_row(raw)

        with self.repository._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            current = con.execute(
                "SELECT * FROM wod_character_scenes WHERE game_id = ? AND id = ?",
                (scene.game_id, scene.id),
            ).fetchone()
            if current is None:
                raise ValueError("Unknown scene")
            current_scene = self._scene_from_row(dict(current))
            if current_scene.to_character_id != character_id or current_scene.status != "open":
                raise ValueError("Scene can no longer be answered")
            con.execute(
                """
                UPDATE wod_character_scenes
                SET response_text = ?, status = 'responded', responded_at = CURRENT_TIMESTAMP
                WHERE game_id = ? AND id = ?
                """,
                (response_text, scene.game_id, scene.id),
            )
            con.commit()
        return self.get_scene(scene.game_id, scene.id)
