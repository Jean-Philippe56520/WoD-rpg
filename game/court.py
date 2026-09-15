"""Cour de la Camarilla et arbitrages autonomes du Prince.

L'agenda n'est pas une liste aléatoire : il est dérivé des problèmes persistants
de la ville. Un litige ancien passe avant une crise de Mascarade, puis une crise
de stabilité. Les choix du Prince sont déterministes et explicables à partir de
sa personnalité, de ses relations et de son capital politique.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_RULES, GameRules
from .domains import resolve_domain_dispute
from .factions import ideology_relation_modifier
from .models import (
    BoonStatus,
    ClanFactionSide,
    DomainDisputeStatus,
    GameEvent,
    GameState,
    MortalStance,
    OrderStance,
    PoliticalAmbition,
)
from .social_politics import add_grievance


@dataclass(frozen=True)
class CourtIssue:
    id: str
    kind: str
    title: str
    description: str
    severity: int
    reference_id: str | None = None


def prince_policy_summary(state: GameState) -> str | None:
    if not state.prince_id or state.prince_id not in state.characters:
        return None
    prince = state.characters[state.prince_id]
    humanity = "protection de la Mascarade et des mortels" if prince.mortal_stance == MortalStance.HUMANIST else "efficacité prédatrice"
    order = "ordre et précédents" if prince.order_stance == OrderStance.ORTHODOX else "pragmatisme et réforme"
    ambition = {
        PoliticalAmbition.ENFORCE_ORDER: "consolider l'autorité de la Cour",
        PoliticalAmbition.RAPPROCHEMENT: "préserver les compromis entre clans",
        PoliticalAmbition.REFORM_CLAN: "faire évoluer les équilibres établis",
        PoliticalAmbition.INCREASE_INFLUENCE: "accroître son réseau personnel",
    }.get(prince.political_ambition, "préserver sa position")
    return f"{humanity} · {order} · priorité : {ambition}"


def current_court_issue(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> CourtIssue | None:
    if not state.prince_id:
        return None

    disputes = sorted(
        (
            dispute
            for dispute in state.domain_disputes.values()
            if dispute.status == DomainDisputeStatus.OPEN
            and dispute.created_night < state.night
        ),
        key=lambda dispute: (
            not dispute.public,
            -dispute.severity,
            dispute.created_night,
            dispute.id,
        ),
    )
    if disputes:
        dispute = disputes[0]
        domain = state.domains[dispute.domain_id]
        claimant = state.characters[dispute.claimant_id]
        respondent = state.characters[dispute.respondent_id]
        return CourtIssue(
            id=f"court_domain_{dispute.id}",
            kind="domain_arbitration",
            title=f"Arbitrage territorial — {domain.name}",
            description=(
                f"{claimant.name} oppose une revendication à {respondent.name} : {dispute.reason}. "
                "Le Prince doit soutenir l'une des parties ou laisser le litige miner la Cour."
            ),
            severity=dispute.severity,
            reference_id=dispute.id,
        )

    if state.masquerade_integrity <= rules.prince_masquerade_crisis_threshold:
        return CourtIssue(
            id=f"court_masquerade_{state.night}",
            kind="masquerade_crisis",
            title="Crise de Mascarade",
            description=(
                f"L'intégrité de la Mascarade est tombée à {state.masquerade_integrity:.0f} %. "
                "La Cour attend une réponse du Prince."
            ),
            severity=2,
        )

    if state.camarilla_stability <= rules.prince_stability_crisis_threshold:
        return CourtIssue(
            id=f"court_stability_{state.night}",
            kind="stability_crisis",
            title="Fracture de la Cour",
            description=(
                f"La stabilité locale est tombée à {state.camarilla_stability:.0f} %. "
                "Le Prince doit restaurer un minimum de confiance entre les clans."
            ),
            severity=2,
        )
    return None


def _party_score(state: GameState, character_id: str, domain_holder_id: str | None) -> float:
    prince = state.characters[state.prince_id]
    character = state.characters[character_id]
    clan_relation = state.prince_relations.get(character.clan_id or "", 0.0)
    score = clan_relation + character.status * 2 + character.reputation * 2
    score += ideology_relation_modifier(prince, character) * 2
    if character.id == domain_holder_id:
        score += 4 if prince.order_stance == OrderStance.ORTHODOX else 1
    # Une faveur appelée au Prince est un levier politique réel, sans garantir
    # mécaniquement le résultat.
    score += 3 * sum(
        1
        for boon in state.boons.values()
        if boon.debtor_id == prince.id
        and boon.creditor_id == character.id
        and boon.status == BoonStatus.CALLED
    )
    return score


def _resolve_domain_arbitration(
    state: GameState,
    issue: CourtIssue,
    rules: GameRules,
) -> GameEvent:
    dispute = state.domain_disputes[issue.reference_id]
    domain = state.domains[dispute.domain_id]
    prince = state.characters[state.prince_id]
    if state.prince_political_capital < rules.prince_domain_arbitration_cost:
        state.camarilla_stability = max(0.0, state.camarilla_stability - 1)
        return GameEvent(
            night=state.night,
            category="cour",
            message=(
                f"{prince.name} diffère l'arbitrage sur {domain.name}, faute de capital politique. "
                "La Cour interprète cette faiblesse : stabilité -1."
            ),
        )

    claimant_score = _party_score(state, dispute.claimant_id, domain.holder_id)
    respondent_score = _party_score(state, dispute.respondent_id, domain.holder_id)
    if claimant_score == respondent_score:
        winner_id = domain.holder_id if domain.holder_id in {dispute.claimant_id, dispute.respondent_id} else dispute.claimant_id
    else:
        winner_id = dispute.claimant_id if claimant_score > respondent_score else dispute.respondent_id
    loser_id = dispute.respondent_id if winner_id == dispute.claimant_id else dispute.claimant_id

    state.prince_political_capital -= rules.prince_domain_arbitration_cost
    resolve_domain_dispute(state, dispute.id)
    winner = state.characters[winner_id]
    loser = state.characters[loser_id]
    if winner.clan_id:
        state.prince_relations[winner.clan_id] = state.prince_relations.get(winner.clan_id, 0.0) + 1
    if loser.clan_id:
        state.prince_relations[loser.clan_id] = state.prince_relations.get(loser.clan_id, 0.0) - 2
    add_grievance(
        state,
        owner_id=loser.id,
        target_id=prince.id,
        reason=f"Arbitrage princier défavorable sur {domain.name}",
        severity=max(1, dispute.severity - 1),
    )
    return GameEvent(
        night=state.night,
        category="cour",
        message=(
            f"{prince.name} tranche le litige de {domain.name} en faveur de {winner.name}. "
            f"{loser.name} encaisse publiquement la décision et nourrit un grief contre le Prince."
        ),
    )


def _resolve_masquerade_crisis(
    state: GameState,
    rules: GameRules,
) -> GameEvent:
    prince = state.characters[state.prince_id]
    humanist = prince.mortal_stance == MortalStance.HUMANIST
    cost = rules.prince_masquerade_response_cost
    if state.prince_political_capital < cost:
        state.masquerade_integrity = max(0.0, state.masquerade_integrity - 1)
        state.camarilla_stability = max(0.0, state.camarilla_stability - 1)
        return GameEvent(
            night=state.night,
            category="cour",
            message=(
                f"{prince.name} ne parvient pas à financer une réponse crédible à la crise. "
                "Mascarade -1, stabilité -1."
            ),
        )

    state.prince_political_capital -= cost
    restoration = rules.prince_masquerade_response_gain + (1 if not humanist else 0)
    state.masquerade_integrity = min(100.0, state.masquerade_integrity + restoration)
    if not humanist:
        state.camarilla_stability = max(0.0, state.camarilla_stability - 1)
        tone = "une répression brutale des témoins et réseaux compromis"
    else:
        tone = "une opération de confinement et de désinformation ciblée"
    return GameEvent(
        night=state.night,
        category="cour",
        message=(
            f"{prince.name} ordonne {tone}. Intégrité de la Mascarade +{restoration:.0f}."
            + (" Stabilité -1." if not humanist else "")
        ),
    )


def _resolve_stability_crisis(
    state: GameState,
    rules: GameRules,
) -> GameEvent:
    prince = state.characters[state.prince_id]
    weakest_clan = min(
        state.clan_states,
        key=lambda clan_id: (state.prince_relations.get(clan_id, 0.0), clan_id),
    )
    clan_name = state.clan_states[weakest_clan].clan.name
    if state.prince_political_capital < rules.prince_stability_response_cost:
        state.camarilla_stability = max(0.0, state.camarilla_stability - 1)
        return GameEvent(
            night=state.night,
            category="cour",
            message=(
                f"{prince.name} ne parvient pas à calmer la fracture de la Cour. Stabilité -1."
            ),
        )
    state.prince_political_capital -= rules.prince_stability_response_cost
    state.prince_relations[weakest_clan] = state.prince_relations.get(weakest_clan, 0.0) + 2
    state.camarilla_stability = min(100.0, state.camarilla_stability + rules.prince_stability_response_gain)
    return GameEvent(
        night=state.night,
        category="cour",
        message=(
            f"{prince.name} concède publiquement du terrain politique au clan {clan_name}. "
            f"Stabilité +{rules.prince_stability_response_gain:.0f}; relation du Prince avec {clan_name} +2."
        ),
    )


def resolve_court_agenda(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    issue = current_court_issue(state, rules)
    if issue is None:
        return []
    if issue.kind == "domain_arbitration":
        return [_resolve_domain_arbitration(state, issue, rules)]
    if issue.kind == "masquerade_crisis":
        return [_resolve_masquerade_crisis(state, rules)]
    return [_resolve_stability_crisis(state, rules)]


def embrace_approval_score(
    state: GameState,
    requester_id: str,
    political_cost: float,
    rules: GameRules = DEFAULT_RULES,
) -> float:
    """Score explicable de l'arbitrage autonome d'une demande d'Étreinte."""

    if not state.prince_id:
        return float("-inf")
    prince = state.characters[state.prince_id]
    requester = state.characters[requester_id]
    if state.prince_political_capital < political_cost:
        return float("-inf")

    score = state.prince_relations.get(requester.clan_id or "", 0.0)
    score += requester.reputation * 2 + requester.status
    score += ideology_relation_modifier(prince, requester) * 2
    if requester.clan_id:
        side = state.clan_states[requester.clan_id].faction_memberships.get(
            requester.id, ClanFactionSide.PRIMOGEN
        )
        score += 1 if side == ClanFactionSide.PRIMOGEN else -2
    if prince.order_stance == OrderStance.ORTHODOX:
        score -= 1
    if state.masquerade_integrity <= rules.prince_masquerade_crisis_threshold:
        score -= 3
    if state.prince_political_capital - political_cost < rules.prince_capital_reserve:
        score -= 2
    return score


def prince_should_approve_embrace(
    state: GameState,
    requester_id: str,
    political_cost: float,
    rules: GameRules = DEFAULT_RULES,
) -> bool:
    return embrace_approval_score(state, requester_id, political_cost, rules) >= rules.prince_embrace_approval_threshold
