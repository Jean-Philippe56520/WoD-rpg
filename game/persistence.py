from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from .models import ClanNightOrders, ClanNightReport, GameState, NightStatus
from .serialization import (
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_json,
    game_state_to_json,
    report_from_json,
    report_to_json,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ResolutionBundle:
    game_id: str
    night: int
    state: GameState
    orders_by_clan: dict[str, ClanNightOrders]


class GameRepository(Protocol):
    def ensure_game(self, game_id: str, name: str, state: GameState, required_clans: tuple[str, ...]) -> None: ...
    def get_game_state(self, game_id: str) -> GameState: ...
    def get_game_info(self, game_id: str) -> dict: ...
    def claim_clan(self, game_id: str, player_id: str, player_name: str, clan_id: str) -> None: ...
    def get_player_clan(self, game_id: str, player_id: str) -> str | None: ...
    def list_assignments(self, game_id: str) -> dict[str, str]: ...
    def submit_orders(self, game_id: str, player_id: str, orders: ClanNightOrders) -> NightStatus: ...
    def submission_statuses(self, game_id: str) -> dict[str, bool]: ...
    def try_begin_resolution(self, game_id: str) -> ResolutionBundle | None: ...
    def abort_resolution(self, game_id: str, night: int) -> None: ...
    def finalize_resolution(self, bundle: ResolutionBundle, state: GameState, reports: dict[str, ClanNightReport]) -> None: ...
    def get_report(self, game_id: str, night: int, clan_id: str) -> ClanNightReport | None: ...
    def list_reports(self, game_id: str, clan_id: str) -> list[ClanNightReport]: ...
    def post_elysium_message(self, game_id: str, player_id: str, clan_id: str, body: str) -> None: ...
    def list_elysium_messages(self, game_id: str, limit: int = 100) -> list[dict]: ...


class SQLiteGameRepository:
    def __init__(self, path: str | Path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._initialize_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        return connection

    def _initialize_schema(self) -> None:
        with self._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    current_night INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    required_clans_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS game_players (
                    game_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    player_name TEXT NOT NULL,
                    clan_id TEXT NOT NULL,
                    claimed_at TEXT NOT NULL,
                    PRIMARY KEY (game_id, player_id),
                    UNIQUE (game_id, clan_id),
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS nights (
                    game_id TEXT NOT NULL,
                    night_number INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    state_before_json TEXT NOT NULL,
                    state_after_json TEXT,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    PRIMARY KEY (game_id, night_number),
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS night_submissions (
                    game_id TEXT NOT NULL,
                    night_number INTEGER NOT NULL,
                    clan_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    orders_json TEXT NOT NULL,
                    submitted_at TEXT NOT NULL,
                    PRIMARY KEY (game_id, night_number, clan_id),
                    FOREIGN KEY (game_id, night_number) REFERENCES nights(game_id, night_number) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS night_reports (
                    game_id TEXT NOT NULL,
                    night_number INTEGER NOT NULL,
                    clan_id TEXT NOT NULL,
                    report_json TEXT NOT NULL,
                    PRIMARY KEY (game_id, night_number, clan_id),
                    FOREIGN KEY (game_id, night_number) REFERENCES nights(game_id, night_number) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS elysium_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    clan_id TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (game_id) REFERENCES games(id) ON DELETE CASCADE
                );
                """
            )

    def ensure_game(self, game_id: str, name: str, state: GameState, required_clans: tuple[str, ...]) -> None:
        now = utc_now()
        raw_state = game_state_to_json(state)
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            exists = con.execute("SELECT 1 FROM games WHERE id = ?", (game_id,)).fetchone()
            if not exists:
                con.execute(
                    "INSERT INTO games(id,name,current_night,state_json,required_clans_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                    (game_id, name, state.night, raw_state, json.dumps(required_clans), now, now),
                )
                con.execute(
                    "INSERT INTO nights(game_id,night_number,status,state_before_json,created_at) VALUES(?,?,?,?,?)",
                    (game_id, state.night, NightStatus.OPEN.value, raw_state, now),
                )
            con.commit()

    def get_game_state(self, game_id: str) -> GameState:
        with self._connect() as con:
            row = con.execute("SELECT state_json FROM games WHERE id = ?", (game_id,)).fetchone()
        if not row:
            raise ValueError(f"Unknown game: {game_id}")
        return game_state_from_json(row["state_json"])

    def get_game_info(self, game_id: str) -> dict:
        with self._connect() as con:
            row = con.execute(
                "SELECT id,name,current_night,required_clans_json FROM games WHERE id = ?",
                (game_id,),
            ).fetchone()
            if not row:
                raise ValueError(f"Unknown game: {game_id}")
            night = con.execute(
                "SELECT status FROM nights WHERE game_id = ? AND night_number = ?",
                (game_id, row["current_night"]),
            ).fetchone()
        return {
            "id": row["id"],
            "name": row["name"],
            "current_night": int(row["current_night"]),
            "required_clans": tuple(json.loads(row["required_clans_json"])),
            "night_status": NightStatus(night["status"]),
        }

    def claim_clan(self, game_id: str, player_id: str, player_name: str, clan_id: str) -> None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            game = con.execute("SELECT required_clans_json FROM games WHERE id = ?", (game_id,)).fetchone()
            if not game:
                raise ValueError(f"Unknown game: {game_id}")
            required = tuple(json.loads(game["required_clans_json"]))
            if clan_id not in required:
                raise ValueError(f"Clan not available in this game: {clan_id}")

            existing_player = con.execute(
                "SELECT clan_id FROM game_players WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
            if existing_player:
                if existing_player["clan_id"] != clan_id:
                    raise ValueError("A player can control only one clan in a game")
                con.commit()
                return

            existing_clan = con.execute(
                "SELECT player_id FROM game_players WHERE game_id = ? AND clan_id = ?",
                (game_id, clan_id),
            ).fetchone()
            if existing_clan and existing_clan["player_id"] != player_id:
                raise ValueError("This clan is already controlled by another player")

            con.execute(
                "INSERT INTO game_players(game_id,player_id,player_name,clan_id,claimed_at) VALUES(?,?,?,?,?)",
                (game_id, player_id, player_name.strip() or "Joueur", clan_id, utc_now()),
            )
            con.commit()

    def get_player_clan(self, game_id: str, player_id: str) -> str | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT clan_id FROM game_players WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
        return row["clan_id"] if row else None

    def list_assignments(self, game_id: str) -> dict[str, str]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT clan_id, player_name FROM game_players WHERE game_id = ? ORDER BY clan_id",
                (game_id,),
            ).fetchall()
        return {row["clan_id"]: row["player_name"] for row in rows}

    def submit_orders(self, game_id: str, player_id: str, orders: ClanNightOrders) -> NightStatus:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            game = con.execute(
                "SELECT current_night, required_clans_json FROM games WHERE id = ?",
                (game_id,),
            ).fetchone()
            if not game:
                raise ValueError(f"Unknown game: {game_id}")
            night_number = int(game["current_night"])
            night = con.execute(
                "SELECT status FROM nights WHERE game_id = ? AND night_number = ?",
                (game_id, night_number),
            ).fetchone()
            status = NightStatus(night["status"])
            if status not in (NightStatus.OPEN, NightStatus.READY):
                raise ValueError("This night no longer accepts orders")

            assignment = con.execute(
                "SELECT clan_id FROM game_players WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
            if not assignment or assignment["clan_id"] != orders.clan_id:
                raise ValueError("Player is not assigned to this clan")

            existing = con.execute(
                "SELECT 1 FROM night_submissions WHERE game_id = ? AND night_number = ? AND clan_id = ?",
                (game_id, night_number, orders.clan_id),
            ).fetchone()
            if existing:
                raise ValueError("Orders already submitted for this clan and night")

            con.execute(
                "INSERT INTO night_submissions(game_id,night_number,clan_id,player_id,orders_json,submitted_at) VALUES(?,?,?,?,?,?)",
                (game_id, night_number, orders.clan_id, player_id, clan_orders_to_json(orders), utc_now()),
            )
            required = tuple(json.loads(game["required_clans_json"]))
            rows = con.execute(
                "SELECT clan_id FROM night_submissions WHERE game_id = ? AND night_number = ?",
                (game_id, night_number),
            ).fetchall()
            submitted = {row["clan_id"] for row in rows}
            new_status = NightStatus.READY if set(required).issubset(submitted) else NightStatus.OPEN
            con.execute(
                "UPDATE nights SET status = ? WHERE game_id = ? AND night_number = ?",
                (new_status.value, game_id, night_number),
            )
            con.commit()
            return new_status

    def submission_statuses(self, game_id: str) -> dict[str, bool]:
        info = self.get_game_info(game_id)
        with self._connect() as con:
            rows = con.execute(
                "SELECT clan_id FROM night_submissions WHERE game_id = ? AND night_number = ?",
                (game_id, info["current_night"]),
            ).fetchall()
        submitted = {row["clan_id"] for row in rows}
        return {clan_id: clan_id in submitted for clan_id in info["required_clans"]}

    def try_begin_resolution(self, game_id: str) -> ResolutionBundle | None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            game = con.execute(
                "SELECT current_night FROM games WHERE id = ?", (game_id,)
            ).fetchone()
            if not game:
                raise ValueError(f"Unknown game: {game_id}")
            night_number = int(game["current_night"])
            night = con.execute(
                "SELECT status,state_before_json FROM nights WHERE game_id = ? AND night_number = ?",
                (game_id, night_number),
            ).fetchone()
            if NightStatus(night["status"]) != NightStatus.READY:
                con.commit()
                return None
            con.execute(
                "UPDATE nights SET status = ? WHERE game_id = ? AND night_number = ?",
                (NightStatus.RESOLVING.value, game_id, night_number),
            )
            rows = con.execute(
                "SELECT clan_id,orders_json FROM night_submissions WHERE game_id = ? AND night_number = ?",
                (game_id, night_number),
            ).fetchall()
            con.commit()
        return ResolutionBundle(
            game_id=game_id,
            night=night_number,
            state=game_state_from_json(night["state_before_json"]),
            orders_by_clan={row["clan_id"]: clan_orders_from_json(row["orders_json"]) for row in rows},
        )

    def abort_resolution(self, game_id: str, night: int) -> None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute(
                "UPDATE nights SET status = ? WHERE game_id = ? AND night_number = ? AND status = ?",
                (NightStatus.READY.value, game_id, night, NightStatus.RESOLVING.value),
            )
            con.commit()

    def finalize_resolution(
        self,
        bundle: ResolutionBundle,
        state: GameState,
        reports: dict[str, ClanNightReport],
    ) -> None:
        raw_state = game_state_to_json(state)
        now = utc_now()
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            current = con.execute(
                "SELECT status FROM nights WHERE game_id = ? AND night_number = ?",
                (bundle.game_id, bundle.night),
            ).fetchone()
            if not current or NightStatus(current["status"]) != NightStatus.RESOLVING:
                raise ValueError("Night is not locked for resolution")
            con.execute(
                "UPDATE nights SET status = ?, state_after_json = ?, resolved_at = ? WHERE game_id = ? AND night_number = ?",
                (NightStatus.RESOLVED.value, raw_state, now, bundle.game_id, bundle.night),
            )
            for report in reports.values():
                con.execute(
                    "INSERT OR REPLACE INTO night_reports(game_id,night_number,clan_id,report_json) VALUES(?,?,?,?)",
                    (bundle.game_id, bundle.night, report.clan_id, report_to_json(report)),
                )
            con.execute(
                "UPDATE games SET current_night = ?, state_json = ?, updated_at = ? WHERE id = ?",
                (state.night, raw_state, now, bundle.game_id),
            )
            con.execute(
                "INSERT INTO nights(game_id,night_number,status,state_before_json,created_at) VALUES(?,?,?,?,?)",
                (bundle.game_id, state.night, NightStatus.OPEN.value, raw_state, now),
            )
            con.commit()

    def get_report(self, game_id: str, night: int, clan_id: str) -> ClanNightReport | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT report_json FROM night_reports WHERE game_id = ? AND night_number = ? AND clan_id = ?",
                (game_id, night, clan_id),
            ).fetchone()
        return report_from_json(row["report_json"]) if row else None

    def list_reports(self, game_id: str, clan_id: str) -> list[ClanNightReport]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT report_json FROM night_reports WHERE game_id = ? AND clan_id = ? ORDER BY night_number DESC",
                (game_id, clan_id),
            ).fetchall()
        return [report_from_json(row["report_json"]) for row in rows]

    def post_elysium_message(self, game_id: str, player_id: str, clan_id: str, body: str) -> None:
        body = body.strip()
        if not body:
            raise ValueError("Message cannot be empty")
        if len(body) > 2000:
            raise ValueError("Message is too long")
        with self._connect() as con:
            assignment = con.execute(
                "SELECT clan_id FROM game_players WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
            if not assignment or assignment["clan_id"] != clan_id:
                raise ValueError("Player is not assigned to this clan")
            con.execute(
                "INSERT INTO elysium_messages(game_id,player_id,clan_id,body,created_at) VALUES(?,?,?,?,?)",
                (game_id, player_id, clan_id, body, utc_now()),
            )

    def list_elysium_messages(self, game_id: str, limit: int = 100) -> list[dict]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT m.id,m.clan_id,m.body,m.created_at,p.player_name
                FROM elysium_messages m
                JOIN game_players p ON p.game_id = m.game_id AND p.player_id = m.player_id
                WHERE m.game_id = ?
                ORDER BY m.id DESC
                LIMIT ?
                """,
                (game_id, limit),
            ).fetchall()
        return [dict(row) for row in reversed(rows)]
