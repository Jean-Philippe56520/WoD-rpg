from __future__ import annotations

from copy import deepcopy

from .config import DEFAULT_RULES, GameRules
from .coteries import initialize_coteries
from .models import (
    CoterieSide,
    EmbracePetitionOrder,
    EmbraceRequest,
    EmbraceStatus,
    GameEvent,
    GameState,
    PrimogenPosition,
)


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

    initialize_coteries(state)
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

    requester_side = state.clan_states[requester.clan_id].coterie_memberships.get(
        requester.id, CoterieSide.PRIMOGEN
    )
    if requester_side == CoterieSide.PRIMOGEN:
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
    submitted_by_primogen_id: str | None = None,
    rules: GameRules = DEFAULT_RULES,
) -> GameState:
    if not proposed_childe_name.strip():
        raise ValueError("A proposed childe name is required")

    next_state = deepcopy(state)
    initialize_coteries(next_state)
    requester = next_state.characters.get(requester_id)
    if requester is None or not requester.clan_id:
        raise ValueError("Requester must be a known clan member")
    current_primogen_id = next_state.clan_states[requester.clan_id].clan.primogen_id
    submitted_by_primogen_id = submitted_by_primogen_id or current_primogen_id
    if submitted_by_primogen_id != current_primogen_id:
        raise ValueError("Only the current Primogen may submit a clan request to the Prince")
    if requester_id == current_primogen_id:
        raise ValueError("The Primogen must submit the request on behalf of another clan member")

    cost = calculate_embrace_cost(next_state, requester_id, primogen_position, rules)
    request_id = f"embrace_{len(next_state.embrace_requests) + 1}"
    request = EmbraceRequest(
        id=request_id,
        requester_id=requester_id,
        proposed_childe_name=proposed_childe_name.strip(),
        primogen_position=primogen_position,
        political_cost=cost,
        created_night=next_state.night,
        submitted_by_primogen_id=submitted_by_primogen_id,
    )
    next_state.embrace_requests[request.id] = request
    primogen = next_state.characters[submitted_by_primogen_id]
    next_state.events.append(
        GameEvent(
            night=next_state.night,
            category="embrace",
            message=(
                f"{primogen.name}, au nom de {requester.name}, demande au Prince l'autorisation "
                f"d'Étreindre {request.proposed_childe_name}. Coût politique estimé : {cost:.0f}."
            ),
            audience_clan_ids=(requester.clan_id,),
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

    initialize_coteries(next_state)
    prince = next_state.characters[next_state.prince_id]
    next_state.events.append(
        GameEvent(
            night=next_state.night,
            category="embrace",
            message=(
                f"{prince.name} {decision_word} la demande portée par le Primogène de "
                f"{requester.name} concernant {request.proposed_childe_name}."
            ),
            audience_clan_ids=(requester.clan_id,),
        )
    )
    return next_state


def process_primogen_petition(
    state: GameState,
    clan_id: str,
    petition: EmbracePetitionOrder,
    rules: GameRules = DEFAULT_RULES,
) -> GameState:
    if state.prince_id is None:
        raise ValueError("No Prince is installed")
    if clan_id not in state.clan_states:
        raise ValueError(f"Unknown clan: {clan_id}")
    member = state.characters.get(petition.member_id)
    if member is None or member.clan_id != clan_id:
        raise ValueError("The Primogen may only petition for a member of their own clan")
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    if member.id == primogen_id:
        raise ValueError("The petition must be on behalf of another clan member")

    next_state = create_embrace_request(
        state,
        requester_id=member.id,
        proposed_childe_name=petition.proposed_childe_name,
        primogen_position=PrimogenPosition.SUPPORT,
        submitted_by_primogen_id=primogen_id,
        rules=rules,
    )
    request = list(next_state.embrace_requests.values())[-1]
    relation = next_state.prince_relations.get(clan_id, 0.0)
    approve = (
        next_state.prince_political_capital >= request.political_cost
        and relation >= rules.prince_auto_refusal_relation_floor
    )
    return decide_embrace_request(next_state, request.id, approve, rules)
