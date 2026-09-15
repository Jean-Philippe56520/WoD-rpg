from __future__ import annotations

from .models import (
    BoonLevel,
    Domain,
    DomainDispute,
    DomainDisputeStatus,
    GameEvent,
    GameState,
    HuntingRight,
    HuntingRightStatus,
)


CANONICAL_DOMAINS: tuple[Domain, ...] = (
    Domain(
        id="quartier_affaires",
        name="Quartier des Affaires",
        description="Tours, sièges sociaux, hôtels et réseaux économiques très surveillés.",
        holder_id="primogen_ventrue",
        grantor_id=None,
        viandis=2,
        servage=3,
        rempart=2,
        masquerade_risk=1,
    ),
    Domain(
        id="vieux_centre",
        name="Vieux-Centre",
        description="Ruelles anciennes, commerces nocturnes et clientèle aisée de passage.",
        holder_id="ventrue_claire",
        grantor_id=None,
        viandis=2,
        servage=2,
        rempart=3,
        masquerade_risk=1,
    ),
    Domain(
        id="quartier_arts",
        name="Quartier des Arts",
        description="Galeries, salles de spectacle, bars et lieux de sociabilité culturelle.",
        holder_id="primogen_toreador",
        grantor_id=None,
        viandis=3,
        servage=2,
        rempart=1,
        masquerade_risk=2,
    ),
    Domain(
        id="campus_hopital",
        name="Campus et Hôpital",
        description="Population mobile, institutions médicales et réseaux académiques denses.",
        holder_id="toreador_camille",
        grantor_id=None,
        viandis=3,
        servage=2,
        rempart=2,
        masquerade_risk=2,
    ),
    Domain(
        id="docks",
        name="Les Docks",
        description="Zone portuaire, entrepôts, travailleurs de nuit et circuits logistiques.",
        holder_id="primogen_brujah",
        grantor_id=None,
        viandis=2,
        servage=2,
        rempart=2,
        masquerade_risk=1,
    ),
    Domain(
        id="faubourgs",
        name="Les Faubourgs",
        description="Quartiers périphériques étendus, réseaux de rue et contrôle diffus.",
        holder_id="brujah_sarah",
        grantor_id=None,
        viandis=2,
        servage=1,
        rempart=1,
        masquerade_risk=2,
    ),
)


def _next_id(prefix: str, values: dict[str, object]) -> str:
    index = len(values) + 1
    candidate = f"{prefix}_{index}"
    while candidate in values:
        index += 1
        candidate = f"{prefix}_{index}"
    return candidate


def initialize_domains(state: GameState) -> None:
    """Ajoute le socle territorial V0.10 aux sauvegardes antérieures sans écraser l'existant."""

    if not state.domains:
        state.domains = {
            template.id: Domain(
                id=template.id,
                name=template.name,
                description=template.description,
                holder_id=(template.holder_id if template.holder_id in state.characters else None),
                grantor_id=template.grantor_id,
                viandis=template.viandis,
                servage=template.servage,
                rempart=template.rempart,
                pressure=template.pressure,
                masquerade_risk=template.masquerade_risk,
            )
            for template in CANONICAL_DOMAINS
        }


def domain_holder_clan(state: GameState, domain_id: str) -> str | None:
    domain = state.domains.get(domain_id)
    if domain is None or not domain.holder_id:
        return None
    holder = state.characters.get(domain.holder_id)
    return holder.clan_id if holder else None


def active_hunting_rights(
    state: GameState,
    *,
    domain_id: str | None = None,
    beneficiary_id: str | None = None,
) -> list[HuntingRight]:
    return [
        right
        for right in state.hunting_rights.values()
        if right.status == HuntingRightStatus.ACTIVE
        and (domain_id is None or right.domain_id == domain_id)
        and (beneficiary_id is None or right.beneficiary_id == beneficiary_id)
    ]


def has_hunting_access(state: GameState, character_id: str, domain_id: str) -> bool:
    domain = state.domains.get(domain_id)
    if domain is None:
        raise ValueError("Unknown domain")
    if domain.holder_id == character_id:
        return True
    return any(
        right.domain_id == domain_id and right.beneficiary_id == character_id
        for right in active_hunting_rights(state)
    )


def _may_administer_domain(state: GameState, domain: Domain, character_id: str) -> bool:
    return character_id == domain.holder_id or character_id == state.prince_id


def grant_hunting_right(
    state: GameState,
    *,
    domain_id: str,
    beneficiary_id: str,
    granted_by_id: str,
    duration_nights: int = 3,
    conditions: str = "",
    boon_id: str | None = None,
) -> HuntingRight:
    domain = state.domains.get(domain_id)
    if domain is None:
        raise ValueError("Unknown domain")
    if beneficiary_id not in state.characters or granted_by_id not in state.characters:
        raise ValueError("Hunting-right participants must exist")
    if not _may_administer_domain(state, domain, granted_by_id):
        raise ValueError("Only the domain holder or Prince may grant hunting rights")
    if duration_nights < 1:
        raise ValueError("A hunting right must last at least one night")
    if has_hunting_access(state, beneficiary_id, domain_id):
        raise ValueError("This vampire already has hunting access to the domain")

    right = HuntingRight(
        id=_next_id("hunting_right", state.hunting_rights),
        domain_id=domain_id,
        beneficiary_id=beneficiary_id,
        granted_by_id=granted_by_id,
        created_night=state.night,
        expires_night=state.night + duration_nights,
        conditions=conditions.strip(),
        boon_id=boon_id,
    )
    state.hunting_rights[right.id] = right
    return right


def revoke_hunting_right(
    state: GameState,
    right_id: str,
    revoked_by_id: str,
) -> HuntingRight:
    right = state.hunting_rights.get(right_id)
    if right is None:
        raise ValueError("Unknown hunting right")
    domain = state.domains.get(right.domain_id)
    if domain is None:
        raise ValueError("Unknown domain")
    if not _may_administer_domain(state, domain, revoked_by_id):
        raise ValueError("Only the domain holder or Prince may revoke hunting rights")
    if right.status not in {HuntingRightStatus.ACTIVE, HuntingRightStatus.CONTESTED}:
        raise ValueError("This hunting right is no longer revocable")
    right.status = HuntingRightStatus.REVOKED
    right.resolved_night = state.night
    return right


def expire_hunting_rights(state: GameState) -> list[HuntingRight]:
    expired: list[HuntingRight] = []
    for right in state.hunting_rights.values():
        if (
            right.status == HuntingRightStatus.ACTIVE
            and right.expires_night is not None
            and state.night > right.expires_night
        ):
            right.status = HuntingRightStatus.EXPIRED
            right.resolved_night = state.night
            expired.append(right)
    return expired


def open_domain_dispute(
    state: GameState,
    *,
    domain_id: str,
    claimant_id: str,
    respondent_id: str,
    reason: str,
    severity: int = 1,
    public: bool = False,
) -> DomainDispute:
    if domain_id not in state.domains:
        raise ValueError("Unknown domain")
    if claimant_id not in state.characters or respondent_id not in state.characters:
        raise ValueError("Domain-dispute participants must exist")
    existing = next(
        (
            dispute
            for dispute in state.domain_disputes.values()
            if dispute.status == DomainDisputeStatus.OPEN
            and dispute.domain_id == domain_id
            and dispute.claimant_id == claimant_id
            and dispute.respondent_id == respondent_id
        ),
        None,
    )
    if existing:
        existing.severity = min(3, max(existing.severity, severity))
        existing.public = existing.public or public
        return existing
    dispute = DomainDispute(
        id=_next_id("domain_dispute", state.domain_disputes),
        domain_id=domain_id,
        claimant_id=claimant_id,
        respondent_id=respondent_id,
        reason=reason.strip() or "Litige territorial",
        created_night=state.night,
        severity=severity,
        public=public,
    )
    state.domain_disputes[dispute.id] = dispute
    return dispute


def resolve_domain_dispute(state: GameState, dispute_id: str) -> DomainDispute:
    dispute = state.domain_disputes.get(dispute_id)
    if dispute is None:
        raise ValueError("Unknown domain dispute")
    dispute.status = DomainDisputeStatus.RESOLVED
    dispute.resolved_night = state.night
    return dispute


def braconnage_pressure_gain(domain: Domain) -> int:
    return 1 + max(0, 2 - domain.viandis)


def register_braconnage(state: GameState, domain_id: str) -> int:
    domain = state.domains.get(domain_id)
    if domain is None:
        raise ValueError("Unknown domain")
    gain = braconnage_pressure_gain(domain)
    domain.pressure += gain
    return gain


def steward_domain(state: GameState, domain_id: str, holder_id: str, effort: int = 1) -> int:
    domain = state.domains.get(domain_id)
    if domain is None:
        raise ValueError("Unknown domain")
    if domain.holder_id != holder_id:
        raise ValueError("Only the holder may steward their personal domain")
    reduction = max(1, effort + domain.servage // 2)
    actual = min(domain.pressure, reduction)
    domain.pressure -= actual
    return actual


def intrusion_detected(domain: Domain, infiltration_score: int) -> bool:
    return infiltration_score < 2 + domain.rempart


def _right_overflow_pressure(state: GameState, domain: Domain) -> int:
    rights = len(active_hunting_rights(state, domain_id=domain.id))
    return max(0, rights - domain.viandis)


def resolve_domain_pressure(state: GameState) -> list[GameEvent]:
    """Résout surexploitation, échéances et risques de Mascarade en fin de nuit."""

    events: list[GameEvent] = []
    for right in expire_hunting_rights(state):
        beneficiary = state.characters[right.beneficiary_id]
        domain = state.domains[right.domain_id]
        events.append(
            GameEvent(
                night=state.night,
                category="domaine",
                message=f"Le droit de chasse de {beneficiary.name} sur {domain.name} arrive à échéance.",
                audience_clan_ids=(beneficiary.clan_id,) if beneficiary.clan_id else None,
            )
        )

    for domain in state.domains.values():
        overflow = _right_overflow_pressure(state, domain)
        if overflow:
            domain.pressure += overflow
        threshold = 4 + domain.rempart
        if domain.pressure < threshold:
            continue
        loss = max(1, domain.masquerade_risk)
        state.masquerade_integrity = max(0.0, state.masquerade_integrity - loss)
        domain.pressure = max(0, domain.pressure - 2)
        events.append(
            GameEvent(
                night=state.night,
                category="mascarade",
                message=(
                    f"La pression accumulée sur {domain.name} provoque un incident local : "
                    f"intégrité de la Mascarade -{loss}."
                ),
            )
        )
    return events
