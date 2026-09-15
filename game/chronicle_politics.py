from __future__ import annotations

"""Canonical political view for the character-centric Chronicle.

The production Chronicle persists political world state in ``SimulationState``.
The older ``models.GameState`` remains the source of truth only for the legacy
atelier.  This module is the boundary that prevents a second political state
from being introduced while legacy rules are progressively reconnected.

Player characters are not copied into ``SimulationState``: their canonical
identity stays in ``ChronicleStore``.  NPCs, Domains, hunting rights, boons and
political offices stay in ``SimulationState``.  ``PoliticalActor`` provides a
single read model over both sources without duplicating persistence.
"""

from dataclasses import dataclass, replace
from typing import Iterable, Mapping

from .chronicle import PlayerCharacter, PoliticalOffice
from .chronicle_simulation import SimulationState
from .era import EraRules


@dataclass(frozen=True)
class PoliticalActor:
    id: str
    name: str
    clan_id: str
    status: int
    influence: float
    source: str  # player | npc


_EXPLICIT_OFFICES = {
    PoliticalOffice.CLAN_ENVOY.value,
    PoliticalOffice.PRIMOGEN.value,
    PoliticalOffice.PRINCE.value,
}

_OFFICE_PRIORITY = (
    PoliticalOffice.PRINCE.value,
    PoliticalOffice.PRIMOGEN.value,
    PoliticalOffice.CLAN_ENVOY.value,
    PoliticalOffice.DOMAIN_HOLDER.value,
)


def _character_map(characters: Iterable[PlayerCharacter]) -> dict[str, PlayerCharacter]:
    result: dict[str, PlayerCharacter] = {}
    for character in characters:
        if character.character_id in result:
            raise ValueError(f"Duplicate player character id: {character.character_id}")
        result[character.character_id] = character
    return result


def known_actor_ids(state: SimulationState, characters: Iterable[PlayerCharacter]) -> set[str]:
    player_ids = set(_character_map(characters))
    npc_ids = set(state.npcs)
    overlap = player_ids & npc_ids
    if overlap:
        raise ValueError(f"Political actor id collision: {', '.join(sorted(overlap))}")
    return player_ids | npc_ids


def political_actor(
    state: SimulationState,
    characters: Iterable[PlayerCharacter],
    actor_id: str,
) -> PoliticalActor:
    players = _character_map(characters)
    if actor_id in players:
        character = players[actor_id]
        return PoliticalActor(
            id=character.character_id,
            name=character.name,
            clan_id=character.clan_id,
            status=character.status,
            influence=character.personal_influence,
            source="player",
        )
    npc = state.npcs.get(actor_id)
    if npc is None:
        raise ValueError(f"Unknown political actor: {actor_id}")
    return PoliticalActor(
        id=npc.id,
        name=npc.name,
        clan_id=npc.clan_id,
        status=npc.status,
        influence=npc.influence,
        source="npc",
    )


def _office_slot(office: str, actor: PoliticalActor) -> str:
    if office == PoliticalOffice.PRINCE.value:
        return PoliticalOffice.PRINCE.value
    if office in {PoliticalOffice.PRIMOGEN.value, PoliticalOffice.CLAN_ENVOY.value}:
        return f"{office}:{actor.clan_id}"
    raise ValueError(f"Office {office} is not stored as an explicit office")


def explicit_office_holders(state: SimulationState, office: str) -> tuple[str, ...]:
    office = PoliticalOffice(office).value
    if office == PoliticalOffice.PRINCE.value:
        holder = state.offices.get(PoliticalOffice.PRINCE.value)
        return (holder,) if holder else ()
    prefix = f"{office}:"
    holders = [
        holder_id
        for slot, holder_id in state.offices.items()
        if holder_id and (slot == office or slot.startswith(prefix))
    ]
    return tuple(dict.fromkeys(holders))


def actor_offices(state: SimulationState, actor_id: str) -> tuple[str, ...]:
    """Return offices derived only from canonical world state.

    ``PlayerCharacter.office`` is intentionally ignored.  It remains in the
    persisted character schema solely for backward compatibility.  Domain
    holder is derived from actual Domain ownership instead of a second flag.
    """

    held: set[str] = set()
    if any(domain.holder_id == actor_id for domain in state.domains.values()):
        held.add(PoliticalOffice.DOMAIN_HOLDER.value)

    for slot, holder_id in state.offices.items():
        if holder_id != actor_id:
            continue
        base = slot.split(":", 1)[0]
        if base in _EXPLICIT_OFFICES:
            held.add(base)
    return tuple(office for office in _OFFICE_PRIORITY if office in held)


def primary_office(state: SimulationState, actor_id: str) -> str:
    offices = actor_offices(state, actor_id)
    return offices[0] if offices else PoliticalOffice.NONE.value


def assign_office(
    state: SimulationState,
    characters: Iterable[PlayerCharacter],
    *,
    actor_id: str,
    office: str,
    era: EraRules,
) -> SimulationState:
    """Low-level canonical office assignment primitive.

    This does not grant political legitimacy by itself.  Praxis, elections or
    narrative procedures must call this only after their own rules succeed.
    """

    office = PoliticalOffice(office).value
    if office == PoliticalOffice.NONE.value:
        raise ValueError("Use clear_explicit_offices to remove an office")
    if office == PoliticalOffice.DOMAIN_HOLDER.value:
        raise ValueError("Domain-holder status comes from actual Domain ownership")
    if office not in _EXPLICIT_OFFICES:
        raise ValueError(f"Unsupported explicit office: {office}")
    if office not in era.available_offices:
        raise ValueError(f"Office {office} is not available in year {era.year}")
    if office == PoliticalOffice.PRIMOGEN.value and not era.primogen_council_standardized:
        raise ValueError("Primogen cannot be treated as a standardized office in this era")

    actor = political_actor(state, characters, actor_id)
    current = set(actor_offices(state, actor_id))
    if office == PoliticalOffice.PRINCE.value and PoliticalOffice.PRIMOGEN.value in current:
        raise ValueError("Prince and Primogen must be held by different vampires")
    if office == PoliticalOffice.PRIMOGEN.value and PoliticalOffice.PRINCE.value in current:
        raise ValueError("Prince and Primogen must be held by different vampires")

    offices = dict(state.offices)
    slot = _office_slot(office, actor)
    offices[slot] = actor_id
    updated = replace(state, offices=offices)
    validate_political_state(updated, characters, era)
    return updated


def clear_explicit_offices(state: SimulationState, *, actor_id: str) -> SimulationState:
    offices = {
        slot: holder_id
        for slot, holder_id in state.offices.items()
        if holder_id != actor_id
    }
    return replace(state, offices=offices)


def validate_political_state(
    state: SimulationState,
    characters: Iterable[PlayerCharacter],
    era: EraRules,
) -> None:
    """Validate cross-object political references and office invariants."""

    characters = tuple(characters)
    actors = known_actor_ids(state, characters)

    for key, domain in state.domains.items():
        if key != domain.id:
            raise ValueError(f"Domain key/id mismatch: {key} != {domain.id}")
        if domain.holder_id is not None and domain.holder_id not in actors:
            raise ValueError(f"Unknown Domain holder: {domain.holder_id}")

    for key, right in state.hunting_rights.items():
        if key != right.id:
            raise ValueError(f"Hunting-right key/id mismatch: {key} != {right.id}")
        if right.domain_id not in state.domains:
            raise ValueError(f"Unknown hunting-right Domain: {right.domain_id}")
        if right.beneficiary_id not in actors:
            raise ValueError(f"Unknown hunting-right beneficiary: {right.beneficiary_id}")
        if right.granted_by_id not in actors:
            raise ValueError(f"Unknown hunting-right grantor: {right.granted_by_id}")

    for key, boon in state.boons.items():
        if key != boon.id:
            raise ValueError(f"Boon key/id mismatch: {key} != {boon.id}")
        if boon.creditor_id not in actors or boon.debtor_id not in actors:
            raise ValueError(f"Unknown boon participant: {boon.id}")
        if boon.creditor_id == boon.debtor_id:
            raise ValueError("A vampire cannot owe a boon to themselves")
        if boon.level not in {"minor", "major", "life"}:
            raise ValueError(f"Unsupported boon level: {boon.level}")
        if boon.status not in {"due", "called", "fulfilled", "refused"}:
            raise ValueError(f"Unsupported boon status: {boon.status}")

    prince_ids: set[str] = set()
    primogen_ids: set[str] = set()
    for slot, holder_id in state.offices.items():
        if holder_id is None:
            continue
        if holder_id not in actors:
            raise ValueError(f"Unknown office holder: {holder_id}")
        base, _, clan_id = slot.partition(":")
        if base == PoliticalOffice.DOMAIN_HOLDER.value:
            raise ValueError("Domain-holder office must be derived from Domain ownership")
        if base not in _EXPLICIT_OFFICES:
            raise ValueError(f"Unknown political office slot: {slot}")
        if base == PoliticalOffice.PRINCE.value:
            if clan_id:
                raise ValueError("Prince is a city-wide office, not a clan slot")
            prince_ids.add(holder_id)
            continue
        if not clan_id:
            # Read compatibility for pre-V0.41 explicit slots; new writes are
            # always clan-scoped. A generic Primogen remains invalid pre-1493.
            if base == PoliticalOffice.PRIMOGEN.value and not era.primogen_council_standardized:
                raise ValueError("Primogen cannot be standardized in this era")
        else:
            actor = political_actor(state, characters, holder_id)
            if actor.clan_id != clan_id:
                raise ValueError(f"Office slot {slot} does not match holder clan {actor.clan_id}")
        if base == PoliticalOffice.PRIMOGEN.value:
            if not era.primogen_council_standardized:
                raise ValueError("Primogen cannot be standardized in this era")
            primogen_ids.add(holder_id)

    if prince_ids & primogen_ids:
        raise ValueError("Prince and Primogen must be held by different vampires")
