from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .config import DEFAULT_RULES, GameRules
from .ideology import build_currents, ideological_affinity_axes, initialize_current_politics, primogen_current_id
from .models import Candidate, CurrentStance, GameState, PrimogenVote


@dataclass(frozen=True)
class VoteResolution:
    primogen_weights: dict[str, float]
    candidate_totals: dict[str, float]
    current_transfers: list[dict[str, float | str]]
    total_cast_influence: float
    recognition_threshold: float
    winner_id: str | None
    disputed: bool


def determine_current_stances(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> dict[str, CurrentStance]:
    initialize_current_politics(state, rules)
    stances: dict[str, CurrentStance] = {}
    current_primogens = {cs.clan.primogen_id for cs in state.clan_states.values()}

    for clan_id, clan_state in state.clan_states.items():
        primogen = state.characters[clan_state.clan.primogen_id]
        primary_id = primogen_current_id(state, clan_id)
        for current_id, current in build_currents(state, clan_id).items():
            if current_id == primary_id:
                stances[current_id] = CurrentStance(
                    clan_id=clan_id,
                    current_id=current_id,
                    supports_primogen=True,
                    support_score=100.0,
                )
                continue

            loyalty = clan_state.current_loyalties.get(current_id, rules.current_default_loyalty)
            affinity = ideological_affinity_axes(
                current.humanity_axis,
                current.tradition_axis,
                primogen.humanity_axis,
                primogen.tradition_axis,
            )
            support_score = max(0.0, min(100.0, loyalty + affinity * rules.ideology_support_scale))
            supports = support_score >= rules.current_support_threshold
            ally_id = None if supports else clan_state.current_allies.get(current_id)
            if ally_id is not None:
                if ally_id == clan_state.clan.primogen_id:
                    raise ValueError("A rival current cannot ally with its own Primogen")
                if ally_id not in current_primogens:
                    raise ValueError(f"Current ally is not a current Primogen: {ally_id}")
            if not supports and not ally_id:
                raise ValueError(f"Dissenting current has no allied Primogen: {current_id}")

            stances[current_id] = CurrentStance(
                clan_id=clan_id,
                current_id=current_id,
                supports_primogen=supports,
                support_score=support_score,
                allied_primogen_id=ally_id,
            )
    return stances


def resolve_praxis_vote(
    state: GameState,
    stances: Mapping[str, CurrentStance],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    opposition_transfer_ratio: float = 0.5,
    recognition_threshold: float = 0.5,
) -> VoteResolution:
    if not 0 <= opposition_transfer_ratio <= 1:
        raise ValueError("opposition_transfer_ratio must be between 0 and 1")
    if not 0 <= recognition_threshold < 1:
        raise ValueError("recognition_threshold must be between 0 (inclusive) and 1")

    candidate_map = {candidate.id: candidate for candidate in candidates}
    primogen_ids = {cs.clan.primogen_id for cs in state.clan_states.values()}
    primogen_weights = {primogen_id: 0.0 for primogen_id in primogen_ids}
    transfers: list[dict[str, float | str]] = []

    for clan_id, clan_state in state.clan_states.items():
        own_primogen_id = clan_state.clan.primogen_id
        primary_id = primogen_current_id(state, clan_id)
        for current_id, current in build_currents(state, clan_id).items():
            stance = stances.get(current_id)
            supports = current_id == primary_id or stance is None or stance.supports_primogen
            if supports:
                primogen_weights[own_primogen_id] += current.influence
                continue

            ally_id = stance.allied_primogen_id
            if not ally_id:
                raise ValueError(f"Dissenting current has no allied Primogen: {current_id}")
            if ally_id == own_primogen_id:
                raise ValueError("A rival current cannot ally with its own Primogen")
            if ally_id not in primogen_weights:
                raise ValueError(f"Unknown allied Primogen: {ally_id}")

            transferred = current.influence * opposition_transfer_ratio
            retained = current.influence - transferred
            primogen_weights[own_primogen_id] += retained
            primogen_weights[ally_id] += transferred
            transfers.append(
                {
                    "from_clan_id": clan_id,
                    "from_current_id": current_id,
                    "from_primogen_id": own_primogen_id,
                    "to_primogen_id": ally_id,
                    "amount": transferred,
                }
            )

    candidate_totals = {candidate_id: 0.0 for candidate_id in candidate_map}
    total_cast = 0.0
    for primogen_id, weight in primogen_weights.items():
        vote = votes.get(primogen_id)
        if vote is None:
            continue
        if vote.candidate_id not in candidate_map:
            raise ValueError(f"Unknown candidate: {vote.candidate_id}")
        candidate_totals[vote.candidate_id] += weight
        total_cast += weight

    required_score = total_cast * recognition_threshold
    winner_id: str | None = None
    if total_cast > 0 and candidate_totals:
        max_score = max(candidate_totals.values())
        leaders = [cid for cid, score in candidate_totals.items() if score == max_score]
        if len(leaders) == 1 and max_score > required_score:
            winner_id = leaders[0]

    return VoteResolution(
        primogen_weights=primogen_weights,
        candidate_totals=candidate_totals,
        current_transfers=transfers,
        total_cast_influence=total_cast,
        recognition_threshold=required_score,
        winner_id=winner_id,
        disputed=winner_id is None,
    )
