from __future__ import annotations

from .domains import grant_hunting_right, initialize_domains
from .factions import effective_relation_to_primogen
from .models import (
    Boon,
    BoonLevel,
    BoonStatus,
    GameEvent,
    GameState,
    Grievance,
    PoliticalAmbition,
    PoliticalPromise,
    PoliticalRequest,
    PoliticalRequestStatus,
    PoliticalRequestType,
    PromiseStatus,
    RequestDecision,
)


def _next_id(prefix: str, values: dict[str, object]) -> str:
    index = len(values) + 1
    candidate = f"{prefix}_{index}"
    while candidate in values:
        index += 1
        candidate = f"{prefix}_{index}"
    return candidate


def _clamp_relation(value: int) -> int:
    return max(0, min(2, value))


def _clamp_reputation(value: int) -> int:
    return max(-3, min(3, value))


def create_boon(
    state: GameState,
    *,
    creditor_id: str,
    debtor_id: str,
    level: BoonLevel,
    origin: str,
    public: bool = False,
) -> Boon:
    if creditor_id == debtor_id:
        raise ValueError("A vampire cannot owe a boon to themselves")
    if creditor_id not in state.characters or debtor_id not in state.characters:
        raise ValueError("Boon participants must exist")
    boon = Boon(
        id=_next_id("boon", state.boons),
        creditor_id=creditor_id,
        debtor_id=debtor_id,
        level=BoonLevel(level),
        origin=origin.strip() or "Prestation",
        created_night=state.night,
        public=public,
    )
    state.boons[boon.id] = boon
    return boon


def call_boon(state: GameState, boon_id: str, creditor_id: str) -> Boon:
    boon = state.boons.get(boon_id)
    if boon is None:
        raise ValueError("Unknown boon")
    if boon.creditor_id != creditor_id:
        raise ValueError("Only the creditor may call a boon")
    if boon.status != BoonStatus.DUE:
        raise ValueError("Only a due boon may be called")
    boon.status = BoonStatus.CALLED
    boon.called_night = state.night
    return boon


def fulfill_boon(state: GameState, boon_id: str) -> Boon:
    boon = state.boons.get(boon_id)
    if boon is None:
        raise ValueError("Unknown boon")
    if boon.status not in {BoonStatus.DUE, BoonStatus.CALLED}:
        raise ValueError("This boon can no longer be fulfilled")
    boon.status = BoonStatus.FULFILLED
    boon.resolved_night = state.night
    debtor = state.characters[boon.debtor_id]
    debtor.reputation = _clamp_reputation(debtor.reputation + 1)
    return boon


def add_grievance(
    state: GameState,
    *,
    owner_id: str,
    target_id: str,
    reason: str,
    severity: int = 1,
) -> Grievance:
    if owner_id not in state.characters or target_id not in state.characters:
        raise ValueError("Grievance participants must exist")
    grievance = Grievance(
        id=_next_id("grievance", state.grievances),
        owner_id=owner_id,
        target_id=target_id,
        reason=reason.strip() or "Grief politique",
        severity=severity,
        created_night=state.night,
    )
    state.grievances[grievance.id] = grievance
    return grievance


def refuse_boon(state: GameState, boon_id: str, reason: str = "Prestation refusée") -> Boon:
    boon = state.boons.get(boon_id)
    if boon is None:
        raise ValueError("Unknown boon")
    if boon.status not in {BoonStatus.DUE, BoonStatus.CALLED}:
        raise ValueError("This boon can no longer be refused")
    boon.status = BoonStatus.REFUSED
    boon.resolved_night = state.night
    severity = {BoonLevel.MINOR: 1, BoonLevel.MAJOR: 2, BoonLevel.LIFE: 3}[boon.level]
    debtor = state.characters[boon.debtor_id]
    debtor.reputation = _clamp_reputation(debtor.reputation - severity)
    add_grievance(
        state,
        owner_id=boon.creditor_id,
        target_id=boon.debtor_id,
        reason=reason,
        severity=severity,
    )
    return boon


def resolve_grievance(state: GameState, grievance_id: str) -> Grievance:
    grievance = state.grievances.get(grievance_id)
    if grievance is None:
        raise ValueError("Unknown grievance")
    grievance.resolved = True
    return grievance


def active_grievance_score(
    state: GameState,
    owner_id: str,
    target_id: str | None = None,
) -> int:
    return sum(
        grievance.severity
        for grievance in state.grievances.values()
        if grievance.owner_id == owner_id
        and not grievance.resolved
        and (target_id is None or grievance.target_id == target_id)
    )


_REQUEST_BY_AMBITION = {
    PoliticalAmbition.INCREASE_INFLUENCE: PoliticalRequestType.PATRONAGE,
    PoliticalAmbition.OBTAIN_EMBRACE: PoliticalRequestType.EMBRACE_SUPPORT,
    PoliticalAmbition.GAIN_DOMAIN: PoliticalRequestType.DOMAIN_ACCESS,
    PoliticalAmbition.GAIN_BOON: PoliticalRequestType.BOON,
    PoliticalAmbition.LEAD_OPPOSITION: PoliticalRequestType.RESPONSIBILITY,
    PoliticalAmbition.WEAKEN_RIVAL: PoliticalRequestType.INTERNAL_CONFLICT,
    PoliticalAmbition.RAPPROCHEMENT: PoliticalRequestType.MISSION,
    PoliticalAmbition.ENFORCE_ORDER: PoliticalRequestType.POLICY,
    PoliticalAmbition.REFORM_CLAN: PoliticalRequestType.POLICY,
    PoliticalAmbition.BECOME_PRIMOGEN: PoliticalRequestType.RESPONSIBILITY,
}


def _domain_target_for_request(state: GameState, requester_id: str) -> str | None:
    requester = state.characters[requester_id]
    if not requester.clan_id:
        return None
    primogen_id = state.clan_states[requester.clan_id].clan.primogen_id
    candidates = sorted(
        (
            domain
            for domain in state.domains.values()
            if domain.holder_id == primogen_id
        ),
        key=lambda domain: (-domain.viandis, -domain.servage, domain.id),
    )
    return candidates[0].id if candidates else None


def _request_description(
    state: GameState,
    requester_id: str,
    request_type: PoliticalRequestType,
    target_id: str | None = None,
) -> str:
    requester = state.characters[requester_id]
    if request_type == PoliticalRequestType.DOMAIN_ACCESS:
        domain = state.domains.get(target_id or "")
        domain_name = domain.name if domain else "un Domaine du Primogène"
        return f"{requester.name} demande un droit de chasse reconnu sur {domain_name}."
    descriptions = {
        PoliticalRequestType.EMBRACE_SUPPORT: f"{requester.name} demande que le Primogène soutienne sa future demande d'Étreinte.",
        PoliticalRequestType.RESPONSIBILITY: f"{requester.name} réclame davantage de responsabilités politiques dans le clan.",
        PoliticalRequestType.PATRONAGE: f"{requester.name} demande le patronage du Primogène pour renforcer sa position.",
        PoliticalRequestType.INTERNAL_CONFLICT: f"{requester.name} demande au Primogène de prendre parti dans une rivalité interne.",
        PoliticalRequestType.BOON: f"{requester.name} sollicite une faveur personnelle du Primogène.",
        PoliticalRequestType.MISSION: f"{requester.name} demande à représenter le clan dans une mission politique importante.",
        PoliticalRequestType.POLICY: f"{requester.name} exige une inflexion de la ligne politique du clan.",
    }
    return descriptions[request_type]


def generate_requests_for_night(state: GameState) -> list[PoliticalRequest]:
    """Crée au plus une requête motivée par clan et par nuit, sans hasard."""

    initialize_domains(state)
    created: list[PoliticalRequest] = []
    existing_keys = {
        (request.clan_id, request.created_night)
        for request in state.political_requests.values()
    }
    for clan_id, clan_state in state.clan_states.items():
        if (clan_id, state.night) in existing_keys:
            continue
        primogen_id = clan_state.clan.primogen_id
        candidates = [
            character
            for character in state.characters.values()
            if character.clan_id == clan_id
            and character.id not in {primogen_id, state.prince_id}
            and not any(
                request.requester_id == character.id
                and request.status in {PoliticalRequestStatus.OPEN, PoliticalRequestStatus.PROMISED}
                for request in state.political_requests.values()
            )
        ]
        if not candidates:
            continue

        def priority(character) -> tuple[float, int, int, str]:
            grievance = active_grievance_score(state, character.id, primogen_id)
            opposition_bonus = 15 if clan_state.opposition_leader_id == character.id else 0
            return (
                character.ambition + grievance * 10 + opposition_bonus,
                character.status,
                int(character.personal_influence),
                character.id,
            )

        requester = max(candidates, key=priority)
        request_type = _REQUEST_BY_AMBITION[requester.political_ambition]
        target_id = None
        if request_type == PoliticalRequestType.DOMAIN_ACCESS:
            target_id = _domain_target_for_request(state, requester.id)
            if target_id is None:
                request_type = PoliticalRequestType.PATRONAGE

        offered_boon = (
            BoonLevel.MINOR
            if effective_relation_to_primogen(state, requester.id) <= 1
            and requester.political_ambition in {
                PoliticalAmbition.OBTAIN_EMBRACE,
                PoliticalAmbition.GAIN_DOMAIN,
                PoliticalAmbition.GAIN_BOON,
                PoliticalAmbition.BECOME_PRIMOGEN,
            }
            else None
        )
        request = PoliticalRequest(
            id=_next_id("request", state.political_requests),
            clan_id=clan_id,
            requester_id=requester.id,
            request_type=request_type,
            description=_request_description(state, requester.id, request_type, target_id),
            created_night=state.night,
            target_id=target_id,
            offered_boon_level=offered_boon,
        )
        state.political_requests[request.id] = request
        created.append(request)
    return created


def _grant_requested_domain_access(
    state: GameState,
    request: PoliticalRequest,
    primogen_id: str,
    *,
    boon_level: BoonLevel | None,
) -> str:
    if not request.target_id or request.target_id not in state.domains:
        raise ValueError("Domain-access request has no valid target domain")
    requester = state.characters[request.requester_id]
    boon_id = None
    if boon_level:
        boon = create_boon(
            state,
            creditor_id=primogen_id,
            debtor_id=requester.id,
            level=boon_level,
            origin=f"Droit de chasse accordé sur {state.domains[request.target_id].name}",
        )
        boon_id = boon.id
    right = grant_hunting_right(
        state,
        domain_id=request.target_id,
        beneficiary_id=requester.id,
        granted_by_id=primogen_id,
        duration_nights=3,
        conditions=f"Accès politique issu de la requête {request.id}",
        boon_id=boon_id,
    )
    return right.id


def process_request_decision(
    state: GameState,
    clan_id: str,
    request_id: str,
    decision: RequestDecision,
) -> GameEvent:
    request = state.political_requests.get(request_id)
    if request is None or request.clan_id != clan_id:
        raise ValueError("Unknown political request for this clan")
    if request.status != PoliticalRequestStatus.OPEN:
        raise ValueError("This political request is no longer open")

    clan_state = state.clan_states[clan_id]
    primogen = state.characters[clan_state.clan.primogen_id]
    requester = state.characters[request.requester_id]
    decision = RequestDecision(decision)
    request.response_night = state.night

    if decision == RequestDecision.ACCEPT:
        request.status = PoliticalRequestStatus.ACCEPTED
        requester.relation_to_primogen = _clamp_relation(requester.relation_to_primogen + 1)
        if request.request_type == PoliticalRequestType.DOMAIN_ACCESS:
            _grant_requested_domain_access(
                state,
                request,
                primogen.id,
                boon_level=request.offered_boon_level,
            )
            domain = state.domains[request.target_id]
            message = (
                f"{primogen.name} accorde à {requester.name} un droit de chasse sur {domain.name}. "
                "Leur relation se renforce."
            )
        else:
            if request.offered_boon_level:
                create_boon(
                    state,
                    creditor_id=primogen.id,
                    debtor_id=requester.id,
                    level=request.offered_boon_level,
                    origin=f"Contrepartie à la requête {request.id}",
                )
            message = f"{primogen.name} accepte la requête de {requester.name}. Leur relation se renforce."

    elif decision == RequestDecision.REFUSE:
        request.status = PoliticalRequestStatus.REFUSED
        requester.relation_to_primogen = _clamp_relation(requester.relation_to_primogen - 1)
        severity = 2 if request.request_type == PoliticalRequestType.EMBRACE_SUPPORT else 1
        add_grievance(
            state,
            owner_id=requester.id,
            target_id=primogen.id,
            reason=f"Requête refusée : {request.description}",
            severity=severity,
        )
        message = f"{primogen.name} refuse la requête de {requester.name}. Un grief politique est créé."

    elif decision == RequestDecision.NEGOTIATE:
        request.status = PoliticalRequestStatus.NEGOTIATED
        if request.request_type == PoliticalRequestType.DOMAIN_ACCESS:
            boon_level = request.offered_boon_level or BoonLevel.MINOR
            _grant_requested_domain_access(
                state,
                request,
                primogen.id,
                boon_level=boon_level,
            )
            domain = state.domains[request.target_id]
            message = (
                f"{primogen.name} accorde à {requester.name} un droit de chasse sur {domain.name} "
                f"contre une faveur {boon_level.value}."
            )
        else:
            boon = create_boon(
                state,
                creditor_id=primogen.id,
                debtor_id=requester.id,
                level=request.offered_boon_level or BoonLevel.MINOR,
                origin=f"Négociation de la requête {request.id}",
            )
            message = (
                f"{primogen.name} négocie avec {requester.name}. "
                f"{requester.name} contracte une faveur {boon.level.value}."
            )

    else:
        request.status = PoliticalRequestStatus.PROMISED
        promise = PoliticalPromise(
            id=_next_id("promise", state.promises),
            promisor_id=primogen.id,
            beneficiary_id=requester.id,
            description=request.description,
            created_night=state.night,
            due_night=state.night + 2,
            request_id=request.id,
        )
        state.promises[promise.id] = promise
        message = (
            f"{primogen.name} promet à {requester.name} de traiter sa requête avant la nuit "
            f"{promise.due_night}."
        )

    return GameEvent(
        night=state.night,
        category="politique_interne",
        message=message,
        audience_clan_ids=(clan_id,),
    )


def fulfill_promise(state: GameState, promise_id: str) -> PoliticalPromise:
    promise = state.promises.get(promise_id)
    if promise is None:
        raise ValueError("Unknown political promise")
    if promise.status != PromiseStatus.PENDING:
        raise ValueError("Promise is no longer pending")
    if promise.request_id and promise.request_id in state.political_requests:
        request = state.political_requests[promise.request_id]
        if request.request_type == PoliticalRequestType.DOMAIN_ACCESS:
            _grant_requested_domain_access(
                state,
                request,
                promise.promisor_id,
                boon_level=None,
            )
        request.status = PoliticalRequestStatus.RESOLVED
    promise.status = PromiseStatus.FULFILLED
    promise.resolved_night = state.night
    beneficiary = state.characters[promise.beneficiary_id]
    beneficiary.relation_to_primogen = _clamp_relation(beneficiary.relation_to_primogen + 1)
    return promise


def expire_broken_promises(state: GameState) -> list[PoliticalPromise]:
    broken: list[PoliticalPromise] = []
    for promise in state.promises.values():
        if promise.status != PromiseStatus.PENDING or state.night <= promise.due_night:
            continue
        promise.status = PromiseStatus.BROKEN
        promise.resolved_night = state.night
        beneficiary = state.characters[promise.beneficiary_id]
        beneficiary.relation_to_primogen = _clamp_relation(beneficiary.relation_to_primogen - 1)
        promisor = state.characters[promise.promisor_id]
        promisor.reputation = _clamp_reputation(promisor.reputation - 1)
        add_grievance(
            state,
            owner_id=promise.beneficiary_id,
            target_id=promise.promisor_id,
            reason=f"Promesse non tenue : {promise.description}",
            severity=2,
        )
        if promise.request_id and promise.request_id in state.political_requests:
            state.political_requests[promise.request_id].status = PoliticalRequestStatus.REFUSED
        broken.append(promise)
    return broken
