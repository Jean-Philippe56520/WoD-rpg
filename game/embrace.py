from __future__ import annotations

from copy import deepcopy

from .config import DEFAULT_RULES, GameRules
from .court import embrace_approval_score, prince_should_approve_embrace
from .factions import effective_relation_to_primogen, initialize_factions
from .models import (
    BloodRank,
    Character,
    ClanFactionSide,
    CLAN_DISCIPLINES,
    EmbracePetitionOrder,
    EmbraceRequest,
    EmbraceStatus,
    GameEvent,
    GameState,
    PoliticalAmbition,
    PrimogenPosition,
)
from .social_politics import active_grievance_score, add_grievance


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

    initialize_factions(state)
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

    requester_side = state.clan_states[requester.clan_id].faction_memberships.get(
        requester.id, ClanFactionSide.PRIMOGEN
    )
    if requester_side == ClanFactionSide.PRIMOGEN:
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
    initialize_factions(next_state)
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


def childe_character_id(request_id: str) -> str:
    return f"childe_{request_id}"


def embrace_was_enacted(state: GameState, request_id: str) -> bool:
    return childe_character_id(request_id) in state.characters


def _create_childe(
    state: GameState,
    request: EmbraceRequest,
    *,
    clandestine: bool,
    rules: GameRules,
) -> Character:
    requester = state.characters[request.requester_id]
    if not requester.clan_id:
        raise ValueError("The sire must belong to a playable clan")
    clan_state = state.clan_states[requester.clan_id]
    childe_id = childe_character_id(request.id)
    existing = state.characters.get(childe_id)
    if existing is not None:
        return existing

    side = clan_state.faction_memberships.get(requester.id, ClanFactionSide.PRIMOGEN)
    disciplines = CLAN_DISCIPLINES.get(requester.clan_id, ())
    starter_disciplines = {disciplines[0]: 1} if disciplines else {}
    relation_to_primogen = 0 if side == ClanFactionSide.OPPOSITION else 1
    childe = Character(
        id=childe_id,
        name=request.proposed_childe_name,
        clan_id=requester.clan_id,
        personal_influence=rules.embrace_childe_initial_influence,
        mortal_stance=requester.mortal_stance,
        order_stance=requester.order_stance,
        humanity=max(4, min(8, requester.humanity)),
        hunger=rules.embrace_childe_initial_hunger,
        status=0,
        reputation=0,
        political_ambition=PoliticalAmbition.INCREASE_INFLUENCE,
        physical=1,
        social=1,
        mental=1,
        expertises=(),
        disciplines=starter_disciplines,
        blood_rank=BloodRank.NEWBORN,
        backgrounds={},
        relation_to_primogen=relation_to_primogen,
        relations={requester.id: 2},
        loyalty=55.0 if not clandestine else 45.0,
        ambition=35.0,
        is_primogen=False,
    )
    state.characters[childe.id] = childe
    requester.relations[childe.id] = 2
    clan_state.faction_memberships[childe.id] = side
    initialize_factions(state)
    return childe


def enact_embrace(
    state: GameState,
    request_id: str,
    *,
    clandestine: bool = False,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent | None:
    """Rend l'Étreinte réelle en ajoutant l'infant au monde persistant.

    Les anciennes sauvegardes dont une demande était déjà approuvée sont donc
    migrables sans changement de schéma : l'identifiant de l'infant est dérivé de
    celui de la demande et la présence du personnage rend l'opération idempotente.
    """

    request = state.embrace_requests.get(request_id)
    if request is None:
        raise ValueError(f"Unknown embrace request: {request_id}")
    if embrace_was_enacted(state, request_id):
        return None
    expected_status = EmbraceStatus.REFUSED if clandestine else EmbraceStatus.APPROVED
    if request.status != expected_status:
        raise ValueError("The embrace request is not in a compatible state")

    requester = state.characters[request.requester_id]
    childe = _create_childe(state, request, clandestine=clandestine, rules=rules)
    clan_id = requester.clan_id
    assert clan_id is not None

    if not clandestine:
        return GameEvent(
            night=state.night,
            category=f"embrace_enacted|{request.id}|authorized",
            message=(
                f"Avec l'autorisation du Prince, {requester.name} Étreint {childe.name}. "
                f"Le nouveau-né rejoint officiellement le clan {state.clan_states[clan_id].clan.name}."
            ),
            audience_clan_ids=(clan_id,),
        )

    requester.reputation = max(
        -3, requester.reputation - rules.clandestine_embrace_reputation_loss
    )
    requester.relation_to_primogen = max(0, requester.relation_to_primogen - 1)
    state.camarilla_stability = max(
        0.0, state.camarilla_stability - rules.clandestine_embrace_stability_loss
    )
    state.masquerade_integrity = max(
        0.0, state.masquerade_integrity - rules.clandestine_embrace_masquerade_loss
    )
    state.prince_relations[clan_id] = (
        state.prince_relations.get(clan_id, 0.0)
        - rules.clandestine_embrace_prince_relation_loss
    )

    if state.prince_id is not None:
        add_grievance(
            state,
            owner_id=state.prince_id,
            target_id=requester.id,
            reason=f"Étreinte clandestine de {childe.name} malgré un refus princier",
            severity=2,
        )
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    if primogen_id != requester.id:
        add_grievance(
            state,
            owner_id=primogen_id,
            target_id=requester.id,
            reason=f"Désobéissance après le refus princier concernant {childe.name}",
            severity=1,
        )

    return GameEvent(
        night=state.night,
        category=f"embrace_enacted|{request.id}|clandestine",
        message=(
            f"L'Étreinte clandestine de {childe.name} par {requester.name} est découverte. "
            "Le Prince y voit une violation directe de son autorité : réputation, stabilité et "
            "Mascarade sont affectées."
        ),
    )


def should_attempt_clandestine_embrace(
    state: GameState,
    request_id: str,
    rules: GameRules = DEFAULT_RULES,
) -> bool:
    request = state.embrace_requests.get(request_id)
    if request is None or request.status != EmbraceStatus.REFUSED:
        return False
    if request.decision_night != state.night or embrace_was_enacted(state, request_id):
        return False

    requester = state.characters[request.requester_id]
    if not requester.clan_id:
        return False
    if requester.political_ambition != PoliticalAmbition.OBTAIN_EMBRACE:
        return False
    if requester.ambition < rules.clandestine_embrace_ambition_threshold:
        return False

    clan_state = state.clan_states[requester.clan_id]
    primogen_id = clan_state.clan.primogen_id
    side = clan_state.faction_memberships.get(requester.id, ClanFactionSide.PRIMOGEN)
    effective = effective_relation_to_primogen(state, requester.id)
    grievances = active_grievance_score(state, requester.id, primogen_id)
    return side == ClanFactionSide.OPPOSITION or effective <= 0 or grievances >= 2


def resolve_embrace_reactions(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Finalise les anciennes autorisations et les désobéissances de la nuit."""

    events: list[GameEvent] = []
    for request in sorted(state.embrace_requests.values(), key=lambda item: item.id):
        if request.status == EmbraceStatus.APPROVED and not embrace_was_enacted(state, request.id):
            event = enact_embrace(state, request.id, rules=rules)
            if event:
                events.append(event)

    for request in sorted(state.embrace_requests.values(), key=lambda item: item.id):
        if should_attempt_clandestine_embrace(state, request.id, rules):
            event = enact_embrace(state, request.id, clandestine=True, rules=rules)
            if event:
                events.append(event)
    return events


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

    initialize_factions(next_state)
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
    if approve:
        enacted = enact_embrace(next_state, request.id, rules=rules)
        if enacted:
            next_state.events.append(enacted)
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
    score = embrace_approval_score(next_state, member.id, request.political_cost, rules)
    approve = prince_should_approve_embrace(
        next_state,
        member.id,
        request.political_cost,
        rules,
    )
    next_state.events.append(
        GameEvent(
            night=next_state.night,
            category="cour",
            message=(
                f"Le Prince évalue la demande d'Étreinte de {member.name} : "
                f"score politique {score:+.0f} (seuil {rules.prince_embrace_approval_threshold:+.0f})."
            ),
            audience_clan_ids=(clan_id,),
        )
    )
    return decide_embrace_request(next_state, request.id, approve, rules)
