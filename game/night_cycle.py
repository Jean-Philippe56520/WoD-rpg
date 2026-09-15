from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Mapping, Sequence

from .chronicle import PlayerCharacter
from .dice import rouse_check
from .mecaniques_vampiriques import bonus_coup_de_sang, usage_discipline
from .praxis import apply_praxis_claim
from .relationship_memory import memory_for
from .situations import Situation, SituationResolution, generate_situations, resolve_situation
from .world_situations import world_event_situations

MAX_FREE_ACTIONS = 2


class NightPhase(str, Enum):
    EVENT = "event"
    FREE_ACTIONS = "free_actions"


@dataclass(frozen=True)
class OptionsResolution:
    depenser_volonte: bool = False
    coup_de_sang: bool = False
    utiliser_discipline: bool = False


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


def _preparer_leviers(
    character: PlayerCharacter,
    profile,
    situation: Situation,
    choice,
    *,
    options: OptionsResolution,
    step_nonce: str,
) -> tuple[PlayerCharacter, Any, bool, tuple[str, ...]]:
    bonus = 0
    notes: list[str] = []
    personnage_prepare = character

    if options.coup_de_sang:
        if character.hunger >= 5:
            raise ValueError("Le Coup de Sang est impossible lorsque la Faim est déjà à 5.")
        gain = bonus_coup_de_sang(profile.blood_potency)
        _, nouvelle_faim = rouse_check(
            hunger=character.hunger,
            seed=(
                f"{character.character_id}:{character.chapter}:{character.segment}:"
                f"{character.local_night}:{situation.id}:{choice.id}:{step_nonce}:exaltation"
            ),
        )
        personnage_prepare = replace(character, hunger=nouvelle_faim)
        bonus += gain
        if nouvelle_faim > character.hunger:
            notes.append(
                f"Coup de Sang : +{gain} dés ; le Test d’Exaltation augmente la Faim de 1."
            )
        else:
            notes.append(
                f"Coup de Sang : +{gain} dés ; le Test d’Exaltation n’augmente pas la Faim."
            )

    if options.utiliser_discipline:
        usage = usage_discipline(profile, situation, choice)
        if usage is None:
            raise ValueError("Aucun pouvoir de Discipline actuellement modélisé ne s’applique à cette action.")
        bonus += usage.bonus_des
        notes.append(
            f"{usage.discipline} — {usage.pouvoir} : +{usage.bonus_des} dé(s). {usage.description}"
        )

    autoriser_volonte = options.depenser_volonte
    if autoriser_volonte and profile.willpower <= 0:
        raise ValueError("Aucun point de Volonté n’est disponible pour cette relance.")

    profil_prepare = replace(profile, bonus_resolution=bonus)
    return personnage_prepare, profil_prepare, autoriser_volonte, tuple(notes)


def _finaliser_leviers(
    resolution: SituationResolution,
    profile_initial,
    notes: tuple[str, ...],
) -> SituationResolution:
    profil_final = replace(resolution.profile, bonus_resolution=0)
    details = list(notes)

    if resolution.dice.relances_volonte > 0:
        profil_final = replace(
            profil_final,
            willpower=max(0, profile_initial.willpower - 1),
        )
        details.append(
            f"Volonté : 1 point dépensé pour relancer {resolution.dice.relances_volonte} dé(s) ordinaire(s)."
        )

    detail_existant = resolution.outcome.detail.strip()
    detail_leviers = " ".join(details).strip()
    nouveau_detail = " ".join(
        part for part in (detail_leviers, detail_existant) if part
    )
    return replace(
        resolution,
        profile=profil_final,
        outcome=replace(resolution.outcome, detail=nouveau_detail),
    )


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
    options: OptionsResolution | None = None,
) -> SituationResolution:
    """Résout une étape de nuit de façon déterministe et sûre en cas de nouvel essai."""

    try:
        canonical_choice = next(item for item in situation.choices if item.id == choice_id)
    except StopIteration as exc:
        raise ValueError("Décision de situation inconnue") from exc

    options = options or OptionsResolution()
    personnage_prepare, profil_prepare, autoriser_volonte, notes = _preparer_leviers(
        character,
        profile,
        situation,
        canonical_choice,
        options=options,
        step_nonce=step_nonce,
    )

    marqueur_volonte = "@volonte" if autoriser_volonte else ""
    seeded_choice = replace(
        canonical_choice,
        id=f"{canonical_choice.id}@{step_nonce}{marqueur_volonte}",
    )
    seeded_situation = replace(
        situation,
        choices=tuple(
            seeded_choice if item.id == canonical_choice.id else item
            for item in situation.choices
        ),
    )
    resolution = resolve_situation(
        personnage_prepare,
        profil_prepare,
        simulation,
        seeded_situation,
        seeded_choice.id,
        nights_per_segment=nights_per_segment,
        free_intent=free_intent,
    )
    resolution = _finaliser_leviers(resolution, profile, notes)
    resolution = replace(resolution, situation=situation, choice=canonical_choice)
    if canonical_choice.effect == "praxis_claim":
        resolution = apply_praxis_claim(resolution, character)
    return resolution


def available_situations(
    character: PlayerCharacter,
    profile,
    simulation,
    *,
    year: int,
    world_events: Sequence[Mapping] = (),
    nights_per_cycle: int = 3,
) -> tuple[Situation, ...]:
    emergent = world_event_situations(
        character,
        simulation,
        world_events,
        nights_per_cycle=nights_per_cycle,
    )
    return emergent + generate_situations(character, profile, simulation, year=year)


def choose_night_event(
    character: PlayerCharacter,
    profile,
    simulation,
    *,
    year: int,
    world_events: Sequence[Mapping] = (),
    nights_per_cycle: int = 3,
) -> Situation:
    situations = available_situations(
        character,
        profile,
        simulation,
        year=year,
        world_events=world_events,
        nights_per_cycle=nights_per_cycle,
    )
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

    emergent = next((item for item in candidates if item.id.startswith("world_event_")), None)
    if emergent is not None:
        return emergent

    return candidates[(character.chapter + character.segment + character.local_night) % len(candidates)]


def free_action_situations(
    character: PlayerCharacter,
    profile,
    simulation,
    *,
    year: int,
    event_id: str,
    world_events: Sequence[Mapping] = (),
    nights_per_cycle: int = 3,
) -> tuple[Situation, ...]:
    return tuple(
        item
        for item in available_situations(
            character,
            profile,
            simulation,
            year=year,
            world_events=world_events,
            nights_per_cycle=nights_per_cycle,
        )
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
    options: OptionsResolution | None = None,
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
            options=options,
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
    options: OptionsResolution | None = None,
) -> NightStepResult:
    if remaining_actions <= 0:
        raise ValueError("Aucune action libre ne reste disponible cette nuit")
    if action_index < 1:
        raise ValueError("L’index d’action libre doit être positif")
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
            options=options,
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
        "relances_volonte": r.dice.relances_volonte,
        "remaining_actions_after": result.remaining_actions,
        "consequence": result.consequence,
    }
