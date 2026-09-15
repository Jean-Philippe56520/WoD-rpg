from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Iterable, Mapping

from .actions import apply_action
from .config import DEFAULT_RULES, GameRules
from .coteries import determine_coterie_stances, initialize_coteries
from .embrace import process_primogen_petition
from .models import Candidate, EmbracePetitionOrder, GameAction, GameEvent, GameState, PrimogenVote
from .offices import install_prince
from .politics import VoteResolution, resolve_praxis_vote


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
    legacy_counts = {clan_id: 0 for clan_id in state.clan_states}
    used_actors: set[str] = set()

    for action in actions:
        if action.clan_id not in state.clan_states:
            raise ValueError(f"Unknown clan: {action.clan_id}")

        if action.actor_character_id is None:
            legacy_counts[action.clan_id] += 1
            if legacy_counts[action.clan_id] > rules.actions_per_clan:
                raise ValueError(
                    f"{state.clan_states[action.clan_id].clan.name}: "
                    f"maximum {rules.actions_per_clan} legacy actions per night"
                )
            continue

        actor = state.characters.get(action.actor_character_id)
        if actor is None or actor.clan_id != action.clan_id:
            raise ValueError("Action actor must belong to the acting clan")
        if actor.id == state.prince_id:
            raise ValueError("The Prince cannot act as a clan member")
        if actor.id in used_actors:
            raise ValueError(f"{actor.name} cannot perform more than one action per night")
        used_actors.add(actor.id)

    return actions


def resolve_night(
    state: GameState,
    actions: Iterable[GameAction],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    embrace_petitions: Iterable[tuple[str, EmbracePetitionOrder]] = (),
    rules: GameRules = DEFAULT_RULES,
) -> NightResolution:
    next_state = deepcopy(state)
    initialize_coteries(next_state)
    actions = _validate_action_budget(next_state, actions, rules)
    candidates = list(candidates)
    candidate_map = {candidate.id: candidate for candidate in candidates}

    for action in actions:
        next_state.events.append(apply_action(next_state, action, rules))

    initialize_coteries(next_state)
    vote_result: VoteResolution | None = None
    if next_state.prince_id is None:
        stances = determine_coterie_stances(next_state)
        for clan_id, stance in stances.items():
            clan_state = next_state.clan_states[clan_id]
            leader = next_state.characters[clan_state.opposition_leader_id]
            if stance.supports_primogen:
                message = (
                    f"L'opposition de {clan_state.clan.name}, menée par {leader.name}, soutient "
                    f"le Primogène pour ce vote (score {stance.support_score:.0f})."
                )
            else:
                ally_name = next_state.characters[stance.allied_primogen_id].name
                message = (
                    f"L'opposition de {clan_state.clan.name}, menée par {leader.name}, refuse "
                    f"le Primogène et active son alliance avec {ally_name}."
                )
            next_state.events.append(
                GameEvent(
                    night=next_state.night,
                    category="coterie",
                    message=message,
                    audience_clan_ids=(clan_id,),
                )
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
                        "La Praxis reste contestée : aucun candidat ne rassemble une majorité "
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

    petitions = list(embrace_petitions)
    if len(petitions) > len(next_state.clan_states) * rules.embrace_petitions_per_clan:
        raise ValueError("Too many embrace petitions")
    if petitions:
        counts: dict[str, int] = {}
        for clan_id, petition in petitions:
            counts[clan_id] = counts.get(clan_id, 0) + 1
            if counts[clan_id] > rules.embrace_petitions_per_clan:
                raise ValueError(
                    f"{clan_id}: maximum {rules.embrace_petitions_per_clan} embrace petition per night"
                )
            next_state = process_primogen_petition(next_state, clan_id, petition, rules)

    initialize_coteries(next_state)
    next_state.night += 1
    return NightResolution(state=next_state, vote=vote_result)
