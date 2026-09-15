from __future__ import annotations

from .models import CoterieSide, CoterieStance, Character, GameState


def ideology_relation_modifier(character: Character, primogen: Character) -> int:
    matches = int(character.humanity_axis == primogen.humanity_axis)
    matches += int(character.tradition_axis == primogen.tradition_axis)
    return {0: -1, 1: 0, 2: 1}[matches]


def effective_relation_to_primogen(state: GameState, character_id: str) -> int:
    character = state.characters[character_id]
    if not character.clan_id or character.clan_id not in state.clan_states:
        raise ValueError("Character must belong to a playable clan")
    primogen_id = state.clan_states[character.clan_id].clan.primogen_id
    primogen = state.characters[primogen_id]
    return character.relation_to_primogen + ideology_relation_modifier(character, primogen)


def coterie_members(
    state: GameState,
    clan_id: str,
    side: CoterieSide,
) -> tuple[Character, ...]:
    clan_state = state.clan_states[clan_id]
    return tuple(
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
        and character.id != state.prince_id
        and clan_state.coterie_memberships.get(character.id) == side
    )


def coterie_influence(state: GameState, clan_id: str, side: CoterieSide) -> float:
    return sum(member.personal_influence for member in coterie_members(state, clan_id, side))


def clan_total_influence(state: GameState, clan_id: str) -> float:
    return coterie_influence(state, clan_id, CoterieSide.PRIMOGEN) + coterie_influence(
        state, clan_id, CoterieSide.OPPOSITION
    )


def _eligible_opposition_leaders(state: GameState, clan_id: str) -> list[Character]:
    clan_state = state.clan_states[clan_id]
    primogen = state.characters[clan_state.clan.primogen_id]
    return [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
        and character.id != primogen.id
        and character.id != state.prince_id
        and (
            character.humanity_axis != primogen.humanity_axis
            or character.tradition_axis != primogen.tradition_axis
        )
    ]


def choose_opposition_leader(state: GameState, clan_id: str) -> Character:
    clan_state = state.clan_states[clan_id]
    candidates = _eligible_opposition_leaders(state, clan_id)
    if not candidates:
        raise ValueError(f"No ideologically distinct opposition leader available for {clan_id}")
    return max(
        candidates,
        key=lambda character: (
            clan_state.coterie_memberships.get(character.id) == CoterieSide.OPPOSITION,
            character.personal_influence,
            character.ambition,
            -character.relation_to_primogen,
            character.id,
        ),
    )


def choose_allied_primogen(state: GameState, clan_id: str) -> str:
    clan_state = state.clan_states[clan_id]
    leader_id = clan_state.opposition_leader_id
    if not leader_id:
        raise ValueError("Opposition leader is required before choosing an ally")
    leader = state.characters[leader_id]
    candidates: list[tuple[int, int, float, str]] = []
    for other_clan_id, other_state in state.clan_states.items():
        if other_clan_id == clan_id:
            continue
        primogen = state.characters[other_state.clan.primogen_id]
        ideology = ideology_relation_modifier(leader, primogen)
        personal_relation = leader.relations.get(primogen.id, 0)
        candidates.append((ideology, personal_relation, primogen.personal_influence, primogen.id))
    if not candidates:
        raise ValueError("No external Primogen available for opposition alliance")
    return max(candidates)[3]


def initialize_coteries(state: GameState) -> None:
    for clan_id, clan_state in state.clan_states.items():
        primogen_id = clan_state.clan.primogen_id
        primogen = state.characters[primogen_id]
        active_members = {
            character.id
            for character in state.characters.values()
            if character.clan_id == clan_id and character.id != state.prince_id
        }
        active_members.add(primogen_id)

        memberships = {
            character_id: CoterieSide(side)
            for character_id, side in clan_state.coterie_memberships.items()
            if character_id in active_members
        }

        if not memberships:
            for character_id in active_members:
                if character_id == primogen_id:
                    memberships[character_id] = CoterieSide.PRIMOGEN
                    continue
                character = state.characters[character_id]
                effective = character.relation_to_primogen + ideology_relation_modifier(
                    character, primogen
                )
                memberships[character_id] = (
                    CoterieSide.OPPOSITION
                    if effective <= 0
                    else CoterieSide.PRIMOGEN
                )

        memberships[primogen_id] = CoterieSide.PRIMOGEN
        clan_state.coterie_memberships = memberships

        leader_id = clan_state.opposition_leader_id
        leader_valid = (
            leader_id in active_members
            and leader_id != primogen_id
            and leader_id is not None
            and (
                state.characters[leader_id].humanity_axis != primogen.humanity_axis
                or state.characters[leader_id].tradition_axis != primogen.tradition_axis
            )
        )
        if not leader_valid:
            leader_id = choose_opposition_leader(state, clan_id).id
            clan_state.opposition_leader_id = leader_id
        clan_state.coterie_memberships[leader_id] = CoterieSide.OPPOSITION

        if not any(
            side == CoterieSide.OPPOSITION
            for character_id, side in clan_state.coterie_memberships.items()
            if character_id != primogen_id
        ):
            clan_state.coterie_memberships[leader_id] = CoterieSide.OPPOSITION

        current_primogens = {
            other_state.clan.primogen_id for other_state in state.clan_states.values()
        }
        ally_id = clan_state.opposition_allied_primogen_id
        if (
            not ally_id
            or ally_id == primogen_id
            or ally_id not in current_primogens
        ):
            clan_state.opposition_allied_primogen_id = choose_allied_primogen(state, clan_id)


def set_coterie_side(
    state: GameState,
    character_id: str,
    side: CoterieSide,
) -> None:
    character = state.characters[character_id]
    if not character.clan_id:
        raise ValueError("Character must belong to a clan")
    clan_state = state.clan_states[character.clan_id]
    if character_id == clan_state.clan.primogen_id and side != CoterieSide.PRIMOGEN:
        raise ValueError("The Primogen cannot join the opposition")
    clan_state.coterie_memberships[character_id] = side
    if character_id == clan_state.opposition_leader_id and side != CoterieSide.OPPOSITION:
        clan_state.opposition_leader_id = None
    initialize_coteries(state)


def determine_coterie_stances(state: GameState) -> dict[str, CoterieStance]:
    initialize_coteries(state)
    stances: dict[str, CoterieStance] = {}
    for clan_id, clan_state in state.clan_states.items():
        leader_id = clan_state.opposition_leader_id
        if not leader_id:
            raise ValueError(f"Missing opposition leader for {clan_id}")
        effective = effective_relation_to_primogen(state, leader_id)
        support_score = {-1: 15.0, 0: 35.0, 1: 60.0, 2: 80.0, 3: 100.0}[effective]
        supports = effective >= 1
        stances[clan_id] = CoterieStance(
            clan_id=clan_id,
            supports_primogen=supports,
            support_score=support_score,
            allied_primogen_id=(
                None if supports else clan_state.opposition_allied_primogen_id
            ),
        )
    return stances
