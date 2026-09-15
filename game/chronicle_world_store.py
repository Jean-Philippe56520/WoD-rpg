from __future__ import annotations

from dataclasses import asdict
from typing import Any
import uuid

from .chronicle import ChronicleProgress
from .chronicle_world import WorldBeat


class ChronicleWorldStore:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        if not self._is_supabase:
            self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        with self.repository._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS wod_chronicle_world_events (
                    id TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    year INTEGER NOT NULL,
                    chapter INTEGER NOT NULL,
                    segment INTEGER NOT NULL,
                    actor_id TEXT NOT NULL,
                    actor_name TEXT NOT NULL,
                    category TEXT NOT NULL,
                    public_text TEXT NOT NULL,
                    hidden_intent TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS wod_chronicle_world_events_game_idx
                    ON wod_chronicle_world_events(game_id, created_at DESC);
                """
            )

    def record_beats(
        self,
        progress: ChronicleProgress,
        beats: tuple[WorldBeat, ...],
    ) -> None:
        for beat in beats:
            payload = {
                "id": f"world_{uuid.uuid4().hex}",
                "game_id": progress.game_id,
                "year": progress.year,
                "chapter": progress.chapter,
                "segment": progress.segment,
                **asdict(beat),
            }
            if self._is_supabase:
                self.repository.client.insert("wod_chronicle_world_events", payload)
            else:
                columns = tuple(payload)
                placeholders = ",".join("?" for _ in columns)
                with self.repository._connect() as con:
                    con.execute(
                        f"INSERT INTO wod_chronicle_world_events({','.join(columns)}) VALUES({placeholders})",
                        tuple(payload[column] for column in columns),
                    )

    def list_events(self, game_id: str, limit: int = 30) -> list[dict[str, Any]]:
        if self._is_supabase:
            return self.repository.client.select(
                "wod_chronicle_world_events",
                "id,game_id,year,chapter,segment,actor_id,actor_name,category,public_text,created_at",
                filters={"game_id": game_id},
                order="created_at.desc",
                limit=limit,
            )
        with self.repository._connect() as con:
            rows = con.execute(
                """
                SELECT id,game_id,year,chapter,segment,actor_id,actor_name,category,public_text,created_at
                FROM wod_chronicle_world_events
                WHERE game_id = ?
                ORDER BY created_at DESC, id DESC LIMIT ?
                """,
                (game_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
