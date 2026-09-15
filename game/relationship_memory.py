from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Iterable


_MEMORY_PREFIX = "@memory"


@dataclass(frozen=True)
class RelationshipMemoryEvent:
    chapter: int
    segment: int
    night: int
    category: str
    summary: str
    detail: str
    valence: int = 0


@dataclass(frozen=True)
class RelationshipMemoryState:
    npc_id: str
    character_id: str
    disposition: int = 0
    trust: int = 0
    respect: int = 0
    fear: int = 0
    awareness: int = 0
    grievance_count: int = 0
    last_interaction_year: int | None = None
    known_facts: tuple[str, ...] = ()


def _metric_key(metric: str, character_id: str) -> str:
    return f"{_MEMORY_PREFIX}:{metric}:{character_id}"


def _bounded(value: int, low: int = -3, high: int = 3) -> int:
    return max(low, min(high, int(value)))


def _metric(relations: dict[str, int], metric: str, character_id: str, default: int = 0) -> int:
    return int(relations.get(_metric_key(metric, character_id), default))


def _has_memory(relations: dict[str, int], character_id: str) -> bool:
    return _metric_key("awareness", character_id) in relations or character_id in relations


def memory_for(state: Any, npc_id: str | None, character: Any) -> RelationshipMemoryState | None:
    if not npc_id or npc_id not in state.npcs:
        return None
    npc = state.npcs[npc_id]
    relations = npc.relations
    if not _has_memory(relations, character.character_id) and npc_id != character.sire_id:
        return None

    if character.character_id in relations:
        disposition = int(relations[character.character_id])
    elif npc_id == character.sire_id:
        disposition = _bounded(character.sire_relation - 2)
    else:
        disposition = 0

    trust_default = _bounded(character.sire_relation - 1) if npc_id == character.sire_id else 0
    awareness = max(0, min(5, _metric(relations, "awareness", character.character_id, 1)))
    known_facts = [f"Nom : {character.name}", f"Clan : {character.clan_id.title()}"]
    if npc_id == character.sire_id:
        known_facts.extend(("Lien : sire", "Position initiale : infant sous responsabilité"))
    if awareness >= 2:
        known_facts.append(f"Sire connu : {character.sire_name}")
    if awareness >= 3:
        known_facts.append("Votre réputation générale lui est connue")

    last_year = _metric(relations, "lastyear", character.character_id, 0)
    return RelationshipMemoryState(
        npc_id=npc_id,
        character_id=character.character_id,
        disposition=_bounded(disposition),
        trust=_bounded(_metric(relations, "trust", character.character_id, trust_default)),
        respect=_bounded(_metric(relations, "respect", character.character_id, 0)),
        fear=_bounded(_metric(relations, "fear", character.character_id, 0), 0, 3),
        awareness=awareness,
        grievance_count=max(0, _metric(relations, "grievances", character.character_id, 0)),
        last_interaction_year=last_year or None,
        known_facts=tuple(known_facts),
    )


def ensure_character_memory(state: Any, character: Any, npc_id: str | None) -> Any:
    if not npc_id or npc_id not in state.npcs:
        return state
    npc = state.npcs[npc_id]
    if _has_memory(npc.relations, character.character_id):
        return state

    relations = dict(npc.relations)
    relations[character.character_id] = _bounded(character.sire_relation - 2) if npc_id == character.sire_id else 0
    relations[_metric_key("trust", character.character_id)] = (
        _bounded(character.sire_relation - 1) if npc_id == character.sire_id else 0
    )
    relations[_metric_key("respect", character.character_id)] = 0
    relations[_metric_key("fear", character.character_id)] = 0
    relations[_metric_key("awareness", character.character_id)] = 2 if npc_id == character.sire_id else 1
    relations[_metric_key("grievances", character.character_id)] = 0
    relations[_metric_key("lastyear", character.character_id)] = 0
    npcs = dict(state.npcs)
    npcs[npc_id] = replace(npc, relations=relations)
    return replace(state, npcs=npcs)


def record_relationship_memory(
    state: Any,
    character: Any,
    npc_id: str | None,
    *,
    year: int,
    disposition_delta: int = 0,
    trust_delta: int = 0,
    respect_delta: int = 0,
    fear_delta: int = 0,
    awareness_delta: int = 1,
    grievance: bool = False,
) -> Any:
    if not npc_id or npc_id not in state.npcs:
        return state
    state = ensure_character_memory(state, character, npc_id)
    npc = state.npcs[npc_id]
    relations = dict(npc.relations)
    character_id = character.character_id

    relations[character_id] = _bounded(relations.get(character_id, 0) + disposition_delta)
    relations[_metric_key("trust", character_id)] = _bounded(
        _metric(relations, "trust", character_id) + trust_delta
    )
    relations[_metric_key("respect", character_id)] = _bounded(
        _metric(relations, "respect", character_id) + respect_delta
    )
    relations[_metric_key("fear", character_id)] = _bounded(
        _metric(relations, "fear", character_id) + fear_delta, 0, 3
    )
    relations[_metric_key("awareness", character_id)] = max(
        0, min(5, _metric(relations, "awareness", character_id) + awareness_delta)
    )
    if grievance:
        relations[_metric_key("grievances", character_id)] = min(
            9, _metric(relations, "grievances", character_id) + 1
        )
    relations[_metric_key("lastyear", character_id)] = int(year)

    npcs = dict(state.npcs)
    npcs[npc_id] = replace(npc, relations=relations)
    return replace(state, npcs=npcs)


def memories_for_character(state: Any, character: Any) -> tuple[RelationshipMemoryState, ...]:
    result: list[RelationshipMemoryState] = []
    for npc_id in state.npcs:
        memory = memory_for(state, npc_id, character)
        if memory is not None:
            result.append(memory)
    result.sort(
        key=lambda item: (
            item.npc_id != character.sire_id,
            -(abs(item.disposition) + abs(item.trust) + abs(item.respect) + item.fear),
            -(item.last_interaction_year or 0),
            item.npc_id,
        )
    )
    return tuple(result)


def relationship_difficulty_adjustment(state: Any, npc_id: str | None, character: Any) -> int:
    memory = memory_for(state, npc_id, character)
    if memory is None:
        return 0
    favorable = memory.disposition + memory.trust + memory.respect
    hostile = memory.grievance_count + max(0, -memory.disposition) + max(0, -memory.trust)
    if favorable >= 5 and hostile == 0:
        return -1
    if hostile >= 4 or favorable <= -3:
        return 1
    return 0


def relationship_tags(npc_id: str | None, category: str, valence: int) -> tuple[str, ...]:
    if not npc_id:
        return ()
    bounded = _bounded(valence)
    return (f"actor:{npc_id}", f"relation:{category}", f"valence:{bounded:+d}")


def events_from_history(history: Iterable[dict[str, Any]], npc_id: str) -> tuple[RelationshipMemoryEvent, ...]:
    events: list[RelationshipMemoryEvent] = []
    actor_tag = f"actor:{npc_id}"
    for item in history:
        outcome = item.get("outcome_json") or {}
        tags = tuple(str(tag) for tag in outcome.get("tags", ()))
        if actor_tag not in tags:
            continue
        category = next((tag.removeprefix("relation:") for tag in tags if tag.startswith("relation:")), "interaction")
        raw_valence = next((tag.removeprefix("valence:") for tag in tags if tag.startswith("valence:")), "0")
        try:
            valence = _bounded(int(raw_valence))
        except ValueError:
            valence = 0
        events.append(
            RelationshipMemoryEvent(
                chapter=int(item["chapter"]),
                segment=int(item["segment"]),
                night=int(item["night_number"]),
                category=category,
                summary=str(outcome.get("summary", item.get("action", "Interaction"))),
                detail=str(outcome.get("detail", "")),
                valence=valence,
            )
        )
    return tuple(events)


def prestation_balance(state: Any, npc_id: str, character_id: str) -> int:
    """Leverage from the NPC perspective, derived from the canonical boon ledger."""
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
    return {
        -3: "très hostile",
        -2: "hostile",
        -1: "réservée",
        0: "neutre",
        1: "plutôt favorable",
        2: "favorable",
        3: "très favorable",
    }[_bounded(value)]


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
