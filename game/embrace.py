from __future__ import annotations

from copy import deepcopy

from .config import DEFAULT_RULES, GameRules
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
    clan = state.clan_states[requester.clan_id].clan
    cost = rules.embrace_base_cost

    if prince.clan_id:
        if prince.clan_id == requester.clan_id:
            cost += rules.embrace_same_prince_clan_modifier
        else:
            cost += rules.embrace_other_clan_modifier

    if requester.current_id == clan.dominant_current.id:
        cost += rules.embrace_dominant_current_modifier
    elif requester.current_id == clan.opposition_current.id:
        cost += rules.embrace_opposition_current_modifier

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


def _relation_delta(
    approve: bool,
    position: PrimogenPosition,
    rules: GameRules,
) -> float:
    if approve:
        mapping = {
            PrimogenPosition.SUPPORT: rules.approve_relation_support,
            PrimogenPosition.NEUTRAL: rules.approve_relation_neutral,
            PrimogenPosition.OPPOSE: rules.approve_relation_oppose,
        }
    else:
        mapping = {
            PrimogenPosition.SUPPORT: rules.refuse_relation_support,
            PrimogenPosition.NEUTRAL: rules.refuse_relation_neutral,
            PrimogenPosition.OPPOSE: rules.refuse_relation_oppose,
        }
    return mapping[position]


def _opposition_loyalty_delta(
    approve: bool,
    position: PrimogenPosition,
    rules: GameRules,
) -> float:
    if approve:
        mapping = {
            PrimogenPosition.SUPPORT: rules.opposition_loyalty_approve_support,
            PrimogenPosition.NEUTRAL: rules.opposition_loyalty_approve_neutral,
            PrimogenPosition.OPPOSE: rules.opposition_loyalty_approve_oppose,
        }
    else:
        mapping = {
            PrimogenPosition.SUPPORT: rules.opposition_loyalty_refuse_support,
            PrimogenPosition.NEUTRAL: rules.opposition_loyalty_refuse_neutral,
            PrimogenPosition.OPPOSE: rules.opposition_loyalty_refuse_oppose,
        }
    return mapping[position]


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
    clan = clan_state.clan

    if approve:
        if next_state.prince_political_capital < request.political_cost:
            raise ValueError("Insufficient Prince political capital")
        next_state.prince_political_capital -= request.political_cost
        request.status = EmbraceStatus.APPROVED
        if requester.current_id == clan.dominant_current.id:
            clan.dominant_current.influence += rules.embrace_current_influence_gain
        elif requester.current_id == clan.opposition_current.id:
            clan.opposition_current.influence += rules.embrace_current_influence_gain
        decision_word = "autorise"
    else:
        request.status = EmbraceStatus.REFUSED
        decision_word = "refuse"

    request.decision_night = next_state.night
    next_state.prince_relations[requester.clan_id] = (
        next_state.prince_relations.get(requester.clan_id, 0.0)
        + _relation_delta(approve, request.primogen_position, rules)
    )

    if requester.current_id == clan.opposition_current.id:
        clan_state.opposition_loyalty = _clamp(
            clan_state.opposition_loyalty
            + _opposition_loyalty_delta(approve, request.primogen_position, rules)
        )

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
