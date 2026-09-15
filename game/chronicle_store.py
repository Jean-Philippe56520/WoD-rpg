from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

from .chronicle import ChronicleProgress, NightOutcome, PlayerCharacter


class ChronicleStore:
    """Persistence adapter for the player-centric chronicle.

    The legacy clan repository remains untouched. This adapter deliberately lives
    beside it so the migration can be rolled back without rewriting the political
    engine. SQLite creates its local tables lazily; Supabase uses the V0.21 schema.
    """

    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        if not self._is_supabase:
            self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        with self.repository._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS wod_chronicle_progress (
                    game_id TEXT PRIMARY KEY,
                    year INTEGER NOT NULL,
                    chapter INTEGER NOT NULL,
                    segment INTEGER NOT NULL,
                    nights_per_segment INTEGER NOT NULL,
                    segments_per_chapter INTEGER NOT NULL,
                    ellipse_years INTEGER NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wod_player_characters (
                    game_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    character_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    clan_id TEXT NOT NULL,
                    concept TEXT NOT NULL,
                    sire_id TEXT NOT NULL,
                    sire_name TEXT NOT NULL,
                    embraced_year INTEGER NOT NULL,
                    chronicle_year INTEGER NOT NULL,
                    chapter INTEGER NOT NULL,
                    segment INTEGER NOT NULL,
                    local_night INTEGER NOT NULL,
                    hunger INTEGER NOT NULL,
                    humanity INTEGER NOT NULL,
                    status INTEGER NOT NULL,
                    reputation INTEGER NOT NULL,
                    personal_influence REAL NOT NULL,
                    sire_relation INTEGER NOT NULL,
                    goal_progress INTEGER NOT NULL,
                    long_term_goal TEXT NOT NULL,
                    chapter_goal TEXT NOT NULL,
                    starting_discipline TEXT NOT NULL,
                    mortal_stance TEXT NOT NULL,
                    order_stance TEXT NOT NULL,
                    ready_for_convergence INTEGER NOT NULL DEFAULT 0,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (game_id, player_id),
                    UNIQUE (game_id, character_id),
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS wod_character_night_history (
                    game_id TEXT NOT NULL,
                    character_id TEXT NOT NULL,
                    chapter INTEGER NOT NULL,
                    segment INTEGER NOT NULL,
                    night_number INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    outcome_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (game_id, character_id, chapter, segment, night_number),
                    FOREIGN KEY (game_id, character_id)
                        REFERENCES wod_player_characters(game_id, character_id)
                        ON DELETE CASCADE
                );
                """
            )

    @staticmethod
    def _progress_from_row(row: dict[str, Any]) -> ChronicleProgress:
        return ChronicleProgress(
            game_id=str(row["game_id"]),
            year=int(row["year"]),
            chapter=int(row["chapter"]),
            segment=int(row["segment"]),
            nights_per_segment=int(row["nights_per_segment"]),
            segments_per_chapter=int(row["segments_per_chapter"]),
            ellipse_years=int(row["ellipse_years"]),
        )

    @staticmethod
    def _character_from_row(row: dict[str, Any]) -> PlayerCharacter:
        return PlayerCharacter(
            game_id=str(row["game_id"]),
            player_id=str(row["player_id"]),
            player_name=str(row["player_name"]),
            character_id=str(row["character_id"]),
            name=str(row["name"]),
            clan_id=str(row["clan_id"]),
            concept=str(row["concept"]),
            sire_id=str(row["sire_id"]),
            sire_name=str(row["sire_name"]),
            embraced_year=int(row["embraced_year"]),
            chronicle_year=int(row["chronicle_year"]),
            chapter=int(row["chapter"]),
            segment=int(row["segment"]),
            local_night=int(row["local_night"]),
            hunger=int(row["hunger"]),
            humanity=int(row["humanity"]),
            status=int(row["status"]),
            reputation=int(row["reputation"]),
            personal_influence=float(row["personal_influence"]),
            sire_relation=int(row["sire_relation"]),
            goal_progress=int(row["goal_progress"]),
            long_term_goal=str(row["long_term_goal"]),
            chapter_goal=str(row["chapter_goal"]),
            starting_discipline=str(row["starting_discipline"]),
            mortal_stance=str(row["mortal_stance"]),
            order_stance=str(row["order_stance"]),
            ready_for_convergence=bool(row["ready_for_convergence"]),
            is_active=bool(row["is_active"]),
        )

    @staticmethod
    def _character_payload(character: PlayerCharacter) -> dict[str, Any]:
        payload = asdict(character)
        payload["ready_for_convergence"] = bool(character.ready_for_convergence)
        payload["is_active"] = bool(character.is_active)
        return payload

    def ensure_progress(self, progress: ChronicleProgress) -> ChronicleProgress:
        existing = self.get_progress(progress.game_id)
        if existing is not None:
            return existing
        payload = asdict(progress)
        if self._is_supabase:
            self.repository.client.insert("wod_chronicle_progress", payload)
        else:
            with self.repository._connect() as con:
                con.execute(
                    """
                    INSERT INTO wod_chronicle_progress(
                        game_id,year,chapter,segment,nights_per_segment,
                        segments_per_chapter,ellipse_years
                    ) VALUES(?,?,?,?,?,?,?)
                    """,
                    (
                        progress.game_id,
                        progress.year,
                        progress.chapter,
                        progress.segment,
                        progress.nights_per_segment,
                        progress.segments_per_chapter,
                        progress.ellipse_years,
                    ),
                )
        return progress

    def get_progress(self, game_id: str) -> ChronicleProgress | None:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_chronicle_progress",
                "game_id,year,chapter,segment,nights_per_segment,segments_per_chapter,ellipse_years",
                filters={"game_id": game_id},
                limit=1,
            )
            return self._progress_from_row(rows[0]) if rows else None
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT * FROM wod_chronicle_progress WHERE game_id = ?",
                (game_id,),
            ).fetchone()
        return self._progress_from_row(dict(row)) if row else None

    def create_character(self, character: PlayerCharacter) -> None:
        if self.get_character(character.game_id, character.player_id) is not None:
            raise ValueError("This player already has a character in the chronicle")
        payload = self._character_payload(character)
        if self._is_supabase:
            self.repository.client.insert("wod_player_characters", payload)
            return
        columns = tuple(payload)
        placeholders = ",".join("?" for _ in columns)
        with self.repository._connect() as con:
            con.execute(
                f"INSERT INTO wod_player_characters({','.join(columns)}) VALUES({placeholders})",
                tuple(payload[column] for column in columns),
            )

    def get_character(self, game_id: str, player_id: str) -> PlayerCharacter | None:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_player_characters",
                "*",
                filters={"game_id": game_id, "player_id": player_id},
                limit=1,
            )
            return self._character_from_row(rows[0]) if rows else None
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT * FROM wod_player_characters WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
        return self._character_from_row(dict(row)) if row else None

    def list_characters(self, game_id: str) -> list[PlayerCharacter]:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_player_characters",
                "*",
                filters={"game_id": game_id},
                order="created_at.asc",
            )
            return [self._character_from_row(row) for row in rows]
        with self.repository._connect() as con:
            rows = con.execute(
                "SELECT * FROM wod_player_characters WHERE game_id = ? ORDER BY created_at, character_id",
                (game_id,),
            ).fetchall()
        return [self._character_from_row(dict(row)) for row in rows]

    def advance_personal_night(
        self,
        before: PlayerCharacter,
        outcome: NightOutcome,
        *,
        free_intent: str = "",
    ) -> PlayerCharacter:
        after = outcome.updated_character
        outcome_payload = {
            "roll": outcome.roll,
            "summary": outcome.summary,
            "detail": outcome.detail,
            "tags": list(outcome.tags),
            "free_intent": free_intent.strip(),
        }
        if self._is_supabase:
            raw = self.repository.client.rpc(
                "wod_advance_personal_night",
                {
                    "p_game_id": before.game_id,
                    "p_player_id": before.player_id,
                    "p_expected_chapter": before.chapter,
                    "p_expected_segment": before.segment,
                    "p_expected_night": before.local_night,
                    "p_action": outcome.action.value,
                    "p_outcome": outcome_payload,
                    "p_hunger": after.hunger,
                    "p_reputation": after.reputation,
                    "p_personal_influence": after.personal_influence,
                    "p_sire_relation": after.sire_relation,
                    "p_goal_progress": after.goal_progress,
                    "p_ready": after.ready_for_convergence,
                    "p_next_night": after.local_night,
                },
            )
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected chronicle update response")
            return self._character_from_row(raw)

        with self.repository._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM wod_player_characters WHERE game_id = ? AND player_id = ?",
                (before.game_id, before.player_id),
            ).fetchone()
            if row is None:
                raise ValueError("Unknown player character")
            current = self._character_from_row(dict(row))
            if (
                current.chapter != before.chapter
                or current.segment != before.segment
                or current.local_night != before.local_night
                or current.ready_for_convergence
            ):
                raise ValueError("Character night changed before submission")
            con.execute(
                """
                INSERT INTO wod_character_night_history(
                    game_id,character_id,chapter,segment,night_number,action,outcome_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    before.game_id,
                    before.character_id,
                    before.chapter,
                    before.segment,
                    before.local_night,
                    outcome.action.value,
                    json.dumps(outcome_payload, ensure_ascii=False),
                ),
            )
            con.execute(
                """
                UPDATE wod_player_characters
                SET local_night = ?, hunger = ?, reputation = ?, personal_influence = ?,
                    sire_relation = ?, goal_progress = ?, ready_for_convergence = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE game_id = ? AND player_id = ?
                """,
                (
                    after.local_night,
                    after.hunger,
                    after.reputation,
                    after.personal_influence,
                    after.sire_relation,
                    after.goal_progress,
                    int(after.ready_for_convergence),
                    before.game_id,
                    before.player_id,
                ),
            )
            con.commit()
        refreshed = self.get_character(before.game_id, before.player_id)
        if refreshed is None:
            raise RuntimeError("Character vanished after night resolution")
        return refreshed

    def list_history(self, game_id: str, character_id: str, limit: int = 30) -> list[dict[str, Any]]:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_character_night_history",
                "chapter,segment,night_number,action,outcome_json,created_at",
                filters={"game_id": game_id, "character_id": character_id},
                limit=limit,
                order="created_at.desc",
            )
            return rows
        with self.repository._connect() as con:
            rows = con.execute(
                """
                SELECT chapter,segment,night_number,action,outcome_json,created_at
                FROM wod_character_night_history
                WHERE game_id = ? AND character_id = ?
                ORDER BY created_at DESC, chapter DESC, segment DESC, night_number DESC
                LIMIT ?
                """,
                (game_id, character_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["outcome_json"] = json.loads(item["outcome_json"])
            result.append(item)
        return result

    def all_ready_for_convergence(self, game_id: str) -> bool:
        progress = self.get_progress(game_id)
        if progress is None:
            return False
        characters = [
            character
            for character in self.list_characters(game_id)
            if character.is_active
            and character.chapter == progress.chapter
            and character.segment == progress.segment
        ]
        return bool(characters) and all(character.ready_for_convergence for character in characters)

    def resolve_convergence(self, game_id: str) -> ChronicleProgress:
        if self._is_supabase:
            raw = self.repository.client.rpc("wod_resolve_convergence", {"p_game_id": game_id})
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected convergence response")
            return self._progress_from_row(raw)

        with self.repository._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            progress_row = con.execute(
                "SELECT * FROM wod_chronicle_progress WHERE game_id = ?",
                (game_id,),
            ).fetchone()
            if progress_row is None:
                raise ValueError("Chronicle progress is missing")
            progress = self._progress_from_row(dict(progress_row))
            rows = con.execute(
                """
                SELECT ready_for_convergence FROM wod_player_characters
                WHERE game_id = ? AND is_active = 1 AND chapter = ? AND segment = ?
                """,
                (game_id, progress.chapter, progress.segment),
            ).fetchall()
            if not rows or any(not bool(row["ready_for_convergence"]) for row in rows):
                raise ValueError("All active characters must be ready for the convergence")

            if progress.segment >= progress.segments_per_chapter:
                next_progress = ChronicleProgress(
                    game_id=game_id,
                    year=progress.year + progress.ellipse_years,
                    chapter=progress.chapter + 1,
                    segment=1,
                    nights_per_segment=progress.nights_per_segment,
                    segments_per_chapter=progress.segments_per_chapter,
                    ellipse_years=progress.ellipse_years,
                )
                reset_goal = True
            else:
                next_progress = ChronicleProgress(
                    game_id=game_id,
                    year=progress.year,
                    chapter=progress.chapter,
                    segment=progress.segment + 1,
                    nights_per_segment=progress.nights_per_segment,
                    segments_per_chapter=progress.segments_per_chapter,
                    ellipse_years=progress.ellipse_years,
                )
                reset_goal = False

            con.execute(
                """
                UPDATE wod_chronicle_progress
                SET year = ?, chapter = ?, segment = ?, updated_at = CURRENT_TIMESTAMP
                WHERE game_id = ?
                """,
                (
                    next_progress.year,
                    next_progress.chapter,
                    next_progress.segment,
                    game_id,
                ),
            )
            con.execute(
                """
                UPDATE wod_player_characters
                SET chronicle_year = ?, chapter = ?, segment = ?, local_night = 1,
                    ready_for_convergence = 0,
                    goal_progress = CASE WHEN ? THEN 0 ELSE goal_progress END,
                    updated_at = CURRENT_TIMESTAMP
                WHERE game_id = ? AND is_active = 1
                """,
                (
                    next_progress.year,
                    next_progress.chapter,
                    next_progress.segment,
                    int(reset_goal),
                    game_id,
                ),
            )
            con.commit()
        return next_progress
