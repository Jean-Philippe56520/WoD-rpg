"""Orchestration des actions de nuit, y compris les réponses aux crises V0.20."""

from __future__ import annotations

from copy import deepcopy

from .config import DEFAULT_RULES, GameRules
from .crises import CRISIS_ACTION_TYPES
from .crisis_actions import resolve_crisis_actions_simultaneously
from .models import GameAction, GameEvent, GameState
from .simultaneous import resolve_actions_simultaneously


def resolve_all_actions_simultaneously(
    state: GameState,
    actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
) -> list[GameEvent]:
    """Résout toutes les missions à partir du même état de début de phase."""

    if not actions:
        return []
    reference_state = deepcopy(state)
    ordinary = [action for action in actions if action.action_type not in CRISIS_ACTION_TYPES]
    crisis = [action for action in actions if action.action_type in CRISIS_ACTION_TYPES]

    events = resolve_actions_simultaneously(state, ordinary, rules)
    events.extend(
        resolve_crisis_actions_simultaneously(
            state,
            crisis,
            rules,
            reference_state=reference_state,
        )
    )
    return events
