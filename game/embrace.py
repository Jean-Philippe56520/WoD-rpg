from __future__ import annotations

from copy import deepcopy

from .config import DEFAULT_RULES, GameRules
from .ideology import (
    character_current_id,
    initialize_current_politics,
    primogen_current_id,
)
from .models import (
    EmbraceRequest,
    EmbraceStatus,
    GameEvent,
    GameState,
    PrimogenPosition,
)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def _position_modifier(position: PrimogenPosition, rules: GameRules) -> float:
    if position == PrimogenPosition.SUPPORT:
        return rules.embrace_primogen_support_modifier
    if position == PrimogenPosition.NEUTRAL:
        return rules.embrace_primogen_neutral_modifier
    return rules.embrace_primogen_oppose_modifier


def calculate_embrace_cost(
    state: GameState,
    requester_id: str,
    primogen_position: PrimogenPosition,
    rules: GameRules = DEFAULT_RULES,
) -> float:
    if state.prince_id is None:
        raise ValueError("No Prince is installed")
    if requester_id not in state.characters:
        raise ValueError(f"Unknown requester: {requester_id}")

    requester = state.characters[requester_id]
    if not requester.clan_id or requester.clan_id not in state.clan_states:
        raise ValueError("Requester must belong to a playable clan")
    if requester.id == state.prince_id:
        raise ValueError("The Prince cannot request their own authorisation")

    prince = state.characters[state.prince_id]
    cost = rules.embrace_base_cost

    if prince.clan_id:
        if prince.clan_id == requester.clan_id:
            cost += rules.embrace_same_prince_clan_modifier
        else:
            cost += rules.embrace_other_clan_modifier

    requester_current = character_current_id(requester)
    primary_current = primogen_current_id(state, requester.clan_id)
    if requester_current == primary_current:
        cost += rules.embrace_primogen_current_modifier
    else:
        cost += rules.embrace_rival_current_modifier

    cost += _position_modifier(primogen_position, rules)
    return max(rules.embrace_minimum_cost, cost)


def create_embrace_request(
    state: GameState,
    requester_id: str,
    proposed_childe_name: str,
    primogen_position: PrimogenPosition,
    rules: GameRules = DEFAULT_RULES,
) -> GameState:
    if not proposed_childe_name.strip():
        raise ValueError("A proposed childe name is required")

    next_state = deepcopy(state)
    cost = calculate_embrace_cost(next_state, requester_id, primogen_position, rules)
    request_id = f"embrace_{len(next_state.embrace_requests) + 1}"
    request = EmbraceRequest(
        id=request_id,
        requester_id=requester_id,
        proposed_childe_name=proposed_childe_name.strip(),
        primogen_position=primogen_position,
        political_cost=cost,
        created_night=next_state.night,
    )
    next_state.embrace_requests[request.id] = request
    requester = next_state.characters[requester_id]
    next_state.events.append(
        GameEvent(
            night=next_state.night,
            category="embrace",
            message=(
                f"{requester.name} demande au Prince l'autorisation d'Etreindre "
                f"{request.proposed_childe_name}. Cout politique estime : {cost:.0f}."
            ),
        )
    )
    return next_state


def _relation_delta(approve: bool, position: PrimogenPosition, rules: GameRules) -> float:
    mapping = {
        True: {
            PrimogenPosition.SUPPORT: rules.approve_relation_support,
            PrimogenPosition.NEUTRAL: rules.approve_relation_neutral,
            PrimogenPosition.OPPOSE: rules.approve_relation_oppose,
        },
        False: {
            PrimogenPosition.SUPPORT: rules.refuse_relation_support,
            PrimogenPosition.NEUTRAL: rules.refuse_relation_neutral,
            PrimogenPosition.OPPOSE: rules.refuse_relation_oppose,
        },
    }
    return mapping[approve][position]


def _rival_loyalty_delta(approve: bool, position: PrimogenPosition, rules: GameRules) -> float:
    mapping = {
        True: {
            PrimogenPosition.SUPPORT: rules.rival_loyalty_approve_support,
            PrimogenPosition.NEUTRAL: rules.rival_loyalty_approve_neutral,
            PrimogenPosition.OPPOSE: rules.rival_loyalty_approve_oppose,
        },
        False: {
            PrimogenPosition.SUPPORT: rules.rival_loyalty_refuse_support,
            PrimogenPosition.NEUTRAL: rules.rival_loyalty_refuse_neutral,
            PrimogenPosition.OPPOSE: rules.rival_loyalty_refuse_oppose,
        },
    }
    return mapping[approve][position]


def decide_embrace_request(
    state: GameState,
    request_id: str,
    approve: bool,
    rules: GameRules = DEFAULT_RULES,
) -> GameState:
    next_state = deepcopy(state)
    if next_state.prince_id is None:
        raise ValueError("No Prince is installed")
    if request_id not in next_state.embrace_requests:
        raise ValueError(f"Unknown embrace request: {request_id}")

    request = next_state.embrace_requests[request_id]
    if request.status != EmbraceStatus.PENDING:
        raise ValueError("This embrace request has already been decided")

    requester = next_state.characters[request.requester_id]
    clan_state = next_state.clan_states[requester.clan_id]
    requester_current = character_current_id(requester)
    primary_current = primogen_current_id(next_state, requester.clan_id)

    if approve:
        if next_state.prince_political_capital < request.political_cost:
            raise ValueError("Insufficient Prince political capital")
        next_state.prince_political_capital -= request.political_cost
        request.status = EmbraceStatus.APPROVED
        requester.personal_influence += rules.embrace_requester_influence_gain
        decision_word = "autorise"
    else:
        request.status = EmbraceStatus.REFUSED
        decision_word = "refuse"

    request.decision_night = next_state.night
    next_state.prince_relations[requester.clan_id] = (
        next_state.prince_relations.get(requester.clan_id, 0.0)
        + _relation_delta(approve, request.primogen_position, rules)
    )

    if requester_current and requester_current != primary_current:
        before = clan_state.current_loyalties.get(
            requester_current, rules.current_default_loyalty
        )
        clan_state.current_loyalties[requester_current] = _clamp(
            before + _rival_loyalty_delta(approve, request.primogen_position, rules)
        )

    initialize_current_politics(next_state, rules)
    prince = next_state.characters[next_state.prince_id]
    next_state.events.append(
        GameEvent(
            night=next_state.night,
            category="embrace",
            message=(
                f"{prince.name} {decision_word} la demande d'Etreinte de {requester.name} "
                f"concernant {request.proposed_childe_name}."
            ),
        )
    )
    return next_state
