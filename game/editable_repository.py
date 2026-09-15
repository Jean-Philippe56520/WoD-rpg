from __future__ import annotations

import json
from pathlib import Path

from .models import ClanNightOrders, GameState, NightStatus
from .persistence import SQLiteGameRepository
from .serialization import clan_orders_from_json
from .supabase_repository import SupabaseGameRepository


PRODUCTION_GAME_ID = "main"


class EditableSQLiteGameRepository(SQLiteGameRepository):
    """SQLite local avec consultation, retrait des ordres et reset de sandbox."""

    def get_submitted_orders(self, game_id: str, clan_id: str) -> ClanNightOrders | None:
        info = self.get_game_info(game_id)
        with self._connect() as con:
            row = con.execute(
                "SELECT orders_json FROM night_submissions "
                "WHERE game_id = ? AND night_number = ? AND clan_id = ?",
                (game_id, info["current_night"], clan_id),
            ).fetchone()
        return clan_orders_from_json(row["orders_json"]) if row else None

    def withdraw_orders(self, game_id: str, player_id: str, clan_id: str) -> None:
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            game = con.execute(
                "SELECT current_night FROM games WHERE id = ?", (game_id,)
            ).fetchone()
            if not game:
                raise ValueError(f"Unknown game: {game_id}")
            night_number = int(game["current_night"])
            night = con.execute(
                "SELECT status FROM nights WHERE game_id = ? AND night_number = ?",
                (game_id, night_number),
            ).fetchone()
            if not night or NightStatus(night["status"]) != NightStatus.OPEN:
                raise ValueError("Orders can no longer be withdrawn for this night")

            assignment = con.execute(
                "SELECT clan_id FROM game_players WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            ).fetchone()
            if not assignment or assignment["clan_id"] != clan_id:
                raise ValueError("Player is not assigned to this clan")

            deleted = con.execute(
                "DELETE FROM night_submissions "
                "WHERE game_id = ? AND night_number = ? AND clan_id = ? AND player_id = ?",
                (game_id, night_number, clan_id, player_id),
            ).rowcount
            if deleted != 1:
                raise ValueError("No submitted orders found for this clan and night")
            con.commit()

    def reset_game(
        self,
        game_id: str,
        name: str,
        state: GameState,
        required_clans: tuple[str, ...],
    ) -> None:
        if game_id == PRODUCTION_GAME_ID:
            raise ValueError("The production game cannot be reset")
        with self._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            con.execute("DELETE FROM games WHERE id = ?", (game_id,))
            con.commit()
        self.ensure_game(game_id, name, state, required_clans)


class EditableSupabaseGameRepository(SupabaseGameRepository):
    """Supabase serveur avec consultation, retrait des ordres et reset de sandbox."""

    def get_submitted_orders(self, game_id: str, clan_id: str) -> ClanNightOrders | None:
        info = self.get_game_info(game_id)
        rows = self.client.select(
            "wod_night_submissions",
            "orders_json",
            filters={
                "game_id": game_id,
                "night_number": info["current_night"],
                "clan_id": clan_id,
            },
            limit=1,
        )
        if not rows:
            return None
        return clan_orders_from_json(json.dumps(rows[0]["orders_json"]))

    def withdraw_orders(self, game_id: str, player_id: str, clan_id: str) -> None:
        self.client.rpc(
            "wod_withdraw_orders",
            {
                "p_game_id": game_id,
                "p_player_id": player_id,
                "p_clan_id": clan_id,
            },
        )

    def reset_game(
        self,
        game_id: str,
        name: str,
        state: GameState,
        required_clans: tuple[str, ...],
    ) -> None:
        if game_id == PRODUCTION_GAME_ID:
            raise ValueError("The production game cannot be reset")
        self.client._request(
            "DELETE",
            "/wod_games",
            params={"id": f"eq.{game_id}"},
            prefer="return=minimal",
        )
        self.ensure_game(game_id, name, state, required_clans)
