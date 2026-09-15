from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Iterable, TYPE_CHECKING

from .chronicle import PlayerCharacter, PoliticalOffice
from .chronicle_politics import actor_offices, assign_office, clear_explicit_offices
from .chronicle_simulation import SimulationBeat, SimulationState
from .era import era_for_year
from .paris_1435_context import active_historical_political_pressures
from .relationship_memory import record_relationship_memory

if TYPE_CHECKING:
    from .situations import SituationResolution


@dataclass(frozen=True)
class PraxisPressure:
    prince_id: str | None
    score: int
    level: str
    reasons: tuple[str, ...]
    credible_challenger_ids: tuple[str, ...]
    player_candidate_ids: tuple[str, ...]

    @property
    def is_contested(self) -> bool:
        return self.level in {"contested", "critical"}

    @property
    def is_critical(self) -> bool:
        return self.level == "critical"


def _level(score: int) -> str:
    if score >= 65:
        return "critical"
    if score >= 45:
        return "contested"
    if score >= 25:
        return "strained"
    return "stable"


def _relation_to(state: SimulationState, observer_id: str, subject_id: str) -> int:
    npc = state.npcs.get(observer_id)
    if npc is None:
        return 0
    return int(npc.relations.get(subject_id, 0))


def _candidate_ids(
    state: SimulationState,
    characters: Iterable[PlayerCharacter],
    *,
    prince_id: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    player_map = {character.character_id: character for character in characters if character.is_active}
    candidates: list[tuple[float, str]] = []
    player_ids: list[str] = []

    for npc in state.npcs.values():
        if not npc.alive or npc.id == prince_id:
            continue
        if PoliticalOffice.PRIMOGEN.value in actor_offices(state, npc.id):
            continue
        if npc.status >= 4 and npc.influence >= 7.0:
            candidates.append((npc.influence + npc.status, npc.id))

    for character in player_map.values():
        if character.character_id == prince_id:
            continue
        if PoliticalOffice.PRIMOGEN.value in actor_offices(state, character.character_id):
            continue
        if character.status >= 3 and character.personal_influence >= 6.0:
            candidates.append((character.personal_influence + character.status, character.character_id))
            player_ids.append(character.character_id)

    candidates.sort(key=lambda item: (-item[0], item[1]))
    return tuple(actor_id for _, actor_id in candidates), tuple(sorted(player_ids))


def assess_praxis_pressure(
    state: SimulationState,
    characters: Iterable[PlayerCharacter] = (),
) -> PraxisPressure:
    """Assess political pressure without inventing a second political state.

    The score is an internal decision aid built from persistent state plus the
    explicitly audited historical context active at the state's date. It is
    never rendered to the player as a raw number.
    """

    characters = tuple(characters)
    prince_id = state.offices.get(PoliticalOffice.PRINCE.value)
    if prince_id is None:
        challengers, player_candidates = _candidate_ids(state, characters, prince_id=None)
        return PraxisPressure(
            prince_id=None,
            score=100,
            level="critical",
            reasons=("La cité ne possède plus de Prince reconnu.",),
            credible_challenger_ids=challengers,
            player_candidate_ids=player_candidates,
        )

    reasons: list[str] = []
    pressure = 10

    prince_npc = state.npcs.get(prince_id)
    prince_character = next((item for item in characters if item.character_id == prince_id), None)
    if prince_npc is not None:
        if not prince_npc.alive:
            pressure += 80
            reasons.append("Le détenteur de la Praxis n'est plus actif.")
        else:
            pressure -= min(15, int(prince_npc.influence + prince_npc.status))
    elif prince_character is not None:
        pressure -= min(15, int(prince_character.personal_influence + prince_character.status))
    else:
        pressure += 35
        reasons.append("Le détenteur de la Praxis n'est plus un acteur politique résolu par la Chronique.")

    supporters = 0
    hostility = 0
    for npc in state.npcs.values():
        if not npc.alive or npc.id == prince_id:
            continue
        relation = _relation_to(state, npc.id, prince_id)
        if relation > 0:
            supporters += relation
        elif relation < 0:
            hostility += abs(relation)

    if hostility:
        pressure += hostility * 7
        reasons.append("Plusieurs acteurs influents entretiennent une hostilité durable envers la Praxis.")
    if supporters:
        pressure -= supporters * 3

    held_domains = [domain for domain in state.domains.values() if domain.holder_id == prince_id]
    if not held_domains:
        pressure += 10
        reasons.append("Le Prince ne contrôle directement aucun Domaine reconnu.")
    else:
        domain_pressure = sum(domain.pressure * 3 + domain.masquerade_risk * 6 for domain in held_domains)
        if domain_pressure:
            pressure += domain_pressure
            reasons.append("Les Domaines directement liés au Prince subissent une pression dangereuse.")

    debts_owed = sum(
        boon.status in {"due", "called"} and boon.debtor_id == prince_id
        for boon in state.boons.values()
    )
    debts_held = sum(
        boon.status in {"due", "called"} and boon.creditor_id == prince_id
        for boon in state.boons.values()
    )
    if debts_owed:
        pressure += debts_owed * 4
        reasons.append("Des Prestations dues par le Prince réduisent sa liberté politique.")
    pressure -= debts_held * 2

    historical_pressures = active_historical_political_pressures(
        state.year,
        target_office=PoliticalOffice.PRINCE.value,
    )
    if historical_pressures:
        pressure += sum(item.intensity * 8 for item in historical_pressures)
        reasons.extend(item.internal_reason for item in historical_pressures)

    score = max(0, min(100, pressure))
    challengers, player_candidates = _candidate_ids(state, characters, prince_id=prince_id)
    if score >= 45 and not challengers:
        reasons.append("La Praxis est fragilisée, mais aucun prétendant crédible ne s'impose encore.")

    return PraxisPressure(
        prince_id=prince_id,
        score=score,
        level=_level(score),
        reasons=tuple(dict.fromkeys(reasons)),
        credible_challenger_ids=challengers,
        player_candidate_ids=player_candidates,
    )


def praxis_pressure_beat(
    state: SimulationState,
    characters: Iterable[PlayerCharacter],
) -> SimulationBeat | None:
    assessment = assess_praxis_pressure(state, characters)
    if not assessment.is_contested:
        return None

    prince_id = assessment.prince_id or "paris_court"
    if assessment.prince_id in state.npcs:
        prince_name = state.npcs[assessment.prince_id].name
    else:
        prince_name = "la Praxis parisienne"

    if assessment.is_critical:
        public_text = (
            f"La question de la Praxis n'est plus seulement murmurée : l'autorité de {prince_name} "
            "est ouvertement discutée et plusieurs puissances cherchent à mesurer leurs soutiens."
        )
    else:
        public_text = (
            f"Des voix de plus en plus nombreuses mettent à l'épreuve l'autorité de {prince_name}. "
            "Personne n'ose encore parler comme si la succession était acquise."
        )

    hidden = " | ".join(assessment.reasons) or "Pression politique cumulée"
    if assessment.credible_challenger_ids:
        hidden += " | prétendants crédibles: " + ", ".join(assessment.credible_challenger_ids)

    return SimulationBeat(
        actor_id=prince_id,
        actor_name=prince_name,
        category="praxis_pressure",
        public_text=public_text,
        hidden_intent=hidden,
    )


def apply_praxis_claim(
    resolution: "SituationResolution",
    character: PlayerCharacter,
) -> "SituationResolution":
    """Resolve a claim only when the world has already produced a critical crisis.

    A normal success makes the claim politically meaningful but does not grant
    the office. Only a clean critical success during a critical crisis transfers
    the Praxis. This prevents a direct 'become Prince' action from bypassing the
    persistent political state.
    """

    assessment = assess_praxis_pressure(resolution.simulation, (character,))
    if character.character_id not in assessment.player_candidate_ids or not assessment.is_critical:
        raise ValueError("Character is not a credible Praxis claimant in the current world state")

    dice = resolution.dice
    updated_character = resolution.outcome.updated_character
    simulation = resolution.simulation
    details = [resolution.outcome.detail]
    tags = set(resolution.outcome.tags)
    tags.add("praxis_claim")

    if dice.critical and not dice.messy_critical:
        previous_prince = assessment.prince_id
        if previous_prince:
            simulation = clear_explicit_offices(simulation, actor_id=previous_prince)
        promoted = replace(
            updated_character,
            status=max(4, updated_character.status),
            personal_influence=updated_character.personal_influence + 2.0,
            reputation=min(3, updated_character.reputation + 1),
            goal_progress=updated_character.goal_progress + 3,
        )
        simulation = assign_office(
            simulation,
            (promoted,),
            actor_id=promoted.character_id,
            office=PoliticalOffice.PRINCE.value,
            era=era_for_year(promoted.chronicle_year),
        )
        details.append(
            "La crise était assez profonde et vos soutiens assez crédibles : votre revendication devient une Praxis reconnue."
        )
        tags.add("praxis_taken")
        if previous_prince and previous_prince in simulation.npcs:
            simulation = record_relationship_memory(
                simulation,
                promoted,
                previous_prince,
                year=promoted.chronicle_year,
                disposition_delta=-2,
                trust_delta=-1,
                respect_delta=1,
                fear_delta=1,
                awareness_delta=2,
                grievance=True,
            )
        outcome = replace(
            resolution.outcome,
            updated_character=promoted,
            detail=" ".join(item for item in details if item),
            tags=tuple(sorted(tags)),
        )
        return replace(resolution, outcome=outcome, simulation=simulation)

    if dice.success:
        promoted = replace(
            updated_character,
            personal_influence=updated_character.personal_influence + 1.0,
            reputation=min(3, updated_character.reputation + 1),
            goal_progress=updated_character.goal_progress + 2,
        )
        details.append(
            "Votre prétention devient publique et sérieuse, mais personne ne peut encore considérer la succession comme tranchée."
        )
        tags.add("praxis_claim_public")
    else:
        promoted = replace(
            updated_character,
            reputation=max(-3, updated_character.reputation - 1),
        )
        details.append("Votre revendication vous expose sans réunir encore assez de soutien pour déplacer la Praxis.")
        tags.add("praxis_claim_failed")

    previous_prince = assessment.prince_id
    if previous_prince and previous_prince in simulation.npcs:
        simulation = record_relationship_memory(
            simulation,
            promoted,
            previous_prince,
            year=promoted.chronicle_year,
            disposition_delta=-1,
            trust_delta=-1,
            respect_delta=1 if dice.success else -1,
            fear_delta=0,
            awareness_delta=2,
            grievance=True,
        )

    outcome = replace(
        resolution.outcome,
        updated_character=promoted,
        detail=" ".join(item for item in details if item),
        tags=tuple(sorted(tags)),
    )
    return replace(resolution, outcome=outcome, simulation=simulation)
