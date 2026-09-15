from __future__ import annotations

import json
from typing import Any

from .chronicle_simulation import (
    SimulationState,
    initial_simulation,
    simulation_from_dict,
    simulation_to_dict,
)


class ChronicleSimulationStore:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._is_supabase = hasattr(self.repository, "client")
        if not self._is_supabase:
            self._ensure_sqlite_schema()

    def _ensure_sqlite_schema(self) -> None:
        with self.repository._connect() as con:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS wod_chronicle_simulations (
                    game_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                """
            )

    def get(self, game_id: str) -> SimulationState | None:
        if self._is_supabase:
            rows = self.repository.client.select(
                "wod_chronicle_simulations",
                "state_json",
                filters={"game_id": game_id},
                limit=1,
            )
            return simulation_from_dict(rows[0]["state_json"]) if rows else None
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT state_json FROM wod_chronicle_simulations WHERE game_id = ?",
                (game_id,),
            ).fetchone()
        return simulation_from_dict(json.loads(row["state_json"])) if row else None

    def ensure(self, game_id: str, *, year: int = 1435) -> SimulationState:
        existing = self.get(game_id)
        if existing is not None:
            return existing
        state = initial_simulation(game_id, year)
        return self.save(state)

    def save(self, state: SimulationState) -> SimulationState:
        payload = simulation_to_dict(state)
        if self._is_supabase:
            raw = self.repository.client.rpc(
                "wod_upsert_chronicle_simulation",
                {"p_game_id": state.game_id, "p_state": payload},
            )
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected simulation persistence response")
            return simulation_from_dict(raw)
        with self.repository._connect() as con:
            con.execute(
                """
                INSERT INTO wod_chronicle_simulations(game_id,state_json)
                VALUES(?,?)
                ON CONFLICT(game_id) DO UPDATE SET
                    state_json=excluded.state_json,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (state.game_id, json.dumps(payload, ensure_ascii=False)),
            )
        return state
