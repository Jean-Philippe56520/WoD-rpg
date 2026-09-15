"""Autonomie des membres pourtant rattachés à la faction du Primogène.

L'opposition conserve ses règles historiques dans ``actions.py``. Ce module traite
le cas plus subtil d'un allié interne : appartenir à la faction du Primogène ne
signifie pas accepter n'importe quelle mission. Une faible relation, des griefs et
une mission contraire à l'ambition personnelle peuvent provoquer un refus.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_RULES, GameRules
from .factions import effective_relation_to_primogen
from .models import (
    ActionType,
    ClanFactionSide,
    GameAction,
    GameEvent,
    GameState,
    PoliticalAmbition,
)
from .social_politics import active_grievance_score


@dataclass(frozen=True)
class AgencyDecision:
    obeys: bool
    alignment: int
    effective_relation: int
    grievance_pressure: int
    reason: str


_POSITIVE_ACTIONS: dict[PoliticalAmbition, frozenset[ActionType]] = {
    PoliticalAmbition.INCREASE_INFLUENCE: frozenset({ActionType.BUILD_INFLUENCE}),
    PoliticalAmbition.OBTAIN_EMBRACE: frozenset({ActionType.BUILD_INFLUENCE, ActionType.DIPLOMACY}),
    PoliticalAmbition.GAIN_DOMAIN: frozenset(
        {ActionType.DOMAIN_STEWARD, ActionType.DOMAIN_INTRUSION, ActionType.BRACONNAGE}
    ),
    PoliticalAmbition.GAIN_BOON: frozenset({ActionType.CALL_BOON, ActionType.DIPLOMACY}),
    PoliticalAmbition.LEAD_OPPOSITION: frozenset(
        {ActionType.RECRUIT, ActionType.UNDERMINE, ActionType.POACH, ActionType.BUILD_INFLUENCE}
    ),
    PoliticalAmbition.WEAKEN_RIVAL: frozenset({ActionType.UNDERMINE, ActionType.POACH}),
    PoliticalAmbition.RAPPROCHEMENT: frozenset({ActionType.DIPLOMACY, ActionType.CONSOLIDATE_RELATION}),
    PoliticalAmbition.ENFORCE_ORDER: frozenset(
        {ActionType.INVESTIGATE, ActionType.DOMAIN_STEWARD, ActionType.CONSOLIDATE_RELATION}
    ),
    PoliticalAmbition.REFORM_CLAN: frozenset({ActionType.DIPLOMACY, ActionType.RECRUIT}),
    PoliticalAmbition.BECOME_PRIMOGEN: frozenset(
        {ActionType.BUILD_INFLUENCE, ActionType.RECRUIT, ActionType.UNDERMINE}
    ),
}

_NEGATIVE_ACTIONS: dict[PoliticalAmbition, frozenset[ActionType]] = {
    PoliticalAmbition.RAPPROCHEMENT: frozenset(
        {ActionType.UNDERMINE, ActionType.POACH, ActionType.DOMAIN_INTRUSION, ActionType.BRACONNAGE}
    ),
    PoliticalAmbition.ENFORCE_ORDER: frozenset({ActionType.POACH, ActionType.BRACONNAGE}),
    PoliticalAmbition.REFORM_CLAN: frozenset({ActionType.CONSOLIDATE_RELATION}),
    PoliticalAmbition.GAIN_DOMAIN: frozenset({ActionType.CONSOLIDATE_RELATION}),
    PoliticalAmbition.OBTAIN_EMBRACE: frozenset({ActionType.BRACONNAGE}),
}

_ALWAYS_SELF_SERVING = frozenset(
    {ActionType.BUILD_INFLUENCE, ActionType.CALL_BOON, ActionType.DOMAIN_STEWARD}
)


def mission_alignment(state: GameState, action: GameAction, actor_id: str) -> int:
    actor = state.characters[actor_id]
    ambition = actor.political_ambition
    if action.action_type in _POSITIVE_ACTIONS.get(ambition, frozenset()):
        return 1
    if action.action_type in _NEGATIVE_ACTIONS.get(ambition, frozenset()):
        return -1
    return 0


def evaluate_member_mission(state: GameState, action: GameAction) -> AgencyDecision | None:
    """Retourne une décision uniquement pour un allié interne non-Primogène.

    ``None`` signifie que ce module ne s'applique pas : Primogène, ordre legacy ou
    membre d'opposition (géré par les règles historiques). Les membres très proches
    du Primogène obéissent ; une mission directement utile à leur ambition est aussi
    acceptée. Le refus exige donc une vraie combinaison politique, pas un simple
    mauvais score relationnel.
    """

    if action.actor_character_id is None:
        return None
    actor = state.characters.get(action.actor_character_id)
    if actor is None or not actor.clan_id:
        return None
    clan_state = state.clan_states[actor.clan_id]
    if actor.id == clan_state.clan.primogen_id:
        return None
    side = clan_state.faction_memberships.get(actor.id, ClanFactionSide.PRIMOGEN)
    if side != ClanFactionSide.PRIMOGEN:
        return None

    relation = effective_relation_to_primogen(state, actor.id)
    grievances = active_grievance_score(state, actor.id, clan_state.clan.primogen_id)
    alignment = mission_alignment(state, action, actor.id)

    if action.action_type in _ALWAYS_SELF_SERVING:
        return AgencyDecision(True, alignment, relation, grievances, "mission personnelle")
    if relation >= 2:
        return AgencyDecision(True, alignment, relation, grievances, "forte relation au Primogène")
    if alignment > 0:
        return AgencyDecision(True, alignment, relation, grievances, "mission conforme à son ambition")

    refuses = False
    reason = "autorité suffisante"
    if relation <= 0 and alignment < 0:
        refuses = True
        reason = "ordre contraire à son ambition et autorité trop faible"
    elif relation <= 0 and grievances >= 1:
        refuses = True
        reason = "grief actif et relation rompue avec le Primogène"
    elif relation <= 1 and grievances >= 2 and alignment < 0:
        refuses = True
        reason = "grief sérieux et mission contraire à son ambition"
    elif relation <= 1 and actor.ambition >= 75 and alignment < 0:
        refuses = True
        reason = "ambition personnelle élevée et mission contraire à ses intérêts"

    return AgencyDecision(not refuses, alignment, relation, grievances, reason)


def apply_member_refusal(
    state: GameState,
    action: GameAction,
    decision: AgencyDecision,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    actor = state.characters[action.actor_character_id]
    actor.personal_influence += rules.influence_action_min_gain
    return GameEvent(
        night=state.night,
        category="autonomie",
        message=(
            f"{actor.name} refuse la mission du Primogène ({decision.reason}) et consacre la nuit "
            f"à son propre agenda « {actor.political_ambition.value} » : influence "
            f"+{rules.influence_action_min_gain:.0f}."
        ),
        audience_clan_ids=(action.clan_id,),
    )


def member_reliability(state: GameState, character_id: str) -> str:
    character = state.characters[character_id]
    if not character.clan_id:
        return "hors_clan"
    clan_state = state.clan_states[character.clan_id]
    if character_id == clan_state.clan.primogen_id:
        return "direct"
    relation = effective_relation_to_primogen(state, character_id)
    grievances = active_grievance_score(state, character_id, clan_state.clan.primogen_id)
    side = clan_state.faction_memberships.get(character_id, ClanFactionSide.PRIMOGEN)
    if side == ClanFactionSide.OPPOSITION:
        return "faible" if relation <= 0 else "conditionnelle"
    if relation >= 2 and grievances == 0:
        return "forte"
    if relation <= 0 or grievances >= 2:
        return "faible"
    return "conditionnelle"
