from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any

from .chronicle import PlayerCharacter
from .relationship_memory import memory_for
from .situations import Situation, SituationResolution, generate_situations, resolve_situation

MAX_FREE_ACTIONS = 2


class NightPhase(str, Enum):
    EVENT = "event"
    FREE_ACTIONS = "free_actions"


@dataclass(frozen=True)
class NightTurnState:
    game_id: str
    player_id: str
    character_id: str
    chapter: int
    segment: int
    night_number: int
    phase: NightPhase
    event_id: str
    remaining_actions: int = 0
    max_actions: int = MAX_FREE_ACTIONS
    log: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class NightStepResult:
    resolution: SituationResolution
    remaining_actions: int
    consequence: str
    action_cost: int = 0


def _same_night(character: PlayerCharacter, resolution: SituationResolution) -> SituationResolution:
    after = replace(
        resolution.outcome.updated_character,
        local_night=character.local_night,
        ready_for_convergence=False,
    )
    return replace(resolution, outcome=replace(resolution.outcome, updated_character=after))


def _resolve_with_step_nonce(
    character: PlayerCharacter,
    profile,
    simulation,
    situation: Situation,
    choice_id: str,
    *,
    nights_per_segment: int,
    free_intent: str,
    step_nonce: str,
) -> SituationResolution:
    """Keep deterministic rolls while avoiding identical rolls for repeated actions.

    ``resolve_situation`` seeds dice from situation/choice/night identifiers. Inside
    V0.45 a player may perform the same action twice during one night, so a stable
    step nonce is injected into the selected choice id for the roll only. The
    public resolution is restored to the canonical situation and choice ids.
    """

    try:
        canonical_choice = next(item for item in situation.choices if item.id == choice_id)
    except StopIteration as exc:
        raise ValueError("Unknown situation choice") from exc

    seeded_choice = replace(canonical_choice, id=f"{canonical_choice.id}@{step_nonce}")
    seeded_situation = replace(
        situation,
        choices=tuple(
            seeded_choice if item.id == canonical_choice.id else item
            for item in situation.choices
        ),
    )
    resolution = resolve_situation(
        character,
        profile,
        simulation,
        seeded_situation,
        seeded_choice.id,
        nights_per_segment=nights_per_segment,
        free_intent=free_intent,
    )
    return replace(resolution, situation=situation, choice=canonical_choice)


def choose_night_event(character: PlayerCharacter, profile, simulation, *, year: int) -> Situation:
    situations = generate_situations(character, profile, simulation, year=year)
    candidates = tuple(item for item in situations if not item.id.startswith("hunt_"))
    if not candidates:
        return situations[0]
    release = next((item for item in candidates if item.id == "sire_release"), None)
    if release is not None:
        return release

    sire_event = next((item for item in candidates if item.id == "sire_accounting"), None)
    sire_memory = memory_for(simulation, character.sire_id, character)
    if sire_event is not None and sire_memory is not None:
        intensity = (
            abs(sire_memory.disposition)
            + abs(sire_memory.trust)
            + abs(sire_memory.respect)
            + sire_memory.grievance_count
        )
        if intensity >= 4:
            return sire_event

    return candidates[(character.chapter + character.segment + character.local_night) % len(candidates)]


def free_action_situations(
    character: PlayerCharacter,
    profile,
    simulation,
    *,
    year: int,
    event_id: str,
) -> tuple[Situation, ...]:
    return tuple(
        item
        for item in generate_situations(character, profile, simulation, year=year)
        if item.id != event_id
    )


def _event_budget(character: PlayerCharacter, resolution: SituationResolution) -> tuple[int, str]:
    dice = resolution.dice
    effect = resolution.choice.effect
    if effect == "sire_refuse" and not dice.success:
        memory = memory_for(resolution.simulation, resolution.situation.source_actor_id, character)
        severe = resolution.outcome.updated_character.sire_relation <= 1 or (
            memory is not None and memory.grievance_count >= 2
        )
        if severe or dice.bestial_failure:
            return 0, "Votre sire transforme le conflit en sanction et vous retient jusqu'à l'approche de l'aube."
        return 0, "Le conflit avec votre sire consume le reste de la nuit."
    if dice.bestial_failure:
        return 0, "La complication provoquée par la Bête consume le reste de la nuit."
    if dice.critical and not dice.messy_critical:
        return 2, "Vous réglez l'événement assez vite pour conserver presque toute votre nuit."
    if dice.success and effect in {"political_intel", "cautious_distance"}:
        return 2, "L'affaire est réglée rapidement ; la nuit est encore jeune."
    if dice.success:
        return 1, "L'événement a pris du temps, mais une occasion importante reste possible."
    if effect in {"political_intel", "cautious_distance"}:
        return 1, "Vous perdez du temps, mais la nuit n'est pas terminée."
    return 0, "L'échec et ses conséquences consument le temps restant avant l'aube."


def resolve_night_event(
    character: PlayerCharacter,
    profile,
    simulation,
    situation: Situation,
    choice_id: str,
    *,
    nights_per_segment: int,
    free_intent: str = "",
) -> NightStepResult:
    resolution = _same_night(
        character,
        _resolve_with_step_nonce(
            character,
            profile,
            simulation,
            situation,
            choice_id,
            nights_per_segment=nights_per_segment,
            free_intent=free_intent,
            step_nonce="event",
        ),
    )
    remaining, consequence = _event_budget(character, resolution)
    return NightStepResult(resolution, remaining, consequence)


def resolve_free_action(
    character: PlayerCharacter,
    profile,
    simulation,
    situation: Situation,
    choice_id: str,
    *,
    nights_per_segment: int,
    remaining_actions: int,
    action_index: int = 1,
    free_intent: str = "",
) -> NightStepResult:
    if remaining_actions <= 0:
        raise ValueError("No free action remains this night")
    if action_index < 1:
        raise ValueError("Free action index must be positive")
    resolution = _same_night(
        character,
        _resolve_with_step_nonce(
            character,
            profile,
            simulation,
            situation,
            choice_id,
            nights_per_segment=nights_per_segment,
            free_intent=free_intent,
            step_nonce=f"free:{action_index}",
        ),
    )
    cost = remaining_actions if situation.id.startswith("hunt_") and choice_id == "careful_hunt" else 1
    left = max(0, remaining_actions - cost)
    if resolution.dice.bestial_failure:
        left = 0
        consequence = "La Bête transforme l'échec en complication : le reste de la nuit est perdu."
    elif cost >= remaining_actions:
        consequence = "Cette entreprise occupe tout le temps restant avant l'aube."
    elif left == 1:
        consequence = "Il reste le temps d'entreprendre encore une chose importante."
    else:
        consequence = "L'aube approche ; aucune nouvelle entreprise importante n'est possible."
    return NightStepResult(resolution, left, consequence, cost)


def time_remaining_text(remaining_actions: int) -> str:
    if remaining_actions >= 2:
        return "La nuit est encore jeune : deux actions importantes restent possibles."
    if remaining_actions == 1:
        return "Une grande partie de la nuit est passée : une action importante reste possible."
    return "L'aube approche : aucune action importante supplémentaire n'est possible."


def log_entry(kind: str, result: NightStepResult) -> dict[str, Any]:
    r = result.resolution
    return {
        "kind": kind,
        "situation_id": r.situation.id,
        "title": r.situation.title,
        "choice_id": r.choice.id,
        "choice_label": r.choice.label,
        "legacy_action": r.outcome.action.value,
        "summary": r.outcome.summary,
        "detail": r.outcome.detail,
        "successes": r.dice.successes,
        "difficulty": r.dice.difficulty,
        "remaining_actions_after": result.remaining_actions,
        "consequence": result.consequence,
    }
