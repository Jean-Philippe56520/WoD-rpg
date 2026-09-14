from __future__ import annotations

import json
from typing import Any

from .models import ClanNightOrders, ClanNightReport, GameState, NightStatus
from .persistence import GameRepository, ResolutionBundle
from .serialization import (
    clan_orders_from_json,
    clan_orders_to_json,
    game_state_from_json,
    game_state_to_json,
    report_from_json,
    report_to_json,
)


def _json_value(raw: str) -> Any:
    return json.loads(raw)


def _as_scalar(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


class SupabaseGameRepository(GameRepository):
    """Persistent repository backed by Supabase using a server secret key.

    The key used here must remain server-side (Streamlit secrets). Players never
    receive it. Direct player-facing access remains protected by RLS.
    """

    def __init__(self, url: str, secret_key: str):
        if not url or not secret_key:
            raise ValueError("Supabase URL and server secret key are required")
        try:
            from supabase import create_client
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("The 'supabase' package is required for Supabase persistence") from exc
        self.client = create_client(url, secret_key)

    def ensure_game(
        self,
        game_id: str,
        name: str,
        state: GameState,
        required_clans: tuple[str, ...],
    ) -> None:
        self.client.rpc(
            "wod_ensure_game",
            {
                "p_game_id": game_id,
                "p_name": name,
                "p_current_night": state.night,
                "p_required_clans": list(required_clans),
                "p_state_json": _json_value(game_state_to_json(state)),
            },
        ).execute()

    def get_game_state(self, game_id: str) -> GameState:
        rows = (
            self.client.table("wod_game_states")
            .select("state_json")
            .eq("game_id", game_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            raise ValueError(f"Unknown game: {game_id}")
        return game_state_from_json(json.dumps(rows[0]["state_json"]))

    def get_game_info(self, game_id: str) -> dict:
        rows = (
            self.client.table("wod_games")
            .select("id,name,current_night,required_clans")
            .eq("id", game_id)
            .limit(1)
            .execute()
            .data
        )
        if not rows:
            raise ValueError(f"Unknown game: {game_id}")
        game = rows[0]
        nights = (
            self.client.table("wod_nights")
            .select("status")
            .eq("game_id", game_id)
            .eq("night_number", game["current_night"])
            .limit(1)
            .execute()
            .data
        )
        if not nights:
            raise ValueError("Current night is missing")
        return {
            "id": game["id"],
            "name": game["name"],
            "current_night": int(game["current_night"]),
            "required_clans": tuple(game["required_clans"]),
            "night_status": NightStatus(nights[0]["status"]),
        }

    def claim_clan(self, game_id: str, player_id: str, player_name: str, clan_id: str) -> None:
        info = self.get_game_info(game_id)
        if clan_id not in info["required_clans"]:
            raise ValueError(f"Clan not available in this game: {clan_id}")
        existing_player = (
            self.client.table("wod_game_players")
            .select("clan_id")
            .eq("game_id", game_id)
            .eq("player_id", player_id)
            .limit(1)
            .execute()
            .data
        )
        if existing_player:
            if existing_player[0]["clan_id"] != clan_id:
                raise ValueError("A player can control only one clan in a game")
            return
        occupied = (
            self.client.table("wod_game_players")
            .select("player_id")
            .eq("game_id", game_id)
            .eq("clan_id", clan_id)
            .limit(1)
            .execute()
            .data
        )
        if occupied:
            raise ValueError("This clan is already controlled by another player")
        try:
            self.client.table("wod_game_players").insert(
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "player_name": player_name.strip() or "Joueur",
                    "clan_id": clan_id,
                }
            ).execute()
        except Exception as exc:
            text = str(exc).lower()
            if "duplicate" in text or "unique" in text:
                raise ValueError("This clan is already controlled by another player") from exc
            raise

    def get_player_clan(self, game_id: str, player_id: str) -> str | None:
        rows = (
            self.client.table("wod_game_players")
            .select("clan_id")
            .eq("game_id", game_id)
            .eq("player_id", player_id)
            .limit(1)
            .execute()
            .data
        )
        return rows[0]["clan_id"] if rows else None

    def list_assignments(self, game_id: str) -> dict[str, str]:
        rows = (
            self.client.table("wod_game_players")
            .select("clan_id,player_name")
            .eq("game_id", game_id)
            .execute()
            .data
        )
        return {row["clan_id"]: row["player_name"] for row in rows}

    def submit_orders(self, game_id: str, player_id: str, orders: ClanNightOrders) -> NightStatus:
        result = self.client.rpc(
            "wod_submit_orders",
            {
                "p_game_id": game_id,
                "p_player_id": player_id,
                "p_clan_id": orders.clan_id,
                "p_orders_json": _json_value(clan_orders_to_json(orders)),
            },
        ).execute().data
        return NightStatus(str(_as_scalar(result)))

    def submission_statuses(self, game_id: str) -> dict[str, bool]:
        info = self.get_game_info(game_id)
        rows = (
            self.client.table("wod_night_submissions")
            .select("clan_id")
            .eq("game_id", game_id)
            .eq("night_number", info["current_night"])
            .execute()
            .data
        )
        submitted = {row["clan_id"] for row in rows}
        return {clan_id: clan_id in submitted for clan_id in info["required_clans"]}

    def try_begin_resolution(self, game_id: str) -> ResolutionBundle | None:
        raw = _as_scalar(
            self.client.rpc("wod_try_begin_resolution", {"p_game_id": game_id}).execute().data
        )
        if raw is None:
            return None
        state = game_state_from_json(json.dumps(raw["state_json"]))
        orders_by_clan = {
            clan_id: clan_orders_from_json(json.dumps(payload))
            for clan_id, payload in raw["orders_by_clan"].items()
        }
        return ResolutionBundle(
            game_id=raw["game_id"],
            night=int(raw["night"]),
            state=state,
            orders_by_clan=orders_by_clan,
        )

    def abort_resolution(self, game_id: str, night: int) -> None:
        self.client.rpc(
            "wod_abort_resolution", {"p_game_id": game_id, "p_night": night}
        ).execute()

    def finalize_resolution(
        self,
        bundle: ResolutionBundle,
        state: GameState,
        reports: dict[str, ClanNightReport],
    ) -> None:
        self.client.rpc(
            "wod_finalize_resolution",
            {
                "p_game_id": bundle.game_id,
                "p_night": bundle.night,
                "p_next_night": state.night,
                "p_state_json": _json_value(game_state_to_json(state)),
                "p_reports": {
                    clan_id: _json_value(report_to_json(report))
                    for clan_id, report in reports.items()
                },
            },
        ).execute()

    def get_report(self, game_id: str, night: int, clan_id: str) -> ClanNightReport | None:
        rows = (
            self.client.table("wod_night_reports")
            .select("report_json")
            .eq("game_id", game_id)
            .eq("night_number", night)
            .eq("clan_id", clan_id)
            .limit(1)
            .execute()
            .data
        )
        return report_from_json(json.dumps(rows[0]["report_json"])) if rows else None

    def list_reports(self, game_id: str, clan_id: str) -> list[ClanNightReport]:
        rows = (
            self.client.table("wod_night_reports")
            .select("report_json,night_number")
            .eq("game_id", game_id)
            .eq("clan_id", clan_id)
            .order("night_number", desc=True)
            .execute()
            .data
        )
        return [report_from_json(json.dumps(row["report_json"])) for row in rows]

    def post_elysium_message(self, game_id: str, player_id: str, clan_id: str, body: str) -> None:
        body = body.strip()
        if not body:
            raise ValueError("Message cannot be empty")
        if len(body) > 2000:
            raise ValueError("Message is too long")
        assigned = self.get_player_clan(game_id, player_id)
        if assigned != clan_id:
            raise ValueError("Player is not assigned to this clan")
        self.client.table("wod_elysium_messages").insert(
            {
                "game_id": game_id,
                "player_id": player_id,
                "clan_id": clan_id,
                "body": body,
            }
        ).execute()

    def list_elysium_messages(self, game_id: str, limit: int = 100) -> list[dict]:
        players = (
            self.client.table("wod_game_players")
            .select("player_id,player_name")
            .eq("game_id", game_id)
            .execute()
            .data
        )
        names = {row["player_id"]: row["player_name"] for row in players}
        rows = (
            self.client.table("wod_elysium_messages")
            .select("id,player_id,clan_id,body,created_at")
            .eq("game_id", game_id)
            .order("id", desc=True)
            .limit(limit)
            .execute()
            .data
        )
        result = []
        for row in reversed(rows):
            result.append(
                {
                    "id": row["id"],
                    "clan_id": row["clan_id"],
                    "body": row["body"],
                    "created_at": row["created_at"],
                    "player_name": names.get(row["player_id"], "Joueur"),
                }
            )
        return result
