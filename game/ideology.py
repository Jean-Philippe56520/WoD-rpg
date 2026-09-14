from __future__ import annotations

from collections import defaultdict

from .config import DEFAULT_RULES, GameRules
from .models import Character, GameState, IdeologyQuadrant, PoliticalCurrent


CURRENT_NAMES = {
    IdeologyQuadrant.HUMANIST_TRADITIONAL: "Humanistes traditionnels",
    IdeologyQuadrant.HUMANIST_REFORMIST: "Reformateurs humanistes",
    IdeologyQuadrant.PREDATORY_TRADITIONAL: "Traditionalistes predateurs",
    IdeologyQuadrant.PREDATORY_RADICAL: "Radicaux predateurs",
}


def _clamp_axis(value: float) -> float:
    return max(-100.0, min(100.0, value))


def quadrant_for_values(humanism: float, tradition: float) -> IdeologyQuadrant:
    if humanism >= 0 and tradition >= 0:
        return IdeologyQuadrant.HUMANIST_TRADITIONAL
    if humanism >= 0 and tradition < 0:
        return IdeologyQuadrant.HUMANIST_REFORMIST
    if humanism < 0 and tradition >= 0:
        return IdeologyQuadrant.PREDATORY_TRADITIONAL
    return IdeologyQuadrant.PREDATORY_RADICAL


def current_id_for(clan_id: str, quadrant: IdeologyQuadrant) -> str:
    return f"{clan_id}__{quadrant.value}"


def character_current_id(character: Character) -> str | None:
    if not character.clan_id:
        return None
    return current_id_for(
        character.clan_id,
        quadrant_for_values(character.humanism, character.tradition),
    )


def ideological_affinity_values(
    humanism_a: float,
    tradition_a: float,
    humanism_b: float,
    tradition_b: float,
) -> float:
    """Return -100 (opposites) to +100 (identical) ideological affinity."""
    distance = abs(humanism_a - humanism_b) + abs(tradition_a - tradition_b)
    return max(-100.0, min(100.0, 100.0 - distance / 2.0))


def character_affinity(character_a: Character, character_b: Character) -> float:
    return ideological_affinity_values(
        character_a.humanism,
        character_a.tradition,
        character_b.humanism,
        character_b.tradition,
    )


def build_currents(state: GameState, clan_id: str) -> dict[str, PoliticalCurrent]:
    members = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
    ]
    grouped: dict[IdeologyQuadrant, list[Character]] = defaultdict(list)
    for member in members:
        grouped[quadrant_for_values(member.humanism, member.tradition)].append(member)

    currents: dict[str, PoliticalCurrent] = {}
    for quadrant, current_members in grouped.items():
        influence = sum(member.personal_influence for member in current_members)
        weights = [max(member.personal_influence, 1.0) for member in current_members]
        total_weight = sum(weights)
        centroid_humanism = sum(
            member.humanism * weight
            for member, weight in zip(current_members, weights)
        ) / total_weight
        centroid_tradition = sum(
            member.tradition * weight
            for member, weight in zip(current_members, weights)
        ) / total_weight
        leader_candidates = [member for member in current_members if member.id != state.prince_id]
        if not leader_candidates:
            leader_candidates = current_members
        leader = max(
            leader_candidates,
            key=lambda member: (member.personal_influence, member.ambition, member.id),
        )
        current_id = current_id_for(clan_id, quadrant)
        currents[current_id] = PoliticalCurrent(
            id=current_id,
            clan_id=clan_id,
            name=CURRENT_NAMES[quadrant],
            quadrant=quadrant,
            influence=influence,
            leader_id=leader.id,
            member_ids=tuple(member.id for member in current_members),
            centroid_humanism=centroid_humanism,
            centroid_tradition=centroid_tradition,
        )
    return currents


def current_affinity(current_a: PoliticalCurrent, current_b: PoliticalCurrent) -> float:
    return ideological_affinity_values(
        current_a.centroid_humanism,
        current_a.centroid_tradition,
        current_b.centroid_humanism,
        current_b.centroid_tradition,
    )


def primogen_current_id(state: GameState, clan_id: str) -> str:
    clan = state.clan_states[clan_id].clan
    primogen = state.characters[clan.primogen_id]
    current_id = character_current_id(primogen)
    if current_id is None:
        raise ValueError("Primogen must belong to a clan")
    return current_id


def clan_total_influence(state: GameState, clan_id: str) -> float:
    return sum(current.influence for current in build_currents(state, clan_id).values())


def _default_allied_primogen(state: GameState, clan_id: str, current: PoliticalCurrent) -> str:
    candidates = []
    for other_id, other_state in state.clan_states.items():
        if other_id == clan_id:
            continue
        primogen = state.characters[other_state.clan.primogen_id]
        affinity = ideological_affinity_values(
            current.centroid_humanism,
            current.centroid_tradition,
            primogen.humanism,
            primogen.tradition,
        )
        candidates.append((affinity, primogen.personal_influence, primogen.id))
    if not candidates:
        raise ValueError("No external Primogen available for current alliance")
    return max(candidates)[2]


def initialize_current_politics(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> None:
    """Ensure every active rival current has persistent loyalty and an ally."""
    for clan_id, clan_state in state.clan_states.items():
        currents = build_currents(state, clan_id)
        primary_id = primogen_current_id(state, clan_id)
        for current_id, current in currents.items():
            if current_id == primary_id:
                continue
            clan_state.current_loyalties.setdefault(
                current_id, rules.current_default_loyalty
            )
            clan_state.current_allies.setdefault(
                current_id,
                _default_allied_primogen(state, clan_id, current),
            )
        active_ids = set(currents)
        clan_state.current_loyalties = {
            key: value
            for key, value in clan_state.current_loyalties.items()
            if key in active_ids
        }
        clan_state.current_allies = {
            key: value
            for key, value in clan_state.current_allies.items()
            if key in active_ids
        }


def shift_ideology(
    state: GameState,
    character_id: str,
    humanism_delta: float = 0.0,
    tradition_delta: float = 0.0,
    rules: GameRules = DEFAULT_RULES,
) -> tuple[str | None, str | None]:
    if character_id not in state.characters:
        raise ValueError(f"Unknown character: {character_id}")
    character = state.characters[character_id]
    before = character_current_id(character)
    character.humanism = _clamp_axis(character.humanism + humanism_delta)
    character.tradition = _clamp_axis(character.tradition + tradition_delta)
    after = character_current_id(character)
    initialize_current_politics(state, rules)
    return before, after
