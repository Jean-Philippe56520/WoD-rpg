from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .config import DEFAULT_RULES, GameRules
from .models import Candidate, Clan, GameState, OppositionStance, PrimogenVote


@dataclass(frozen=True)
class VoteResolution:
    primogen_weights: dict[str, float]
    candidate_totals: dict[str, float]
    opposition_transfers: list[dict[str, float | str]]
    total_cast_influence: float
    recognition_threshold: float
    winner_id: str | None
    disputed: bool


def _validate_unique_clans(clans: Iterable[Clan]) -> dict[str, Clan]:
    clan_map: dict[str, Clan] = {}
    for clan in clans:
        if clan.id in clan_map:
            raise ValueError(f"Duplicate clan id: {clan.id}")
        clan_map[clan.id] = clan
    return clan_map


def determine_opposition_stances(
    state: GameState,
    rules: GameRules = DEFAULT_RULES,
) -> dict[str, OppositionStance]:
    """Let each opposition decide whether it follows its Primogen.

    V0.2 deliberately keeps the decision model readable: the leader follows the
    Primogen when the opposition's loyalty reaches the configurable threshold.
    The allied Primogen is persistent state and is used only when dissent occurs.
    """
    stances: dict[str, OppositionStance] = {}
    for clan_id, clan_state in state.clan_states.items():
        supports = clan_state.opposition_loyalty >= rules.opposition_support_threshold
        stances[clan_id] = OppositionStance(
            clan_id=clan_id,
            supports_primogen=supports,
            allied_primogen_id=None if supports else clan_state.opposition_ally_id,
        )
    return stances


def resolve_praxis_vote(
    clans: Iterable[Clan],
    stances: Mapping[str, OppositionStance],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    opposition_transfer_ratio: float = 0.5,
    recognition_threshold: float = 0.5,
) -> VoteResolution:
    """Resolve the Primogens' weighted vote for recognition of a Praxis.

    If an opposition dissents, a configured share of its influence leaves its
    Primogen's voting weight and reinforces a pre-selected allied Primogen. The
    transferred influence follows that allied Primogen's candidate choice.

    A plurality is not enough: a candidate is recognised only when their score
    is strictly greater than the configured share of all influence actually cast.
    """
    if not 0 <= opposition_transfer_ratio <= 1:
        raise ValueError("opposition_transfer_ratio must be between 0 and 1")
    if not 0 <= recognition_threshold < 1:
        raise ValueError("recognition_threshold must be between 0 (inclusive) and 1")

    clan_map = _validate_unique_clans(clans)
    candidate_map = {candidate.id: candidate for candidate in candidates}
    primogen_to_clan = {clan.primogen_id: clan for clan in clan_map.values()}
    primogen_weights = {
        clan.primogen_id: clan.total_influence for clan in clan_map.values()
    }
    transfers: list[dict[str, float | str]] = []

    for clan_id, clan in clan_map.items():
        stance = stances.get(
            clan_id,
            OppositionStance(clan_id=clan_id, supports_primogen=True),
        )
        if stance.supports_primogen:
            continue

        ally_id = stance.allied_primogen_id
        if not ally_id:
            raise ValueError(f"{clan.name}: dissent requires an allied Primogen")
        if ally_id == clan.primogen_id:
            raise ValueError(f"{clan.name}: opposition ally cannot be its own Primogen")
        if ally_id not in primogen_to_clan:
            raise ValueError(f"Unknown allied Primogen: {ally_id}")

        transferred = clan.opposition_current.influence * opposition_transfer_ratio
        primogen_weights[clan.primogen_id] -= transferred
        primogen_weights[ally_id] += transferred
        transfers.append(
            {
                "from_clan_id": clan_id,
                "from_primogen_id": clan.primogen_id,
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
        opposition_transfers=transfers,
        total_cast_influence=total_cast,
        recognition_threshold=required_score,
        winner_id=winner_id,
        disputed=winner_id is None,
    )
