from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from .chronicle import NightOutcome, PersonalAction, PlayerCharacter
from .chronicle_store import ChronicleStore
from .night_cycle import MAX_FREE_ACTIONS, NightPhase, NightStepResult, NightTurnState, log_entry


class NightCycleStore:
    def __init__(self, repository: Any):
        self.repository = getattr(repository, "delegate", repository)
        self._supabase = hasattr(self.repository, "client")
        if not self._supabase:
            with self.repository._connect() as con:
                con.executescript("""
                CREATE TABLE IF NOT EXISTS wod_character_night_state (
                    game_id TEXT NOT NULL, player_id TEXT NOT NULL, character_id TEXT NOT NULL,
                    chapter INTEGER NOT NULL, segment INTEGER NOT NULL, night_number INTEGER NOT NULL,
                    phase TEXT NOT NULL CHECK (phase IN ('event','free_actions')),
                    event_id TEXT NOT NULL, remaining_actions INTEGER NOT NULL DEFAULT 0,
                    max_actions INTEGER NOT NULL DEFAULT 2, log_json TEXT NOT NULL DEFAULT '[]',
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (game_id, player_id),
                    FOREIGN KEY (game_id, player_id) REFERENCES wod_player_characters(game_id, player_id) ON DELETE CASCADE
                );
                """)

    @staticmethod
    def _from_row(row: dict[str, Any]) -> NightTurnState:
        raw = row.get("log_json", [])
        if isinstance(raw, str):
            raw = json.loads(raw)
        return NightTurnState(
            game_id=str(row["game_id"]), player_id=str(row["player_id"]),
            character_id=str(row["character_id"]), chapter=int(row["chapter"]),
            segment=int(row["segment"]), night_number=int(row["night_number"]),
            phase=NightPhase(str(row["phase"])), event_id=str(row["event_id"]),
            remaining_actions=int(row["remaining_actions"]),
            max_actions=int(row.get("max_actions", MAX_FREE_ACTIONS)), log=tuple(raw or ()),
        )

    @staticmethod
    def _matches(state: NightTurnState, character: PlayerCharacter) -> bool:
        return (
            state.character_id == character.character_id
            and state.chapter == character.chapter
            and state.segment == character.segment
            and state.night_number == character.local_night
            and not character.ready_for_convergence
        )

    def get_state(self, game_id: str, player_id: str) -> NightTurnState | None:
        if self._supabase:
            rows = self.repository.client.select(
                "wod_character_night_state", "*", filters={"game_id": game_id, "player_id": player_id}, limit=1
            )
            return self._from_row(rows[0]) if rows else None
        with self.repository._connect() as con:
            row = con.execute(
                "SELECT * FROM wod_character_night_state WHERE game_id=? AND player_id=?", (game_id, player_id)
            ).fetchone()
        return self._from_row(dict(row)) if row else None

    def ensure(self, character: PlayerCharacter, *, event_id: str) -> NightTurnState:
        if character.ready_for_convergence:
            raise ValueError("Cannot open a night cycle while waiting for convergence")
        if self._supabase:
            raw = self.repository.client.rpc("wod_ensure_night_cycle_state", {
                "p_game_id": character.game_id, "p_player_id": character.player_id,
                "p_character_id": character.character_id, "p_chapter": character.chapter,
                "p_segment": character.segment, "p_night_number": character.local_night,
                "p_event_id": event_id, "p_max_actions": MAX_FREE_ACTIONS,
            })
            if isinstance(raw, list) and len(raw) == 1:
                raw = raw[0]
            if not isinstance(raw, dict):
                raise RuntimeError("Unexpected night-cycle state response")
            return self._from_row(raw)

        current = self.get_state(character.game_id, character.player_id)
        if current is not None and self._matches(current, character):
            if (
                current.phase == NightPhase.EVENT
                and not current.log
                and current.event_id != event_id
            ):
                with self.repository._connect() as con:
                    con.execute(
                        """
                        UPDATE wod_character_night_state
                        SET event_id=?, updated_at=CURRENT_TIMESTAMP
                        WHERE game_id=? AND player_id=? AND phase='event' AND log_json='[]'
                        """,
                        (event_id, character.game_id, character.player_id),
                    )
                refreshed = self.get_state(character.game_id, character.player_id)
                if refreshed is None:
                    raise RuntimeError("Night-cycle state vanished during event recovery")
                return refreshed
            return current
        with self.repository._connect() as con:
            con.execute("""
                INSERT INTO wod_character_night_state(
                    game_id,player_id,character_id,chapter,segment,night_number,phase,event_id,
                    remaining_actions,max_actions,log_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(game_id,player_id) DO UPDATE SET
                    character_id=excluded.character_id, chapter=excluded.chapter, segment=excluded.segment,
                    night_number=excluded.night_number, phase=excluded.phase, event_id=excluded.event_id,
                    remaining_actions=0, max_actions=excluded.max_actions, log_json='[]', updated_at=CURRENT_TIMESTAMP
            """, (
                character.game_id, character.player_id, character.character_id, character.chapter,
                character.segment, character.local_night, NightPhase.EVENT.value, event_id,
                0, MAX_FREE_ACTIONS, "[]",
            ))
        state = self.get_state(character.game_id, character.player_id)
        if state is None:
            raise RuntimeError("Night-cycle state was not created")
        return state

    def _persist(self, before: PlayerCharacter, after: PlayerCharacter, old: NightTurnState, new: NightTurnState) -> None:
        if not self._matches(old, before):
            raise ValueError("Night state is stale")
        payload = {
            "p_game_id": before.game_id, "p_player_id": before.player_id,
            "p_expected_chapter": before.chapter, "p_expected_segment": before.segment,
            "p_expected_night": before.local_night, "p_expected_phase": old.phase.value,
            "p_expected_log_count": len(old.log), "p_phase": new.phase.value,
            "p_event_id": new.event_id, "p_remaining_actions": new.remaining_actions,
            "p_max_actions": new.max_actions, "p_log": list(new.log),
            "p_hunger": after.hunger, "p_reputation": after.reputation,
            "p_personal_influence": after.personal_influence, "p_sire_relation": after.sire_relation,
            "p_goal_progress": after.goal_progress,
        }
        if self._supabase:
            self.repository.client.rpc("wod_apply_night_cycle_step", payload)
            return
        with self.repository._connect() as con:
            con.execute("BEGIN IMMEDIATE")
            row = con.execute(
                "SELECT * FROM wod_player_characters WHERE game_id=? AND player_id=?", (before.game_id, before.player_id)
            ).fetchone()
            if row is None:
                raise ValueError("Unknown player character")
            current = ChronicleStore._character_from_row(dict(row))
            if current.chapter != before.chapter or current.segment != before.segment or current.local_night != before.local_night or current.ready_for_convergence:
                raise ValueError("Character night changed before step submission")
            cycle = con.execute(
                "SELECT * FROM wod_character_night_state WHERE game_id=? AND player_id=?", (before.game_id, before.player_id)
            ).fetchone()
            if cycle is None:
                raise ValueError("Night-cycle state is missing")
            current_state = self._from_row(dict(cycle))
            if not self._matches(current_state, before) or current_state.phase != old.phase or len(current_state.log) != len(old.log):
                raise ValueError("Night-cycle state changed before step submission")
            con.execute("""
                UPDATE wod_player_characters SET hunger=?, reputation=?, personal_influence=?, sire_relation=?,
                    goal_progress=?, updated_at=CURRENT_TIMESTAMP WHERE game_id=? AND player_id=?
            """, (after.hunger, after.reputation, after.personal_influence, after.sire_relation,
                   after.goal_progress, before.game_id, before.player_id))
            con.execute("""
                UPDATE wod_character_night_state SET phase=?, event_id=?, remaining_actions=?, max_actions=?,
                    log_json=?, updated_at=CURRENT_TIMESTAMP WHERE game_id=? AND player_id=?
            """, (new.phase.value, new.event_id, new.remaining_actions, new.max_actions,
                   json.dumps(list(new.log), ensure_ascii=False), before.game_id, before.player_id))
            con.commit()

    def apply_event(self, character: PlayerCharacter, state: NightTurnState, result: NightStepResult) -> NightTurnState:
        if state.phase != NightPhase.EVENT or result.resolution.situation.id != state.event_id:
            raise ValueError("Opening event does not match persistent night state")
        new = replace(state, phase=NightPhase.FREE_ACTIONS, remaining_actions=result.remaining_actions,
                      log=state.log + (log_entry("event", result),))
        self._persist(character, result.resolution.outcome.updated_character, state, new)
        return new

    def apply_free_action(self, character: PlayerCharacter, state: NightTurnState, result: NightStepResult) -> NightTurnState:
        if state.phase != NightPhase.FREE_ACTIONS or state.remaining_actions <= 0:
            raise ValueError("No free action is available")
        new = replace(state, remaining_actions=result.remaining_actions,
                      log=state.log + (log_entry("free_action", result),))
        self._persist(character, result.resolution.outcome.updated_character, state, new)
        return new

    def finish_night(self, character: PlayerCharacter, state: NightTurnState, *, nights_per_segment: int) -> PlayerCharacter:
        if not self._matches(state, character) or state.phase == NightPhase.EVENT:
            raise ValueError("Opening event must be resolved before ending the night")
        ready = character.local_night >= nights_per_segment
        updated = replace(
            character,
            local_night=character.local_night if ready else character.local_night + 1,
            ready_for_convergence=ready,
        )
        last_action = PersonalAction.PURSUE_GOAL
        if state.log:
            try:
                last_action = PersonalAction(str(state.log[-1].get("legacy_action", "")))
            except ValueError:
                pass
        action_count = sum(item.get("kind") == "free_action" for item in state.log)
        details = [
            f"{item.get('title')} — {item.get('consequence')}"
            for item in state.log if item.get("title") and item.get("consequence")
        ]
        outcome = NightOutcome(
            action=last_action,
            roll=sum(int(item.get("successes", 0)) for item in state.log),
            summary=f"Nuit achevée : événement résolu, {action_count} action(s) libre(s) entreprise(s).",
            detail=" ".join(details) or "La nuit s'achève sans autre fait notable.",
            updated_character=updated,
            tags=("night_cycle", "event_then_free_actions"),
        )
        return ChronicleStore(self.repository).advance_personal_night(character, outcome)
