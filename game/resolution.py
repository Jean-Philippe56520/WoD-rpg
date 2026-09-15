from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Mapping

from .autonomy import resolve_autonomous_reactions
from .config import DEFAULT_RULES, GameRules
from .court import resolve_court_agenda
from .domains import (
    grant_hunting_right,
    has_hunting_access,
    initialize_domains,
    open_domain_dispute,
    resolve_domain_pressure,
    revoke_hunting_right,
)
from .embrace import process_primogen_petition
from .factions import determine_faction_stances, initialize_factions
from .hunger import resolve_hunger
from .models import (
    Candidate,
    DomainDecisionOrder,
    DomainDecisionType,
    EmbracePetitionOrder,
    GameAction,
    GameEvent,
    GameState,
    PoliticalRequestDecisionOrder,
    PrimogenVote,
)
from .offices import install_prince
from .politics import VoteResolution, resolve_praxis_vote
from .simultaneous import resolve_actions_simultaneously
from .social_politics import (
    add_grievance,
    create_boon,
    fulfill_promise,
    generate_requests_for_night,
    process_request_decision,
)


@dataclass(frozen=True)
class NightResolution:
    state: GameState
    vote: VoteResolution | None


def _validate_action_budget(
    state: GameState,
    actions: Iterable[GameAction],
    rules: GameRules,
) -> list[GameAction]:
    actions = list(actions)
    legacy_counts = {clan_id: 0 for clan_id in state.clan_states}
    used_actors: set[str] = set()

    for action in actions:
        if action.clan_id not in state.clan_states:
            raise ValueError(f"Unknown clan: {action.clan_id}")

        if action.actor_character_id is None:
            legacy_counts[action.clan_id] += 1
            if legacy_counts[action.clan_id] > rules.actions_per_clan:
                raise ValueError(
                    f"{state.clan_states[action.clan_id].clan.name}: "
                    f"maximum {rules.actions_per_clan} legacy actions per night"
                )
            continue

        actor = state.characters.get(action.actor_character_id)
        if actor is None or actor.clan_id != action.clan_id:
            raise ValueError("Action actor must belong to the acting clan")
        if actor.id == state.prince_id:
            raise ValueError("The Prince cannot act as a clan member")
        if actor.id in used_actors:
            raise ValueError(f"{actor.name} cannot perform more than one action per night")
        used_actors.add(actor.id)

    return actions


def _audience_for_characters(state: GameState, *character_ids: str) -> tuple[str, ...] | None:
    clans = {
        state.characters[character_id].clan_id
        for character_id in character_ids
        if character_id in state.characters and state.characters[character_id].clan_id
    }
    return tuple(sorted(clans)) or None


def _apply_domain_decision(
    state: GameState,
    clan_id: str,
    order: DomainDecisionOrder,
) -> GameEvent:
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    primogen = state.characters[primogen_id]
    domain = state.domains[order.domain_id]

    if order.decision == DomainDecisionType.GRANT_HUNTING_RIGHT:
        if not order.beneficiary_id:
            raise ValueError("Granting a hunting right requires a beneficiary")
        beneficiary = state.characters[order.beneficiary_id]
        if has_hunting_access(state, beneficiary.id, domain.id):
            return GameEvent(
                night=state.night,
                category="domaine",
                message=(
                    f"La concession prévue par {primogen.name} sur {domain.name} devient sans objet : "
                    f"{beneficiary.name} dispose déjà d'un droit de chasse reconnu."
                ),
                audience_clan_ids=_audience_for_characters(state, primogen_id, beneficiary.id),
            )
        boon_id = None
        if order.boon_level:
            boon = create_boon(
                state,
                creditor_id=primogen_id,
                debtor_id=beneficiary.id,
                level=order.boon_level,
                origin=f"Droit de chasse accordé sur {domain.name}",
            )
            boon_id = boon.id
        grant_hunting_right(
            state,
            domain_id=domain.id,
            beneficiary_id=beneficiary.id,
            granted_by_id=primogen_id,
            duration_nights=order.duration_nights,
            conditions="Concession directe du Primogène",
            boon_id=boon_id,
        )
        counterpart = (
            f" contre une faveur {order.boon_level.value}" if order.boon_level else ""
        )
        return GameEvent(
            night=state.night,
            category="domaine",
            message=(
                f"{primogen.name} accorde à {beneficiary.name} un droit de chasse sur "
                f"{domain.name} pour {order.duration_nights} nuits{counterpart}."
            ),
            audience_clan_ids=_audience_for_characters(state, primogen_id, beneficiary.id),
        )

    if not order.right_id:
        raise ValueError("Revoking a hunting right requires a right id")
    right = state.hunting_rights[order.right_id]
    beneficiary = state.characters[right.beneficiary_id]
    revoke_hunting_right(state, order.right_id, primogen_id)
    if beneficiary.id != primogen_id:
        add_grievance(
            state,
            owner_id=beneficiary.id,
            target_id=primogen_id,
            reason=f"Révocation du droit de chasse sur {domain.name}",
            severity=1,
        )
        open_domain_dispute(
            state,
            domain_id=domain.id,
            claimant_id=beneficiary.id,
            respondent_id=primogen_id,
            reason=f"Révocation contestée d'un droit de chasse sur {domain.name}",
            severity=1,
        )
    return GameEvent(
        night=state.night,
        category="domaine",
        message=(
            f"{primogen.name} révoque le droit de chasse de {beneficiary.name} sur {domain.name}. "
            "La décision crée une tension territoriale."
        ),
        audience_clan_ids=_audience_for_characters(state, primogen_id, beneficiary.id),
    )


def resolve_night(
    state: GameState,
    actions: Iterable[GameAction],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    embrace_petitions: Iterable[tuple[str, EmbracePetitionOrder]] = (),
    request_decisions: Iterable[tuple[str, PoliticalRequestDecisionOrder]] = (),
    domain_decisions: Iterable[tuple[str, DomainDecisionOrder]] = (),
    promise_fulfillments: Iterable[tuple[str, str]] = (),
    rules: GameRules = DEFAULT_RULES,
) -> NightResolution:
    next_state = deepcopy(state)
    initialize_factions(next_state)
    initialize_domains(next_state)
    had_prince_at_start = next_state.prince_id is not None
    actions = _validate_action_budget(next_state, actions, rules)
    candidates = list(candidates)
    candidate_map = {candidate.id: candidate for candidate in candidates}

    for clan_id, order in request_decisions:
        next_state.events.append(
            process_request_decision(next_state, clan_id, order.request_id, order.decision)
        )

    for clan_id, promise_id in promise_fulfillments:
        promise = next_state.promises[promise_id]
        fulfill_promise(next_state, promise_id)
        beneficiary = next_state.characters[promise.beneficiary_id]
        primogen = next_state.characters[promise.promisor_id]
        next_state.events.append(
            GameEvent(
                night=next_state.night,
                category="promesse",
                message=f"{primogen.name} honore sa promesse envers {beneficiary.name}.",
                audience_clan_ids=(clan_id,),
            )
        )

    for clan_id, order in domain_decisions:
        next_state.events.append(_apply_domain_decision(next_state, clan_id, order))

    next_state.events.extend(resolve_actions_simultaneously(next_state, actions, rules))

    initialize_factions(next_state)
    vote_result: VoteResolution | None = None
    # Si la Praxis vient de tomber pendant cette même nuit, aucun vote n'avait pu
    # être soumis dans les ordres. La nouvelle reconnaissance commence donc à la
    # nuit suivante, jamais rétroactivement dans la résolution en cours.
    if not had_prince_at_start and next_state.prince_id is None:
        stances = determine_faction_stances(next_state)
        for clan_id, stance in stances.items():
            clan_state = next_state.clan_states[clan_id]
            leader = next_state.characters[clan_state.opposition_leader_id]
            if stance.supports_primogen:
                message = (
                    f"La faction d'opposition de {clan_state.clan.name}, menée par {leader.name}, soutient "
                    f"le Primogène pour ce vote (score {stance.support_score:.0f})."
                )
            else:
                ally_name = next_state.characters[stance.allied_primogen_id].name
                message = (
                    f"La faction d'opposition de {clan_state.clan.name}, menée par {leader.name}, refuse "
                    f"le Primogène et active son alliance avec {ally_name}."
                )
            next_state.events.append(
                GameEvent(
                    night=next_state.night,
                    category="faction",
                    message=message,
                    audience_clan_ids=(clan_id,),
                )
            )

        vote_result = resolve_praxis_vote(
            state=next_state,
            stances=stances,
            votes=votes,
            candidates=candidates,
            opposition_transfer_ratio=rules.opposition_transfer_ratio,
            recognition_threshold=rules.praxis_recognition_threshold,
        )

        if vote_result.disputed:
            next_state.praxis_status = "contested"
            next_state.camarilla_stability = max(
                0.0, next_state.camarilla_stability - rules.disputed_stability_loss
            )
            next_state.masquerade_integrity = max(
                0.0, next_state.masquerade_integrity - rules.disputed_masquerade_loss
            )
            next_state.events.append(
                GameEvent(
                    night=next_state.night,
                    category="praxis",
                    message=(
                        "La Praxis reste contestée : aucun candidat ne rassemble une reconnaissance "
                        "politique suffisante. La Camarilla locale s'affaiblit."
                    ),
                )
            )
        else:
            winner = candidate_map[vote_result.winner_id]
            install_prince(next_state, winner, rules)
            next_state.camarilla_stability = min(
                100.0, next_state.camarilla_stability + rules.recognized_stability_gain
            )

    if had_prince_at_start and next_state.prince_id is not None:
        next_state.events.extend(resolve_court_agenda(next_state, rules))

    petitions = list(embrace_petitions)
    if len(petitions) > len(next_state.clan_states) * rules.embrace_petitions_per_clan:
        raise ValueError("Too many embrace petitions")
    if petitions and next_state.prince_id is None:
        for clan_id, petition in petitions:
            requester = next_state.characters[petition.member_id]
            next_state.events.append(
                GameEvent(
                    night=next_state.night,
                    category="embrace",
                    message=(
                        f"La demande d'Étreinte portée pour {requester.name} n'est pas examinée : "
                        "la Praxis vient de perdre sa reconnaissance et aucun Prince n'est en position "
                        "d'accorder l'autorisation cette nuit."
                    ),
                    audience_clan_ids=(clan_id,),
                )
            )
    elif petitions:
        counts: dict[str, int] = {}
        for clan_id, petition in petitions:
            counts[clan_id] = counts.get(clan_id, 0) + 1
            if counts[clan_id] > rules.embrace_petitions_per_clan:
                raise ValueError(
                    f"{clan_id}: maximum {rules.embrace_petitions_per_clan} embrace petition per night"
                )
            next_state = process_primogen_petition(next_state, clan_id, petition, rules)

    next_state.events.extend(resolve_autonomous_reactions(next_state, rules))
    # La chasse de routine se produit avant l'expiration territoriale de fin de
    # nuit : un droit reste donc exploitable pendant sa nuit d'échéance incluse.
    next_state.events.extend(resolve_hunger(next_state))
    next_state.events.extend(resolve_domain_pressure(next_state))
    initialize_factions(next_state)

    next_state.night += 1
    generate_requests_for_night(next_state)
    return NightResolution(state=next_state, vote=vote_result)
