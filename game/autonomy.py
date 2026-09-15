from __future__ import annotations

from .factions import (
    effective_relation_to_primogen,
    ideology_relation_modifier,
    initialize_factions,
    set_faction_side,
)
from .models import BoonLevel, BoonStatus, ClanFactionSide, GameEvent, GameState, PoliticalAmbition
from .social_politics import active_grievance_score, expire_broken_promises, fulfill_boon, refuse_boon


def _resolve_called_boons(state: GameState) -> list[GameEvent]:
    events: list[GameEvent] = []
    for boon in state.boons.values():
        if boon.status != BoonStatus.CALLED:
            continue
        creditor = state.characters[boon.creditor_id]
        debtor = state.characters[boon.debtor_id]
        severe_grievance = active_grievance_score(state, debtor.id, creditor.id) >= 2
        may_refuse_minor = severe_grievance or creditor.reputation <= -2
        if boon.level == BoonLevel.MINOR and may_refuse_minor:
            refuse_boon(state, boon.id, "Refus d'honorer une faveur réclamée")
            message = (
                f"{debtor.name} refuse d'honorer une faveur mineure due à {creditor.name}. "
                "Sa réputation en souffre."
            )
        else:
            fulfill_boon(state, boon.id)
            message = f"{debtor.name} honore la faveur due à {creditor.name}."
        audiences = tuple(
            sorted(
                {
                    clan_id
                    for clan_id in (creditor.clan_id, debtor.clan_id)
                    if clan_id is not None
                }
            )
        ) or None
        events.append(
            GameEvent(
                night=state.night,
                category="prestation",
                message=message,
                audience_clan_ids=audiences,
            )
        )
    return events


def _defection_reactions(state: GameState) -> list[GameEvent]:
    events: list[GameEvent] = []
    initialize_factions(state)
    for clan_id, clan_state in state.clan_states.items():
        primogen_id = clan_state.clan.primogen_id
        leader_id = clan_state.opposition_leader_id
        if not leader_id:
            continue
        leader = state.characters[leader_id]
        candidates = [
            character
            for character in state.characters.values()
            if character.clan_id == clan_id
            and character.id not in {primogen_id, leader_id, state.prince_id}
            and clan_state.faction_memberships.get(character.id) == ClanFactionSide.PRIMOGEN
            and effective_relation_to_primogen(state, character.id) <= 0
            and active_grievance_score(state, character.id, primogen_id) >= 2
        ]
        if not candidates:
            continue
        target = max(
            candidates,
            key=lambda character: (
                ideology_relation_modifier(leader, character),
                active_grievance_score(state, character.id, primogen_id),
                character.ambition,
                character.personal_influence,
                character.id,
            ),
        )
        if ideology_relation_modifier(leader, target) < 0:
            continue
        set_faction_side(state, target.id, ClanFactionSide.OPPOSITION)
        leader.relations[target.id] = min(2, leader.relations.get(target.id, 0) + 1)
        target.relations[leader.id] = min(2, target.relations.get(leader.id, 0) + 1)
        events.append(
            GameEvent(
                night=state.night,
                category="faction",
                message=(
                    f"{target.name}, fragilisé par ses griefs envers le Primogène, rejoint ouvertement "
                    f"la faction d'opposition menée par {leader.name}."
                ),
                audience_clan_ids=(clan_id,),
            )
        )
    return events


def _ambition_reactions(state: GameState) -> list[GameEvent]:
    events: list[GameEvent] = []
    for clan_id, clan_state in state.clan_states.items():
        leader_id = clan_state.opposition_leader_id
        if not leader_id:
            continue
        leader = state.characters[leader_id]
        if leader.political_ambition != PoliticalAmbition.LEAD_OPPOSITION:
            continue
        if effective_relation_to_primogen(state, leader.id) > 0:
            continue
        leader.personal_influence += 1
        events.append(
            GameEvent(
                night=state.night,
                category="faction",
                message=(
                    f"{leader.name} exploite les tensions internes et renforce discrètement son réseau "
                    "d'opposition : influence +1."
                ),
                audience_clan_ids=(clan_id,),
            )
        )
    return events


def resolve_autonomous_reactions(state: GameState) -> list[GameEvent]:
    """Réactions PNJ post-résolution, déterministes et motivées par l'état politique."""

    events: list[GameEvent] = []
    for promise in expire_broken_promises(state):
        beneficiary = state.characters[promise.beneficiary_id]
        promisor = state.characters[promise.promisor_id]
        clan_id = beneficiary.clan_id or promisor.clan_id
        events.append(
            GameEvent(
                night=state.night,
                category="promesse",
                message=(
                    f"La promesse de {promisor.name} envers {beneficiary.name} arrive à échéance sans être "
                    "tenue. Un grief sérieux apparaît et la réputation du promettant recule."
                ),
                audience_clan_ids=((clan_id,) if clan_id else None),
            )
        )
    events.extend(_resolve_called_boons(state))
    events.extend(_defection_reactions(state))
    events.extend(_ambition_reactions(state))
    return events
