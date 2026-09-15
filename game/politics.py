from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from .config import DEFAULT_RULES, GameRules
from .factions import determine_faction_stances, faction_influence, initialize_factions
from .models import Candidate, ClanFactionSide, FactionStance, GameState, PrimogenVote


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
) -> dict[str, FactionStance]:
    """Alias historique conservé ; le moteur actif raisonne désormais en factions."""
    return determine_faction_stances(state)


def primogen_political_weights(
    state: GameState,
    stances: Mapping[str, FactionStance],
    opposition_transfer_ratio: float = 0.5,
) -> tuple[dict[str, float], list[dict[str, float | str]]]:
    """Calcule le poids politique réellement contrôlé par chaque Primogène.

    Cette fonction matérialise la règle locale de la chronique : si l'opposition
    soutient son Primogène, son influence reste entièrement derrière lui. Sinon,
    une part configurable est transférée au Primogène allié choisi par l'opposition.
    Le même poids sert désormais à la reconnaissance comme à la contestation de
    Praxis, ce qui évite deux systèmes politiques divergents.
    """

    if not 0 <= opposition_transfer_ratio <= 1:
        raise ValueError("opposition_transfer_ratio must be between 0 and 1")

    initialize_factions(state)
    primogen_ids = {cs.clan.primogen_id for cs in state.clan_states.values()}
    primogen_weights = {primogen_id: 0.0 for primogen_id in primogen_ids}
    transfers: list[dict[str, float | str]] = []

    for clan_id, clan_state in state.clan_states.items():
        own_primogen_id = clan_state.clan.primogen_id
        primogen_influence = faction_influence(state, clan_id, ClanFactionSide.PRIMOGEN)
        opposition_influence = faction_influence(state, clan_id, ClanFactionSide.OPPOSITION)
        primogen_weights[own_primogen_id] += primogen_influence

        stance = stances.get(clan_id)
        if stance is None or stance.supports_primogen:
            primogen_weights[own_primogen_id] += opposition_influence
            continue

        ally_id = stance.allied_primogen_id
        if not ally_id:
            raise ValueError(f"Dissenting opposition has no allied Primogen: {clan_id}")
        if ally_id == own_primogen_id:
            raise ValueError("Opposition cannot ally with its own Primogen")
        if ally_id not in primogen_weights:
            raise ValueError(f"Unknown allied Primogen: {ally_id}")

        transferred = opposition_influence * opposition_transfer_ratio
        retained = opposition_influence - transferred
        primogen_weights[own_primogen_id] += retained
        primogen_weights[ally_id] += transferred
        transfers.append(
            {
                "from_clan_id": clan_id,
                "from_current_id": f"{clan_id}__opposition",
                "from_primogen_id": own_primogen_id,
                "to_primogen_id": ally_id,
                "amount": transferred,
            }
        )

    return primogen_weights, transfers


def resolve_praxis_vote(
    state: GameState,
    stances: Mapping[str, FactionStance],
    votes: Mapping[str, PrimogenVote],
    candidates: Iterable[Candidate],
    opposition_transfer_ratio: float = 0.5,
    recognition_threshold: float = 0.5,
) -> VoteResolution:
    if not 0 <= recognition_threshold < 1:
        raise ValueError("recognition_threshold must be between 0 (inclusive) and 1")

    candidate_map = {candidate.id: candidate for candidate in candidates}
    primogen_weights, transfers = primogen_political_weights(
        state,
        stances,
        opposition_transfer_ratio,
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
