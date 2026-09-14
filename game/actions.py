from __future__ import annotations

from .config import DEFAULT_RULES, GameRules
from .ideology import build_currents, character_affinity, initialize_current_politics, primogen_current_id
from .models import ActionType, GameAction, GameEvent, GameState


ACTION_LABELS = {
    ActionType.CONSOLIDATE: "Consolider le courant du Primogene",
    ActionType.RALLY_OPPOSITION: "Rallier un courant rival",
    ActionType.BUILD_INFLUENCE: "Mobiliser les reseaux du clan",
    ActionType.DIPLOMACY: "Diplomatie avec un autre clan",
}


def _clamp(value: float, minimum: float = 0.0, maximum: float = 100.0) -> float:
    return max(minimum, min(maximum, value))


def apply_action(
    state: GameState,
    action: GameAction,
    rules: GameRules = DEFAULT_RULES,
) -> GameEvent:
    if action.clan_id not in state.clan_states:
        raise ValueError(f"Unknown clan: {action.clan_id}")

    initialize_current_politics(state, rules)
    clan_state = state.clan_states[action.clan_id]
    clan = clan_state.clan
    primogen = state.characters[clan.primogen_id]
    primary_id = primogen_current_id(state, action.clan_id)
    currents = build_currents(state, action.clan_id)

    if action.action_type == ActionType.CONSOLIDATE:
        primogen.personal_influence += rules.consolidate_influence_gain
        for current_id in currents:
            if current_id == primary_id:
                continue
            clan_state.current_loyalties[current_id] = _clamp(
                clan_state.current_loyalties.get(current_id, rules.current_default_loyalty)
                - rules.consolidate_rival_loyalty_penalty
            )
        message = (
            f"{clan.name} consolide le courant du Primogene : influence personnelle de "
            f"{primogen.name} +{rules.consolidate_influence_gain:.0f}, avec davantage de tension interne."
        )

    elif action.action_type == ActionType.RALLY_OPPOSITION:
        target_id = action.target_current_id
        if not target_id or target_id == primary_id:
            raise ValueError("Rallying requires a rival current")
        if target_id not in currents:
            raise ValueError(f"Unknown target current: {target_id}")
        before = clan_state.current_loyalties.get(target_id, rules.current_default_loyalty)
        clan_state.current_loyalties[target_id] = _clamp(before + rules.rally_current_loyalty_gain)
        gained = clan_state.current_loyalties[target_id] - before
        message = (
            f"{clan.name} rallie le courant {currents[target_id].name} : "
            f"loyaute envers le Primogene +{gained:.0f}."
        )

    elif action.action_type == ActionType.BUILD_INFLUENCE:
        primogen.personal_influence += rules.influence_gain_primogen
        peers = [
            state.characters[member_id]
            for member_id in currents[primary_id].member_ids
            if member_id != primogen.id and member_id != state.prince_id
        ]
        peer_name = None
        if peers:
            peer = max(peers, key=lambda member: (member.personal_influence, member.id))
            peer.personal_influence += rules.influence_gain_peer
            peer_name = peer.name
        total_gain = rules.influence_gain_primogen + (rules.influence_gain_peer if peer_name else 0.0)
        message = f"{clan.name} mobilise ses reseaux : influence personnelle cumulee +{total_gain:.0f}."
        if peer_name:
            message += f" {peer_name} profite egalement de cette mobilisation."

    elif action.action_type == ActionType.DIPLOMACY:
        target_id = action.target_clan_id
        if not target_id or target_id == action.clan_id:
            raise ValueError("Diplomacy requires another target clan")
        if target_id not in state.clan_states:
            raise ValueError(f"Unknown target clan: {target_id}")
        target_state = state.clan_states[target_id]
        target_primogen = state.characters[target_state.clan.primogen_id]
        affinity = character_affinity(primogen, target_primogen)
        gain = max(
            rules.diplomacy_minimum_gain,
            rules.diplomacy_gain + affinity * rules.ideology_diplomacy_scale,
        )
        clan_state.relations[target_id] = clan_state.relations.get(target_id, 0.0) + gain
        target_state.relations[action.clan_id] = target_state.relations.get(action.clan_id, 0.0) + gain
        message = (
            f"{clan.name} ouvre des negociations avec {target_state.clan.name} : "
            f"relation +{gain:.1f} (affinite ideologique {affinity:+.0f})."
        )

    else:
        raise ValueError(f"Unsupported action type: {action.action_type}")

    return GameEvent(
        night=state.night,
        category="action",
        message=message,
        audience_clan_ids=(action.clan_id,),
    )
