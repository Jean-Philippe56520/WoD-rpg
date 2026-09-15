from __future__ import annotations

from .config import DEFAULT_RULES, GameRules
from .coteries import coterie_influence, initialize_coteries
from .models import (
    AxisPolarity,
    BloodRank,
    Candidate,
    Character,
    CoterieSide,
    GameEvent,
    GameState,
)


def succession_score(
    state: GameState,
    character: Character,
    rules: GameRules = DEFAULT_RULES,
) -> float:
    if character.clan_id is None:
        return float("-inf")
    clan_state = state.clan_states[character.clan_id]
    side = clan_state.coterie_memberships.get(character.id, CoterieSide.PRIMOGEN)
    return (
        character.personal_influence
        + coterie_influence(state, character.clan_id, side) * rules.succession_current_weight
        + character.ambition * rules.succession_ambition_weight
        + character.relation_to_primogen * 5.0
    )


def choose_successor(
    state: GameState,
    clan_id: str,
    outgoing_primogen_id: str,
    rules: GameRules = DEFAULT_RULES,
) -> Character:
    initialize_coteries(state)
    eligible = [
        character
        for character in state.characters.values()
        if character.clan_id == clan_id
        and character.id != outgoing_primogen_id
        and character.id != state.prince_id
    ]
    if not eligible:
        raise ValueError(f"No eligible successor for clan {clan_id}")
    return max(eligible, key=lambda character: (succession_score(state, character, rules), character.id))


def _reset_relations_to_new_primogen(
    state: GameState,
    clan_id: str,
    successor: Character,
) -> None:
    """Une relation au Primogène est attachée au titulaire, pas au siège abstrait."""
    for member in state.characters.values():
        if member.clan_id != clan_id or member.id == state.prince_id:
            continue
        if member.id == successor.id:
            member.relation_to_primogen = 2
            continue
        member.relation_to_primogen = member.relations.get(successor.id, 1)


def _apply_succession(state: GameState, outgoing: Character, rules: GameRules) -> Character:
    if not outgoing.clan_id:
        raise ValueError("A Primogen must belong to a clan")
    clan_state = state.clan_states[outgoing.clan_id]
    clan = clan_state.clan
    outgoing.is_primogen = False

    successor = choose_successor(state, outgoing.clan_id, outgoing.id, rules)
    successor.is_primogen = True
    clan.primogen_id = successor.id
    clan_state.coterie_memberships[successor.id] = CoterieSide.PRIMOGEN
    if clan_state.opposition_leader_id == successor.id:
        clan_state.opposition_leader_id = None

    _reset_relations_to_new_primogen(state, outgoing.clan_id, successor)

    for other_state in state.clan_states.values():
        if other_state.opposition_allied_primogen_id == outgoing.id:
            other_state.opposition_allied_primogen_id = successor.id

    state.events.append(
        GameEvent(
            night=state.night,
            category="succession",
            message=(
                f"{outgoing.name} quitte la Primogéniture {clan.name}. "
                f"{successor.name} devient le nouveau Primogène du clan."
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
            humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.PLUS,
            physical=1,
            social=2,
            mental=1,
            expertises=("Politique",),
            disciplines={},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Influence politique": 1},
            relation_to_primogen=1,
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
    initialize_coteries(state)
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
