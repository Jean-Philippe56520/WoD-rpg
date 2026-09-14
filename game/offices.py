from __future__ import annotations

from .config import DEFAULT_RULES, GameRules
from .ideology import (
    build_currents,
    character_current_id,
    initialize_current_politics,
)
from .models import Candidate, Character, GameEvent, GameState


def _current_influence(state: GameState, character: Character) -> float:
    if not character.clan_id:
        return 0.0
    current_id = character_current_id(character)
    if current_id is None:
        return 0.0
    current = build_currents(state, character.clan_id).get(current_id)
    return current.influence if current else 0.0


def succession_score(
    state: GameState,
    character: Character,
    rules: GameRules = DEFAULT_RULES,
) -> float:
    if character.clan_id is None:
        return float("-inf")
    return (
        character.personal_influence
        + _current_influence(state, character) * rules.succession_current_weight
        + character.ambition * rules.succession_ambition_weight
        + character.loyalty * rules.succession_loyalty_weight
    )


def choose_successor(
    state: GameState,
    clan_id: str,
    outgoing_primogen_id: str,
    rules: GameRules = DEFAULT_RULES,
) -> Character:
    eligible = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
        and character.id != outgoing_primogen_id
        and character.id != state.prince_id
    ]
    if not eligible:
        raise ValueError(f"No eligible successor for clan {clan_id}")
    return max(
        eligible,
        key=lambda character: (succession_score(state, character, rules), character.id),
    )


def _apply_succession(
    state: GameState,
    outgoing: Character,
    rules: GameRules,
) -> Character:
    if not outgoing.clan_id:
        raise ValueError("A Primogen must belong to a clan")
    clan_state = state.clan_states[outgoing.clan_id]
    clan = clan_state.clan
    outgoing_current_id = character_current_id(outgoing)
    outgoing.is_primogen = False

    successor = choose_successor(state, outgoing.clan_id, outgoing.id, rules)
    successor.is_primogen = True
    clan.primogen_id = successor.id
    successor_current_id = character_current_id(successor)

    if outgoing_current_id and successor_current_id != outgoing_current_id:
        clan_state.current_loyalties.setdefault(
            outgoing_current_id, rules.succession_loyalty_reset
        )

    for other_state in state.clan_states.values():
        for current_id, ally_id in list(other_state.current_allies.items()):
            if ally_id == outgoing.id:
                other_state.current_allies[current_id] = successor.id

    initialize_current_politics(state, rules)
    state.events.append(
        GameEvent(
            night=state.night,
            category="succession",
            message=(
                f"{outgoing.name} quitte la Primogeniture {clan.name}. "
                f"{successor.name} devient le nouveau Primogene du clan."
            ),
        )
    )
    return successor


def install_prince(
    state: GameState,
    winner: Candidate,
    rules: GameRules = DEFAULT_RULES,
) -> None:
    if state.prince_id is not None:
        raise ValueError("A Prince is already installed")

    character = state.characters.get(winner.id)
    if character is None:
        character = Character(
            id=winner.id,
            name=winner.name,
            clan_id=winner.clan_id,
            personal_influence=18,
            humanity=7,
            humanism=0,
            tradition=0,
            loyalty=50,
            ambition=75,
            is_primogen=False,
        )
        state.characters[character.id] = character

    if character.is_primogen:
        _apply_succession(state, character, rules)

    character.is_primogen = False
    state.prince_id = character.id
    state.prince_political_capital = rules.prince_initial_capital
    state.prince_relations = {clan_id: 0.0 for clan_id in state.clan_states}
    state.praxis_status = "recognized"
    initialize_current_politics(state, rules)
    state.events.append(
        GameEvent(
            night=state.night,
            category="praxis",
            message=(
                f"{character.name} est reconnu comme Prince. "
                f"Capital politique initial : {rules.prince_initial_capital:.0f}."
            ),
        )
    )
