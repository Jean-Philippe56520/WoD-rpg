from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
from typing import Any, Iterable


MAX_MEMORY_EVENTS = 24
MAX_GRIEVANCES = 8


@dataclass(frozen=True)
class RelationshipMemoryEvent:
    id: str
    year: int
    chapter: int
    segment: int
    night: int
    category: str
    summary: str
    valence: int = 0


@dataclass(frozen=True)
class RelationshipMemoryState:
    npc_id: str
    character_id: str
    disposition: int = 0
    trust: int = 0
    respect: int = 0
    fear: int = 0
    known_facts: tuple[str, ...] = ()
    grievances: tuple[str, ...] = ()
    events: tuple[RelationshipMemoryEvent, ...] = ()
    last_interaction_year: int | None = None


def relationship_memory_key(npc_id: str, character_id: str) -> str:
    return f"{npc_id}::{character_id}"


def _bounded(value: int, low: int = -3, high: int = 3) -> int:
    return max(low, min(high, int(value)))


def _unique_limited(values: Iterable[str], *, limit: int) -> tuple[str, ...]:
    ordered: list[str] = []
    for raw in values:
        value = str(raw).strip()
        if value and value not in ordered:
            ordered.append(value)
    return tuple(ordered[-limit:])


def memory_for(state: Any, npc_id: str | None, character_id: str) -> RelationshipMemoryState | None:
    if not npc_id:
        return None
    return state.relationship_memories.get(relationship_memory_key(npc_id, character_id))


def ensure_character_memory(
    state: Any,
    character: Any,
    npc_id: str | None,
) -> Any:
    if not npc_id or npc_id not in state.npcs:
        return state
    key = relationship_memory_key(npc_id, character.character_id)
    if key in state.relationship_memories:
        return state

    known_facts = (
        f"name:{character.name}",
        f"clan:{character.clan_id}",
        f"sire:{character.sire_id}",
    )
    disposition = 0
    trust = 0
    respect = 0
    if npc_id == character.sire_id:
        # Legacy ``sire_relation`` stays authoritative for old saves while the
        # richer memory starts from an equivalent, non-extreme baseline.
        trust = _bounded(character.sire_relation - 1)
        disposition = _bounded(character.sire_relation - 2)
        known_facts += ("relationship:sire", "status:infant")

    memories = dict(state.relationship_memories)
    memories[key] = RelationshipMemoryState(
        npc_id=npc_id,
        character_id=character.character_id,
        disposition=disposition,
        trust=trust,
        respect=respect,
        known_facts=known_facts,
    )
    return replace(state, relationship_memories=memories)


def record_relationship_memory(
    state: Any,
    character: Any,
    npc_id: str | None,
    *,
    category: str,
    summary: str,
    year: int,
    chapter: int,
    segment: int,
    night: int,
    disposition_delta: int = 0,
    trust_delta: int = 0,
    respect_delta: int = 0,
    fear_delta: int = 0,
    known_facts: Iterable[str] = (),
    grievance: str | None = None,
    valence: int = 0,
) -> Any:
    if not npc_id or npc_id not in state.npcs:
        return state
    state = ensure_character_memory(state, character, npc_id)
    key = relationship_memory_key(npc_id, character.character_id)
    memory = state.relationship_memories[key]

    seed = (
        f"{state.game_id}:{npc_id}:{character.character_id}:{year}:{chapter}:"
        f"{segment}:{night}:{category}:{summary}"
    )
    event_id = "memory_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    events = list(memory.events)
    if not any(item.id == event_id for item in events):
        events.append(
            RelationshipMemoryEvent(
                id=event_id,
                year=int(year),
                chapter=int(chapter),
                segment=int(segment),
                night=int(night),
                category=str(category),
                summary=str(summary).strip(),
                valence=_bounded(valence),
            )
        )
    events = events[-MAX_MEMORY_EVENTS:]

    grievances = list(memory.grievances)
    if grievance:
        grievances.append(grievance)

    memories = dict(state.relationship_memories)
    memories[key] = replace(
        memory,
        disposition=_bounded(memory.disposition + disposition_delta),
        trust=_bounded(memory.trust + trust_delta),
        respect=_bounded(memory.respect + respect_delta),
        fear=_bounded(memory.fear + fear_delta, 0, 3),
        known_facts=_unique_limited((*memory.known_facts, *known_facts), limit=24),
        grievances=_unique_limited(grievances, limit=MAX_GRIEVANCES),
        events=tuple(events),
        last_interaction_year=int(year),
    )
    return replace(state, relationship_memories=memories)


def memories_for_character(state: Any, character_id: str) -> tuple[RelationshipMemoryState, ...]:
    memories = [
        memory
        for memory in state.relationship_memories.values()
        if memory.character_id == character_id
    ]
    memories.sort(
        key=lambda item: (
            -(abs(item.disposition) + abs(item.trust) + abs(item.respect) + item.fear),
            -(item.last_interaction_year or 0),
            item.npc_id,
        )
    )
    return tuple(memories)


def relationship_difficulty_adjustment(
    state: Any,
    npc_id: str | None,
    character_id: str,
) -> int:
    memory = memory_for(state, npc_id, character_id)
    if memory is None:
        return 0
    favorable = memory.disposition + memory.trust + memory.respect
    hostile = len(memory.grievances) + max(0, -memory.disposition) + max(0, -memory.trust)
    if favorable >= 5 and hostile == 0:
        return -1
    if hostile >= 4 or favorable <= -3:
        return 1
    return 0


def prestation_balance(state: Any, npc_id: str, character_id: str) -> int:
    """Return leverage from the NPC perspective without duplicating the boon ledger.

    Positive means the character owes the NPC; negative means the NPC owes the
    character. Major and life boons weigh more than minor boons.
    """

    weights = {"minor": 1, "major": 2, "life": 3}
    balance = 0
    for boon in state.boons.values():
        if boon.status != "due":
            continue
        weight = weights.get(boon.level, 1)
        if boon.creditor_id == npc_id and boon.debtor_id == character_id:
            balance += weight
        elif boon.creditor_id == character_id and boon.debtor_id == npc_id:
            balance -= weight
    return balance


def qualitative_relation(value: int) -> str:
    if value >= 3:
        return "très favorable"
    if value == 2:
        return "favorable"
    if value == 1:
        return "plutôt favorable"
    if value == 0:
        return "neutre"
    if value == -1:
        return "réservée"
    if value == -2:
        return "hostile"
    return "très hostile"


def qualitative_confidence(value: int) -> str:
    if value >= 2:
        return "forte"
    if value == 1:
        return "prudente"
    if value == 0:
        return "incertaine"
    if value == -1:
        return "faible"
    return "brisée"


def qualitative_respect(value: int) -> str:
    if value >= 2:
        return "marqué"
    if value == 1:
        return "réel"
    if value == 0:
        return "à gagner"
    if value == -1:
        return "faible"
    return "mépris"
