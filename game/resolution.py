from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Mapping

from .actions import apply_action
from .config import DEFAULT_RULES, GameRules
from .ideology import build_currents, initialize_current_politics
from .models import Candidate, GameAction, GameEvent, GameState, PrimogenVote
from .offices import install_prince
from .politics import VoteResolution, determine_current_stances, resolve_praxis_vote


@dataclass(frozen=True)
class NightResolution:
    state: GameState
    vote: VoteResolution | None


def _validate_action_budget(
    state: GameState,
    actions: Iterable[GameAction],
    rules: GameRules,
) -> list[GameAction]:
    actions = list(actions)
    counts = {clan_id: 0 for clan_id in state.clan_states}
    for action in actions:
        if action.clan_id not in counts:
            raise ValueError(f"Unknown clan: {action.clan_id}")
        counts[action.clan_id] += 1
        if counts[action.clan_id] > rules.actions_per_clan:
            raise ValueError(
                f"{state.clan_states[action.clan_id].clan.name}: "
                f"maximum {rules.actions_per_clan} actions per night"
            )
    return actions


def resolve_night(
    state: GameState,
    actions: Iterable[GameAction],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    rules: GameRules = DEFAULT_RULES,
) -> NightResolution:
    next_state = deepcopy(state)
    initialize_current_politics(next_state, rules)
    actions = _validate_action_budget(next_state, actions, rules)
    candidates = list(candidates)
    candidate_map = {candidate.id: candidate for candidate in candidates}

    for action in actions:
        next_state.events.append(apply_action(next_state, action, rules))

    initialize_current_politics(next_state, rules)
    vote_result: VoteResolution | None = None
    if next_state.prince_id is None:
        stances = determine_current_stances(next_state, rules)
        for current_id, stance in stances.items():
            current = build_currents(next_state, stance.clan_id)[current_id]
            if stance.supports_primogen:
                message = (
                    f"Le courant {current.name} ({next_state.clan_states[stance.clan_id].clan.name}) "
                    f"soutient son Primogene (score {stance.support_score:.0f})."
                )
            else:
                ally_name = next_state.characters[stance.allied_primogen_id].name
                message = (
                    f"Le courant {current.name} ({next_state.clan_states[stance.clan_id].clan.name}) "
                    f"refuse son Primogene et active son alliance avec {ally_name}."
                )
            next_state.events.append(
                GameEvent(night=next_state.night, category="current", message=message)
            )

        vote_result = resolve_praxis_vote(
            state=next_state,
            stances=stances,
            votes=votes,
            candidates=candidates,
            opposition_transfer_ratio=rules.opposition_transfer_ratio,
            recognition_threshold=rules.praxis_recognition_threshold,
        )

        if vote_result.disputed:
            next_state.praxis_status = "contested"
            next_state.camarilla_stability = max(
                0.0, next_state.camarilla_stability - rules.disputed_stability_loss
            )
            next_state.masquerade_integrity = max(
                0.0, next_state.masquerade_integrity - rules.disputed_masquerade_loss
            )
            next_state.events.append(
                GameEvent(
                    night=next_state.night,
                    category="praxis",
                    message=(
                        "La Praxis reste contestee : aucun candidat ne rassemble une majorite "
                        "politique suffisante. La Camarilla locale s'affaiblit."
                    ),
                )
            )
        else:
            winner = candidate_map[vote_result.winner_id]
            install_prince(next_state, winner, rules)
            next_state.camarilla_stability = min(
                100.0, next_state.camarilla_stability + rules.recognized_stability_gain
            )

    next_state.night += 1
    return NightResolution(state=next_state, vote=vote_result)
