"""Rumeurs persistantes dérivées des enquêtes.

Les rumeurs sont event-sourcées : aucune nouvelle table n'est nécessaire. La vérité
est encodée dans la catégorie interne de l'événement et n'est révélée à l'interface
qu'après corroboration. Une affirmation peut donc être vraie ou fausse sans que le
joueur le sache au premier renseignement.
"""

from __future__ import annotations

from dataclasses import dataclass

from .factions import effective_relation_to_primogen
from .models import ClanFactionSide, GameEvent, GameState, PoliticalAmbition
from .social_politics import active_grievance_score


RUMOR_PREFIX = "rumeur|"


@dataclass(frozen=True)
class RumorView:
    id: str
    subject_id: str
    claim: str
    created_night: int
    confidence: int
    status: str
    truth: bool


def _parse_category(category: str):
    if not category.startswith(RUMOR_PREFIX):
        return None
    parts = category.split("|")
    if len(parts) != 7:
        return None
    _, rumor_id, truth_raw, subject_id, kind, stage, created_raw = parts
    try:
        created_night = int(created_raw)
    except ValueError:
        return None
    return rumor_id, truth_raw == "1", subject_id, kind, stage, created_night


def rumor_views(state: GameState, clan_id: str) -> tuple[RumorView, ...]:
    grouped: dict[str, dict] = {}
    for event in state.events:
        parsed = _parse_category(event.category)
        if parsed is None or not event.visible_to(clan_id):
            continue
        rumor_id, truth, subject_id, _kind, stage, created_night = parsed
        item = grouped.setdefault(
            rumor_id,
            {
                "subject_id": subject_id,
                "truth": truth,
                "created_night": created_night,
                "claim": "",
                "evidence": 0,
                "verified": False,
            },
        )
        if stage == "lead":
            item["evidence"] += 1
            if not item["claim"]:
                item["claim"] = event.message.removeprefix("Rumeur : ").strip()
        elif stage == "verify":
            item["verified"] = True
            item["evidence"] = max(2, item["evidence"])

    views: list[RumorView] = []
    for rumor_id, item in grouped.items():
        confidence = min(2, max(1, item["evidence"]))
        if item["verified"] or confidence >= 2:
            status = "confirmed" if item["truth"] else "disproved"
            confidence = 2
        else:
            status = "unverified"
        views.append(
            RumorView(
                id=rumor_id,
                subject_id=item["subject_id"],
                claim=item["claim"],
                created_night=item["created_night"],
                confidence=confidence,
                status=status,
                truth=item["truth"],
            )
        )
    return tuple(sorted(views, key=lambda item: (item.created_night, item.id), reverse=True))


def _deterministic_variant(subject_id: str, night: int) -> int:
    return sum(ord(char) for char in f"{subject_id}:{night}") % 3


def _deterministic_flip(subject_id: str, night: int) -> bool:
    return sum(ord(char) for char in f"{night}:{subject_id}:source") % 2 == 0


def _new_claim(state: GameState, subject_id: str) -> tuple[str, str, bool]:
    subject = state.characters[subject_id]
    if not subject.clan_id:
        raise ValueError("Rumor subject must belong to a clan")
    clan_state = state.clan_states[subject.clan_id]
    primogen_id = clan_state.clan.primogen_id
    variant = _deterministic_variant(subject_id, state.night)

    if variant == 0:
        actual_opposition = (
            clan_state.faction_memberships.get(subject_id, ClanFactionSide.PRIMOGEN)
            == ClanFactionSide.OPPOSITION
        )
        claim_opposition = actual_opposition if _deterministic_flip(subject_id, state.night) else not actual_opposition
        if claim_opposition:
            claim = f"{subject.name} appartiendrait réellement à la faction d'opposition de son clan."
        else:
            claim = f"{subject.name} resterait solidement aligné avec la faction de son Primogène."
        return "faction", claim, claim_opposition == actual_opposition

    if variant == 1:
        has_grievance = active_grievance_score(state, subject_id, primogen_id) >= 1
        primogen = state.characters[primogen_id]
        claim = f"{subject.name} nourrirait un grief personnel contre {primogen.name}."
        return "grievance", claim, has_grievance

    wants_seat = subject.political_ambition == PoliticalAmbition.BECOME_PRIMOGEN
    effective = effective_relation_to_primogen(state, subject_id)
    claim = (
        f"{subject.name} préparerait une rupture politique avec son Primogène et chercherait à prendre sa place."
    )
    return "ambition", claim, wants_seat and effective <= 0


def investigation_rumor_event(
    state: GameState,
    clan_id: str,
    subject_id: str,
    actor_id: str,
) -> GameEvent:
    """Crée une nouvelle rumeur ou vérifie d'abord une rumeur encore incertaine."""

    subject = state.characters[subject_id]
    actor = state.characters[actor_id]
    target_clan_id = subject.clan_id
    unresolved = [
        rumor
        for rumor in rumor_views(state, clan_id)
        if rumor.status == "unverified"
        and state.characters.get(rumor.subject_id)
        and state.characters[rumor.subject_id].clan_id == target_clan_id
    ]
    if unresolved:
        rumor = unresolved[0]
        verdict = "corroborée" if rumor.truth else "démentie"
        category = (
            f"{RUMOR_PREFIX}{rumor.id}|{1 if rumor.truth else 0}|{rumor.subject_id}|"
            f"verification|verify|{rumor.created_night}"
        )
        return GameEvent(
            night=state.night,
            category=category,
            message=(
                f"Vérification : {actor.name} obtient une seconde source ; la rumeur concernant "
                f"{state.characters[rumor.subject_id].name} est {verdict}."
            ),
            audience_clan_ids=(clan_id,),
        )

    kind, claim, truth = _new_claim(state, subject_id)
    variant = _deterministic_variant(subject_id, state.night)
    rumor_id = f"{subject_id}_{state.night}_{variant}"
    category = (
        f"{RUMOR_PREFIX}{rumor_id}|{1 if truth else 0}|{subject_id}|{kind}|lead|{state.night}"
    )
    return GameEvent(
        night=state.night,
        category=category,
        message=f"Rumeur : {claim}",
        audience_clan_ids=(clan_id,),
    )
