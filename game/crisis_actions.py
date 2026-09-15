"""Résolution simultanée des actions consacrées aux crises.

Les actions de crise utilisent le même état de référence que les autres missions :
un joueur ne bénéficie pas d'un effet obtenu plus tôt dans la liste d'ordres. Ce
module est séparé de ``actions.py`` pour conserver le moteur historique stable.
"""

from __future__ import annotations

from collections import defaultdict
from copy import deepcopy

from .agency import apply_member_refusal, evaluate_member_mission
from .config import DEFAULT_RULES, GameRules
from .crises import (
    CRISIS_ACTION_TYPES,
    crisis_member_accepts,
    crisis_refusal_event,
    crisis_response_event,
)
from .models import GameAction, GameEvent, GameState
from .social_politics import add_grievance


def _action_key(action: GameAction) -> tuple[str, str, str, str]:
    return (
        action.clan_id,
        action.actor_character_id or "",
        action.action_type.value,
        action.target_domain_id or "",
    )


def resolve_crisis_actions_simultaneously(
    state: GameState,
    actions: list[GameAction],
    rules: GameRules = DEFAULT_RULES,
    *,
    reference_state: GameState | None = None,
) -> list[GameEvent]:
    """Évalue les réponses de crise sur un snapshot commun et cumule leurs effets."""

    crisis_actions = [action for action in actions if action.action_type in CRISIS_ACTION_TYPES]
    if not crisis_actions:
        return []

    baseline = deepcopy(reference_state or state)
    influence_delta: dict[str, float] = defaultdict(float)
    stability_delta = 0.0
    masquerade_delta = 0.0
    new_grievances: list[object] = []
    events: list[GameEvent] = []

    for action in sorted(crisis_actions, key=_action_key):
        trial = deepcopy(baseline)
        agency = evaluate_member_mission(trial, action)
        if agency is not None and not agency.obeys:
            event = apply_member_refusal(trial, action, agency, rules)
        elif action.actor_character_id is not None and not crisis_member_accepts(trial, action):
            event = crisis_refusal_event(trial, action, rules)
        else:
            event = crisis_response_event(trial, action, rules)
        events.append(event)

        for character_id, before in baseline.characters.items():
            after = trial.characters[character_id]
            influence_delta[character_id] += after.personal_influence - before.personal_influence
        stability_delta += trial.camarilla_stability - baseline.camarilla_stability
        masquerade_delta += trial.masquerade_integrity - baseline.masquerade_integrity
        for grievance_id in set(trial.grievances) - set(baseline.grievances):
            new_grievances.append(deepcopy(trial.grievances[grievance_id]))

    for character_id, delta in influence_delta.items():
        state.characters[character_id].personal_influence = max(
            0.0,
            state.characters[character_id].personal_influence + delta,
        )
    state.camarilla_stability = max(
        0.0,
        min(100.0, state.camarilla_stability + stability_delta),
    )
    state.masquerade_integrity = max(
        0.0,
        min(100.0, state.masquerade_integrity + masquerade_delta),
    )

    for grievance in new_grievances:
        add_grievance(
            state,
            owner_id=grievance.owner_id,
            target_id=grievance.target_id,
            reason=grievance.reason,
            severity=grievance.severity,
        )

    return events
