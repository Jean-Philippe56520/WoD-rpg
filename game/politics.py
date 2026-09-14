from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .models import Candidate, Clan, OppositionStance, PrimogenVote


@dataclass(frozen=True)
class VoteResolution:
    primogen_weights: dict[str, float]
    candidate_totals: dict[str, float]
    opposition_transfers: list[dict[str, float | str]]
    winner_id: str | None
    disputed: bool


def _validate_unique_clans(clans: Iterable[Clan]) -> dict[str, Clan]:
    clan_map: dict[str, Clan] = {}
    for clan in clans:
        if clan.id in clan_map:
            raise ValueError(f"Duplicate clan id: {clan.id}")
        clan_map[clan.id] = clan
    return clan_map


def resolve_praxis_vote(
    clans: Iterable[Clan],
    stances: Mapping[str, OppositionStance],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    opposition_transfer_ratio: float = 0.5,
) -> VoteResolution:
    """Resolve a weighted Prince vote.

    Each Primogen initially carries the full influence of their clan. If the
    opposition refuses to support its Primogen, a configured share of the
    opposition current is removed from that Primogen's vote weight and added
    to the vote weight of the opposition leader's pre-selected allied Primogen.

    The transferred influence follows the allied Primogen's candidate choice;
    it is not cast directly for a candidate by the opposition.
    """
    if not 0 <= opposition_transfer_ratio <= 1:
        raise ValueError("opposition_transfer_ratio must be between 0 and 1")

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
    for primogen_id, weight in primogen_weights.items():
        vote = votes.get(primogen_id)
        if vote is None:
            continue
        if vote.candidate_id not in candidate_map:
            raise ValueError(f"Unknown candidate: {vote.candidate_id}")
        candidate_totals[vote.candidate_id] += weight

    if not candidate_totals:
        return VoteResolution(
            primogen_weights=primogen_weights,
            candidate_totals=candidate_totals,
            opposition_transfers=transfers,
            winner_id=None,
            disputed=True,
        )

    max_score = max(candidate_totals.values())
    winners = [cid for cid, score in candidate_totals.items() if score == max_score]
    winner_id = winners[0] if len(winners) == 1 and max_score > 0 else None

    return VoteResolution(
        primogen_weights=primogen_weights,
        candidate_totals=candidate_totals,
        opposition_transfers=transfers,
        winner_id=winner_id,
        disputed=winner_id is None,
    )
