from __future__ import annotations

import base64
import json
from typing import Any

import httpx

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


def _jwt_role(token: str) -> str | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    role = decoded.get("role")
    return str(role) if role else None


def _server_headers(secret_key: str) -> dict[str, str]:
    key = secret_key.strip()
    if key.startswith("sb_publishable_"):
        raise ValueError("A Supabase publishable key cannot be used as the server secret key")

    headers = {
        "apikey": key,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    if key.startswith("sb_secret_"):
        return headers

    role = _jwt_role(key)
    if role != "service_role":
        raise ValueError(
            "SUPABASE_SECRET_KEY must be an sb_secret_ key or a legacy service_role JWT"
        )
    headers["Authorization"] = f"Bearer {key}"
    return headers


class SupabaseRestError(RuntimeError):
    def __init__(self, status_code: int, code: str | None, message: str):
        self.status_code = status_code
        self.code = code
        self.api_message = message
        label = f"HTTP {status_code}"
        if code:
            label += f", {code}"
        super().__init__(f"Supabase API error ({label}): {message}")


class _PostgrestServerClient:
    def __init__(
        self,
        url: str,
        secret_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        if not url or not secret_key:
            raise ValueError("Supabase URL and server secret key are required")
        self.http = httpx.Client(
            base_url=f"{url.rstrip('/')}/rest/v1",
            headers=_server_headers(secret_key),
            timeout=20.0,
            transport=transport,
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        payload: Any = None,
        prefer: str | None = None,
    ) -> Any:
        headers = {"Prefer": prefer} if prefer else None
        try:
            response = self.http.request(
                method,
                path,
                params=params,
                json=payload,
                headers=headers,
            )
        except httpx.HTTPError as exc:
            raise RuntimeError("Unable to reach the Supabase Data API") from exc

        if response.is_error:
            code = None
            message = "Request rejected"
            try:
                error = response.json()
                if isinstance(error, dict):
                    code = str(error.get("code")) if error.get("code") else None
                    raw_message = error.get("message") or error.get("error")
                    if raw_message:
                        message = str(raw_message)
            except ValueError:
                pass
            raise SupabaseRestError(response.status_code, code, message)

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def rpc(self, function_name: str, payload: dict[str, Any]) -> Any:
        return self._request("POST", f"/rpc/{function_name}", payload=payload)

    def select(
        self,
        table: str,
        columns: str,
        *,
        filters: dict[str, Any] | None = None,
        limit: int | None = None,
        order: str | None = None,
    ) -> list[dict[str, Any]]:
        params = {"select": columns}
        for column, value in (filters or {}).items():
            params[column] = f"eq.{value}"
        if limit is not None:
            params["limit"] = str(limit)
        if order:
            params["order"] = order
        result = self._request("GET", f"/{table}", params=params)
        return result or []

    def insert(self, table: str, payload: dict[str, Any]) -> None:
        self._request(
            "POST",
            f"/{table}",
            payload=payload,
            prefer="return=minimal",
        )


class SupabaseGameRepository(GameRepository):
    """Persistent repository backed by the Supabase Data API.

    New ``sb_secret_`` keys are sent only as ``apikey`` as required by the
    current Supabase key model. Legacy ``service_role`` JWT keys keep the
    Authorization header for backwards compatibility.
    """

    def __init__(
        self,
        url: str,
        secret_key: str,
        *,
        transport: httpx.BaseTransport | None = None,
    ):
        self.client = _PostgrestServerClient(url, secret_key, transport=transport)

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
        )

    def get_game_state(self, game_id: str) -> GameState:
        rows = self.client.select(
            "wod_game_states", "state_json", filters={"game_id": game_id}, limit=1
        )
        if not rows:
            raise ValueError(f"Unknown game: {game_id}")
        return game_state_from_json(json.dumps(rows[0]["state_json"]))

    def get_game_info(self, game_id: str) -> dict:
        rows = self.client.select(
            "wod_games",
            "id,name,current_night,required_clans",
            filters={"id": game_id},
            limit=1,
        )
        if not rows:
            raise ValueError(f"Unknown game: {game_id}")
        game = rows[0]
        nights = self.client.select(
            "wod_nights",
            "status",
            filters={"game_id": game_id, "night_number": game["current_night"]},
            limit=1,
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
        existing_player = self.client.select(
            "wod_game_players",
            "clan_id",
            filters={"game_id": game_id, "player_id": player_id},
            limit=1,
        )
        if existing_player:
            if existing_player[0]["clan_id"] != clan_id:
                raise ValueError("A player can control only one clan in a game")
            return
        occupied = self.client.select(
            "wod_game_players",
            "player_id",
            filters={"game_id": game_id, "clan_id": clan_id},
            limit=1,
        )
        if occupied:
            raise ValueError("This clan is already controlled by another player")
        try:
            self.client.insert(
                "wod_game_players",
                {
                    "game_id": game_id,
                    "player_id": player_id,
                    "player_name": player_name.strip() or "Joueur",
                    "clan_id": clan_id,
                },
            )
        except SupabaseRestError as exc:
            if exc.code == "23505" or exc.status_code == 409:
                raise ValueError("This clan is already controlled by another player") from exc
            raise

    def get_player_clan(self, game_id: str, player_id: str) -> str | None:
        rows = self.client.select(
            "wod_game_players",
            "clan_id",
            filters={"game_id": game_id, "player_id": player_id},
            limit=1,
        )
        return rows[0]["clan_id"] if rows else None

    def list_assignments(self, game_id: str) -> dict[str, str]:
        rows = self.client.select(
            "wod_game_players",
            "clan_id,player_name",
            filters={"game_id": game_id},
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
        )
        return NightStatus(str(_as_scalar(result)))

    def submission_statuses(self, game_id: str) -> dict[str, bool]:
        info = self.get_game_info(game_id)
        rows = self.client.select(
            "wod_night_submissions",
            "clan_id",
            filters={"game_id": game_id, "night_number": info["current_night"]},
        )
        submitted = {row["clan_id"] for row in rows}
        return {clan_id: clan_id in submitted for clan_id in info["required_clans"]}

    def try_begin_resolution(self, game_id: str) -> ResolutionBundle | None:
        raw = _as_scalar(self.client.rpc("wod_try_begin_resolution", {"p_game_id": game_id}))
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
        self.client.rpc("wod_abort_resolution", {"p_game_id": game_id, "p_night": night})

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
        )

    def get_report(self, game_id: str, night: int, clan_id: str) -> ClanNightReport | None:
        rows = self.client.select(
            "wod_night_reports",
            "report_json",
            filters={"game_id": game_id, "night_number": night, "clan_id": clan_id},
            limit=1,
        )
        return report_from_json(json.dumps(rows[0]["report_json"])) if rows else None

    def list_reports(self, game_id: str, clan_id: str) -> list[ClanNightReport]:
        rows = self.client.select(
            "wod_night_reports",
            "report_json,night_number",
            filters={"game_id": game_id, "clan_id": clan_id},
            order="night_number.desc",
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
        self.client.insert(
            "wod_elysium_messages",
            {"game_id": game_id, "player_id": player_id, "clan_id": clan_id, "body": body},
        )

    def list_elysium_messages(self, game_id: str, limit: int = 100) -> list[dict]:
        players = self.client.select(
            "wod_game_players",
            "player_id,player_name",
            filters={"game_id": game_id},
        )
        names = {row["player_id"]: row["player_name"] for row in players}
        rows = self.client.select(
            "wod_elysium_messages",
            "id,player_id,clan_id,body,created_at",
            filters={"game_id": game_id},
            order="id.desc",
            limit=limit,
        )
        return [
            {
                "id": row["id"],
                "clan_id": row["clan_id"],
                "body": row["body"],
                "created_at": row["created_at"],
                "player_name": names.get(row["player_id"], "Joueur"),
            }
            for row in reversed(rows)
        ]
