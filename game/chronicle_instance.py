from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import uuid
from typing import Any

from .chronicle import (
    CHRONICLE_GAME_ID,
    CHRONICLE_NAME,
    ChronicleProgress,
    SUPPORTED_CLANS,
)
from .chronicle_politics import validate_political_state
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .chronicle_world_store import ChronicleWorldStore
from .era import era_for_year
from .models import GameState
from .vampire_profile_store import VampireProfileStore


PERSONAL_CHRONICLE_PREFIX = "chronicle_solo_"


@dataclass(frozen=True)
class PersonalChronicleContext:
    game_id: str
    migrated_legacy: bool = False


def personal_chronicle_game_id(player_id: str) -> str:
    """Return a stable private game id without exposing the account identifier."""

    normalized = player_id.strip()
    if not normalized:
        raise ValueError("Player id is required for a personal chronicle")
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]
    return f"{PERSONAL_CHRONICLE_PREFIX}{digest}"


def _copy_history(repository: Any, source_game_id: str, target_game_id: str, character_id: str) -> None:
    base = getattr(repository, "delegate", repository)
    if hasattr(base, "client"):
        rows = base.client.select(
            "wod_character_night_history",
            "character_id,chapter,segment,night_number,action,outcome_json",
            filters={"game_id": source_game_id, "character_id": character_id},
            order="created_at.asc",
            limit=1000,
        )
        for row in rows:
            payload = dict(row)
            payload["game_id"] = target_game_id
            base.client.insert("wod_character_night_history", payload)
        return

    with base._connect() as con:
        rows = con.execute(
            """
            SELECT character_id,chapter,segment,night_number,action,outcome_json
            FROM wod_character_night_history
            WHERE game_id = ? AND character_id = ?
            ORDER BY created_at, chapter, segment, night_number
            """,
            (source_game_id, character_id),
        ).fetchall()
        for row in rows:
            item = dict(row)
            con.execute(
                """
                INSERT OR IGNORE INTO wod_character_night_history(
                    game_id,character_id,chapter,segment,night_number,action,outcome_json
                ) VALUES(?,?,?,?,?,?,?)
                """,
                (
                    target_game_id,
                    item["character_id"],
                    item["chapter"],
                    item["segment"],
                    item["night_number"],
                    item["action"],
                    item["outcome_json"],
                ),
            )


def _copy_world_events(
    repository: Any,
    source_game_id: str,
    target_game_id: str,
    *,
    excluded_actor_ids: set[str],
) -> None:
    base = getattr(repository, "delegate", repository)
    if hasattr(base, "client"):
        rows = base.client.select(
            "wod_chronicle_world_events",
            "year,chapter,segment,actor_id,actor_name,category,public_text,hidden_intent",
            filters={"game_id": source_game_id},
            order="created_at.asc",
            limit=1000,
        )
        for row in rows:
            if str(row["actor_id"]) in excluded_actor_ids:
                continue
            payload = dict(row)
            payload["id"] = f"world_{uuid.uuid4().hex}"
            payload["game_id"] = target_game_id
            base.client.insert("wod_chronicle_world_events", payload)
        return

    with base._connect() as con:
        rows = con.execute(
            """
            SELECT year,chapter,segment,actor_id,actor_name,category,public_text,hidden_intent
            FROM wod_chronicle_world_events
            WHERE game_id = ?
            ORDER BY created_at, id
            """,
            (source_game_id,),
        ).fetchall()
        for row in rows:
            item = dict(row)
            if str(item["actor_id"]) in excluded_actor_ids:
                continue
            con.execute(
                """
                INSERT INTO wod_chronicle_world_events(
                    id,game_id,year,chapter,segment,actor_id,actor_name,category,public_text,hidden_intent
                ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    f"world_{uuid.uuid4().hex}",
                    target_game_id,
                    item["year"],
                    item["chapter"],
                    item["segment"],
                    item["actor_id"],
                    item["actor_name"],
                    item["category"],
                    item["public_text"],
                    item["hidden_intent"],
                ),
            )


def _personalize_legacy_simulation(
    simulation,
    *,
    game_id: str,
    excluded_character_ids: set[str],
):
    domains = {
        domain_id: (
            replace(domain, holder_id=None)
            if domain.holder_id in excluded_character_ids
            else domain
        )
        for domain_id, domain in simulation.domains.items()
    }
    hunting_rights = {
        right_id: right
        for right_id, right in simulation.hunting_rights.items()
        if right.beneficiary_id not in excluded_character_ids
        and right.granted_by_id not in excluded_character_ids
    }
    boons = {
        boon_id: boon
        for boon_id, boon in simulation.boons.items()
        if boon.creditor_id not in excluded_character_ids
        and boon.debtor_id not in excluded_character_ids
    }
    offices = {
        slot: holder_id
        for slot, holder_id in simulation.offices.items()
        if holder_id not in excluded_character_ids
    }
    npcs = {
        npc_id: replace(
            npc,
            relations={
                actor_id: score
                for actor_id, score in npc.relations.items()
                if actor_id not in excluded_character_ids
            },
        )
        for npc_id, npc in simulation.npcs.items()
    }
    return replace(
        simulation,
        game_id=game_id,
        npcs=npcs,
        domains=domains,
        hunting_rights=hunting_rights,
        boons=boons,
        offices=offices,
    )


def ensure_personal_chronicle(
    repository: Any,
    *,
    player_id: str,
) -> PersonalChronicleContext:
    """Ensure one isolated Chronicle game per account and migrate legacy data once.

    V0.21-V0.41 stored every player in ``chronicle_1435``. V0.42 keeps that
    legacy game untouched, creates a deterministic per-account game, and copies
    the current player's progress when possible. New writes then stay isolated.
    """

    game_id = personal_chronicle_game_id(player_id)
    repository.ensure_game(
        game_id,
        CHRONICLE_NAME,
        GameState(),
        SUPPORTED_CLANS,
    )

    store = ChronicleStore(repository)
    profile_store = VampireProfileStore(repository)
    simulation_store = ChronicleSimulationStore(repository)
    # Ensures the event table exists for SQLite before a possible legacy copy.
    ChronicleWorldStore(repository)

    existing_characters = store.list_characters(game_id)
    foreign_characters = [item for item in existing_characters if item.player_id != player_id]
    if foreign_characters:
        raise ValueError("A personal chronicle cannot contain another player's character")

    target_character = store.get_character(game_id, player_id)
    legacy_character = None
    legacy_characters = []
    if target_character is None:
        legacy_character = store.get_character(CHRONICLE_GAME_ID, player_id)
        if legacy_character is not None:
            legacy_characters = store.list_characters(CHRONICLE_GAME_ID)

    target_progress = store.get_progress(game_id)
    if target_progress is None:
        legacy_progress = store.get_progress(CHRONICLE_GAME_ID) if legacy_character is not None else None
        if legacy_progress is not None:
            target_progress = store.ensure_progress(replace(legacy_progress, game_id=game_id))
        else:
            target_progress = store.ensure_progress(ChronicleProgress(game_id=game_id))

    if target_character is not None or legacy_character is None:
        return PersonalChronicleContext(game_id=game_id, migrated_legacy=False)

    migrated_character = replace(legacy_character, game_id=game_id)
    store.create_character(migrated_character)

    legacy_profile = profile_store.get(CHRONICLE_GAME_ID, legacy_character.character_id)
    if legacy_profile is not None:
        profile_store.save(replace(legacy_profile, game_id=game_id))

    other_character_ids = {
        item.character_id
        for item in legacy_characters
        if item.character_id != legacy_character.character_id
    }
    _copy_history(repository, CHRONICLE_GAME_ID, game_id, legacy_character.character_id)
    _copy_world_events(
        repository,
        CHRONICLE_GAME_ID,
        game_id,
        excluded_actor_ids=other_character_ids,
    )

    legacy_simulation = simulation_store.get(CHRONICLE_GAME_ID)
    if legacy_simulation is not None:
        candidate = _personalize_legacy_simulation(
            legacy_simulation,
            game_id=game_id,
            excluded_character_ids=other_character_ids,
        )
        validate_political_state(
            candidate,
            [migrated_character],
            era_for_year(target_progress.year),
        )
        simulation_store.save(candidate)

    return PersonalChronicleContext(game_id=game_id, migrated_legacy=True)
