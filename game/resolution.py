from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Mapping

from .actions import apply_action
from .config import DEFAULT_RULES, GameRules
from .models import Candidate, GameAction, GameEvent, GameState, PrimogenVote
from .offices import install_prince
from .politics import VoteResolution, determine_opposition_stances, resolve_praxis_vote


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
    actions = _validate_action_budget(next_state, actions, rules)
    candidates = list(candidates)
    candidate_map = {candidate.id: candidate for candidate in candidates}

    for action in actions:
        next_state.events.append(apply_action(next_state, action, rules))

    vote_result: VoteResolution | None = None
    if next_state.prince_id is None:
        stances = determine_opposition_stances(next_state, rules)
        for clan_id, stance in stances.items():
            clan_state = next_state.clan_states[clan_id]
            if stance.supports_primogen:
                message = (
                    f"L'opposition {clan_state.clan.name} soutient son Primogene "
                    f"(loyaute {clan_state.opposition_loyalty:.0f})."
                )
            else:
                message = (
                    f"L'opposition {clan_state.clan.name} refuse de suivre son Primogene et "
                    "active son alliance politique preexistante."
                )
            next_state.events.append(
                GameEvent(night=next_state.night, category="opposition", message=message)
            )

        vote_result = resolve_praxis_vote(
            clans=[cs.clan for cs in next_state.clan_states.values()],
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
