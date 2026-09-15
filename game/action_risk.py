from __future__ import annotations

from dataclasses import dataclass

from .chronicle import PlayerCharacter
from .chronicle_simulation import SimulationState
from .dice import difficulty_band, difficulty_hint
from .relationship_memory import relationship_difficulty_adjustment
from .situations import Situation, SituationChoice


RELATIONAL_EFFECTS = frozenset(
    {
        "sire_service",
        "sire_negotiate",
        "sire_refuse",
        "seek_release",
        "political_voice",
        "protect_touchstone",
        "cautious_distance",
    }
)


@dataclass(frozen=True)
class ActionRiskPreview:
    """Player-facing estimate of a check without exposing its numeric target."""

    attribute: str
    skill: str
    band: str
    hint: str


def effective_difficulty(
    character: PlayerCharacter,
    simulation: SimulationState,
    situation: Situation,
    choice: SituationChoice,
) -> tuple[int, int]:
    """Mirror the resolver's contextual difficulty without exposing it to the UI.

    Character capability belongs to the dice pool. Circumstances such as an
    established relationship alter the target. The exact value remains engine
    state; player-facing code receives only a broad risk band and narrative clue.
    """

    relation_adjustment = (
        relationship_difficulty_adjustment(simulation, situation.source_actor_id, character)
        if choice.effect in RELATIONAL_EFFECTS
        else 0
    )
    return max(1, choice.difficulty + relation_adjustment), relation_adjustment


def action_risk_preview(
    character: PlayerCharacter,
    simulation: SimulationState,
    situation: Situation,
    choice: SituationChoice,
) -> ActionRiskPreview:
    difficulty, _ = effective_difficulty(character, simulation, situation, choice)
    return ActionRiskPreview(
        attribute=choice.attribute,
        skill=choice.skill,
        band=difficulty_band(difficulty),
        hint=difficulty_hint(difficulty),
    )
