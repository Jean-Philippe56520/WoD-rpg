from __future__ import annotations

from .config import DEFAULT_RULES, GameRules
from .models import ActionType, GameAction, GameEvent, GameState


ACTION_LABELS = {
    ActionType.CONSOLIDATE: "Consolider le courant du Primogène",
    ActionType.RALLY_OPPOSITION: "Rallier l'opposition",
    ActionType.BUILD_INFLUENCE: "Mobiliser les réseaux du clan",
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

    clan_state = state.clan_states[action.clan_id]
    clan = clan_state.clan

    if action.action_type == ActionType.CONSOLIDATE:
        shifted = min(rules.consolidate_shift, clan.opposition_current.influence)
        clan.opposition_current.influence -= shifted
        clan.dominant_current.influence += shifted
        clan_state.opposition_loyalty = _clamp(
            clan_state.opposition_loyalty - rules.consolidate_loyalty_penalty
        )
        message = (
            f"{clan.name} consolide le courant du Primogène : {shifted:.0f} influence "
            "bascule depuis l'opposition, qui apprécie peu la manœuvre."
        )

    elif action.action_type == ActionType.RALLY_OPPOSITION:
        before = clan_state.opposition_loyalty
        clan_state.opposition_loyalty = _clamp(before + rules.rally_loyalty_gain)
        gained = clan_state.opposition_loyalty - before
        message = (
            f"{clan.name} rallie son opposition : loyauté interne +{gained:.0f}."
        )

    elif action.action_type == ActionType.BUILD_INFLUENCE:
        clan.dominant_current.influence += rules.influence_gain_dominant
        clan.opposition_current.influence += rules.influence_gain_opposition
        message = (
            f"{clan.name} mobilise ses réseaux : influence du clan +"
            f"{rules.influence_gain_dominant + rules.influence_gain_opposition:.0f}."
        )

    elif action.action_type == ActionType.DIPLOMACY:
        target_id = action.target_clan_id
        if not target_id or target_id == action.clan_id:
            raise ValueError("Diplomacy requires another target clan")
        if target_id not in state.clan_states:
            raise ValueError(f"Unknown target clan: {target_id}")
        target_state = state.clan_states[target_id]
        clan_state.relations[target_id] = clan_state.relations.get(target_id, 0.0) + rules.diplomacy_gain
        target_state.relations[action.clan_id] = target_state.relations.get(action.clan_id, 0.0) + rules.diplomacy_gain
        message = (
            f"{clan.name} ouvre des négociations avec {target_state.clan.name} : "
            f"relation +{rules.diplomacy_gain:.0f}."
        )

    else:
        raise ValueError(f"Unsupported action type: {action.action_type}")

    return GameEvent(night=state.night, category="action", message=message)
