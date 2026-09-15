from __future__ import annotations

from collections import defaultdict

from .config import DEFAULT_RULES, GameRules
from .models import AxisPolarity, Character, GameState, IdeologyQuadrant, PoliticalCurrent


CURRENT_NAMES = {
    IdeologyQuadrant.HUMANIST_TRADITIONAL: "Humanistes traditionalistes",
    IdeologyQuadrant.HUMANIST_REFORMIST: "Humanistes réformateurs",
    IdeologyQuadrant.PREDATORY_TRADITIONAL: "Prédateurs traditionalistes",
    IdeologyQuadrant.PREDATORY_RADICAL: "Prédateurs radicaux",
}


def quadrant_for_axes(
    humanity_axis: AxisPolarity | str,
    tradition_axis: AxisPolarity | str,
) -> IdeologyQuadrant:
    humanity_axis = AxisPolarity(humanity_axis)
    tradition_axis = AxisPolarity(tradition_axis)
    if humanity_axis == AxisPolarity.PLUS and tradition_axis == AxisPolarity.PLUS:
        return IdeologyQuadrant.HUMANIST_TRADITIONAL
    if humanity_axis == AxisPolarity.PLUS and tradition_axis == AxisPolarity.MINUS:
        return IdeologyQuadrant.HUMANIST_REFORMIST
    if humanity_axis == AxisPolarity.MINUS and tradition_axis == AxisPolarity.PLUS:
        return IdeologyQuadrant.PREDATORY_TRADITIONAL
    return IdeologyQuadrant.PREDATORY_RADICAL


def quadrant_for_values(humanism: float, tradition: float) -> IdeologyQuadrant:
    """Compatibilité V0.6 : convertit d'anciens axes numériques en polarités."""
    humanity_axis = AxisPolarity.PLUS if humanism >= 0 else AxisPolarity.MINUS
    tradition_axis = AxisPolarity.PLUS if tradition >= 0 else AxisPolarity.MINUS
    return quadrant_for_axes(humanity_axis, tradition_axis)


def current_id_for(clan_id: str, quadrant: IdeologyQuadrant) -> str:
    return f"{clan_id}__{quadrant.value}"


def character_current_id(character: Character) -> str | None:
    if not character.clan_id:
        return None
    return current_id_for(
        character.clan_id,
        quadrant_for_axes(character.humanity_axis, character.tradition_axis),
    )


def ideological_affinity_axes(
    humanity_a: AxisPolarity | str,
    tradition_a: AxisPolarity | str,
    humanity_b: AxisPolarity | str,
    tradition_b: AxisPolarity | str,
) -> float:
    """Affinité simple : +100 même courant, 0 un axe commun, -100 axes opposés."""
    matches = int(AxisPolarity(humanity_a) == AxisPolarity(humanity_b))
    matches += int(AxisPolarity(tradition_a) == AxisPolarity(tradition_b))
    return {-0: -100.0, 1: 0.0, 2: 100.0}[matches]


def ideological_affinity_values(
    humanism_a: float,
    tradition_a: float,
    humanism_b: float,
    tradition_b: float,
) -> float:
    """Compatibilité V0.6 pour les appels utilisant encore des valeurs numériques."""
    return ideological_affinity_axes(
        AxisPolarity.PLUS if humanism_a >= 0 else AxisPolarity.MINUS,
        AxisPolarity.PLUS if tradition_a >= 0 else AxisPolarity.MINUS,
        AxisPolarity.PLUS if humanism_b >= 0 else AxisPolarity.MINUS,
        AxisPolarity.PLUS if tradition_b >= 0 else AxisPolarity.MINUS,
    )


def character_affinity(character_a: Character, character_b: Character) -> float:
    return ideological_affinity_axes(
        character_a.humanity_axis,
        character_a.tradition_axis,
        character_b.humanity_axis,
        character_b.tradition_axis,
    )


def build_currents(state: GameState, clan_id: str) -> dict[str, PoliticalCurrent]:
    members = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
    ]
    grouped: dict[IdeologyQuadrant, list[Character]] = defaultdict(list)
    for member in members:
        grouped[quadrant_for_axes(member.humanity_axis, member.tradition_axis)].append(member)

    currents: dict[str, PoliticalCurrent] = {}
    for quadrant, current_members in grouped.items():
        influence = sum(member.personal_influence for member in current_members)
        leader_candidates = [member for member in current_members if member.id != state.prince_id]
        if not leader_candidates:
            leader_candidates = current_members
        leader = max(
            leader_candidates,
            key=lambda member: (member.personal_influence, member.ambition, member.id),
        )
        humanity_axis = (
            AxisPolarity.PLUS
            if quadrant in {
                IdeologyQuadrant.HUMANIST_TRADITIONAL,
                IdeologyQuadrant.HUMANIST_REFORMIST,
            }
            else AxisPolarity.MINUS
        )
        tradition_axis = (
            AxisPolarity.PLUS
            if quadrant in {
                IdeologyQuadrant.HUMANIST_TRADITIONAL,
                IdeologyQuadrant.PREDATORY_TRADITIONAL,
            }
            else AxisPolarity.MINUS
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
            humanity_axis=humanity_axis,
            tradition_axis=tradition_axis,
        )
    return currents


def current_affinity(current_a: PoliticalCurrent, current_b: PoliticalCurrent) -> float:
    return ideological_affinity_axes(
        current_a.humanity_axis,
        current_a.tradition_axis,
        current_b.humanity_axis,
        current_b.tradition_axis,
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
        affinity = ideological_affinity_axes(
            current.humanity_axis,
            current.tradition_axis,
            primogen.humanity_axis,
            primogen.tradition_axis,
        )
        candidates.append((affinity, primogen.personal_influence, primogen.id))
    if not candidates:
        raise ValueError("No external Primogen available for current alliance")
    return max(candidates)[2]


def initialize_current_politics(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> None:
    for clan_id, clan_state in state.clan_states.items():
        currents = build_currents(state, clan_id)
        primary_id = primogen_current_id(state, clan_id)
        for current_id, current in currents.items():
            if current_id == primary_id:
                continue
            clan_state.current_loyalties.setdefault(current_id, rules.current_default_loyalty)
            clan_state.current_allies.setdefault(
                current_id,
                _default_allied_primogen(state, clan_id, current),
            )
        active_ids = set(currents)
        clan_state.current_loyalties = {
            key: value for key, value in clan_state.current_loyalties.items() if key in active_ids
        }
        clan_state.current_allies = {
            key: value for key, value in clan_state.current_allies.items() if key in active_ids
        }


def shift_ideology(
    state: GameState,
    character_id: str,
    humanity_axis: AxisPolarity | str | None = None,
    tradition_axis: AxisPolarity | str | None = None,
    rules: GameRules = DEFAULT_RULES,
) -> tuple[str | None, str | None]:
    if character_id not in state.characters:
        raise ValueError(f"Unknown character: {character_id}")
    character = state.characters[character_id]
    before = character_current_id(character)
    if humanity_axis is not None:
        character.humanity_axis = AxisPolarity(humanity_axis)
    if tradition_axis is not None:
        character.tradition_axis = AxisPolarity(tradition_axis)
    after = character_current_id(character)
    initialize_current_politics(state, rules)
    return before, after
