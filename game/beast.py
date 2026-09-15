from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .dice import DiceResult, roll_pool
from .mecaniques_vampiriques import severite_fleau


class TypeFrenesie(str, Enum):
    FUREUR = "fureur"
    FAIM = "faim"
    TERREUR = "terreur"


@dataclass(frozen=True)
class ResultatFrenesie:
    type: TypeFrenesie
    difficulty: int
    pool: int
    dice: DiceResult | None
    resisted: bool
    rode_wave: bool = False


@dataclass(frozen=True)
class CompulsionDefinition:
    id: str
    clan_id: str
    nom: str
    description: str
    penalty: int = 2


CLAN_COMPULSIONS = {
    "brujah": CompulsionDefinition(
        id="brujah_rebellion",
        clan_id="brujah",
        nom="Rébellion",
        description=(
            "La Bête refuse l'ordre établi. Tant que vous ne prenez pas réellement position contre une autorité, "
            "les actions sans rapport avec cette opposition subissent une pénalité."
        ),
    ),
    "toreador": CompulsionDefinition(
        id="toreador_obsession",
        clan_id="toreador",
        nom="Obsession",
        description=(
            "La Bête fixe votre attention sur une personne, une œuvre ou un détail fascinant. Les actions sans rapport "
            "avec cette fixation subissent une pénalité jusqu'à ce que vous vous y consacriez ou que la scène se dissolve."
        ),
    ),
    "ventrue": CompulsionDefinition(
        id="ventrue_arrogance",
        clan_id="ventrue",
        nom="Arrogance",
        description=(
            "La Bête exige que votre autorité soit reconnue. Les actions qui ne servent pas à commander ou établir "
            "votre prééminence subissent une pénalité jusqu'à ce qu'un ordre soit accepté sans coercition surnaturelle."
        ),
    ),
}


def frenzy_pool(profile, humanity: int, clan_id: str, frenzy_type: TypeFrenesie | str) -> int:
    """Pool V5 simplifié : Volonté restante + un tiers d'Humanité, arrondi à l'inférieur.

    Le Fléau Brujah retranche sa Sévérité uniquement aux tests de Frénésie de Fureur.
    La Volonté de WoD-rpg est encore suivie comme un nombre de points restants et non
    comme une piste superficielle/aggravée complète ; ce pool utilise donc ce nombre.
    """

    frenzy_type = TypeFrenesie(frenzy_type)
    pool = max(0, int(profile.willpower)) + max(0, int(humanity)) // 3
    if clan_id == "brujah" and frenzy_type == TypeFrenesie.FUREUR:
        pool -= severite_fleau(profile.blood_potency)
    return max(1, pool)


def resoudre_frenesie(
    profile,
    *,
    humanity: int,
    clan_id: str,
    frenzy_type: TypeFrenesie | str,
    difficulty: int,
    seed: str,
    ride_wave: bool = False,
) -> ResultatFrenesie:
    if difficulty < 1:
        raise ValueError("La difficulté de Frénésie doit être positive")
    frenzy_type = TypeFrenesie(frenzy_type)
    pool = frenzy_pool(profile, humanity, clan_id, frenzy_type)
    if ride_wave:
        return ResultatFrenesie(
            type=frenzy_type,
            difficulty=difficulty,
            pool=pool,
            dice=None,
            resisted=False,
            rode_wave=True,
        )
    dice = roll_pool(pool=pool, hunger=0, difficulty=difficulty, seed=f"{seed}:frenzy")
    return ResultatFrenesie(
        type=frenzy_type,
        difficulty=difficulty,
        pool=pool,
        dice=dice,
        resisted=dice.success,
    )


def compulsion_definition(clan_id: str) -> CompulsionDefinition:
    try:
        return CLAN_COMPULSIONS[clan_id]
    except KeyError as exc:
        raise ValueError(f"Clan jouable sans Compulsion : {clan_id}") from exc


def active_compulsion(character, profile) -> CompulsionDefinition | None:
    """Une Compulsion produite par une Nuit significative expire avec cette Nuit."""

    if not profile.current_compulsion:
        return None
    scope = f"{character.chapter}:{character.segment}:{character.local_night}"
    if profile.compulsion_scope != scope:
        return None
    definition = CLAN_COMPULSIONS.get(character.clan_id)
    if definition is None or definition.id != profile.current_compulsion:
        return None
    return definition


def trigger_clan_compulsion(character, profile, *, focus: str) -> tuple[object, CompulsionDefinition]:
    definition = compulsion_definition(character.clan_id)
    scope = f"{character.chapter}:{character.segment}:{character.local_night}"
    return (
        replace(
            profile,
            current_compulsion=definition.id,
            compulsion_focus=" ".join(focus.strip().split())[:160],
            compulsion_scope=scope,
        ),
        definition,
    )


def clear_compulsion(profile):
    return replace(profile, current_compulsion=None, compulsion_focus="", compulsion_scope="")


def compulsion_aligned(
    clan_id: str,
    *,
    situation_tags: tuple[str, ...],
    choice_effect: str,
    choice_skill: str,
) -> bool:
    tags = set(situation_tags)
    if clan_id == "brujah":
        return bool(tags.intersection({"revolt", "debate", "authority", "protect_young"})) and choice_effect in {
            "sire_refuse",
            "political_voice",
        }
    if clan_id == "toreador":
        return bool(tags.intersection({"art", "patronage", "beauty"}))
    if clan_id == "ventrue":
        return (
            bool(tags.intersection({"authority", "administration", "oath"}))
            and choice_skill in {"leadership", "intimidation", "persuasion", "politics"}
        )
    return False


def compulsion_pool_modifier(character, profile, situation, choice) -> int:
    definition = active_compulsion(character, profile)
    if definition is None:
        return 0
    if compulsion_aligned(
        character.clan_id,
        situation_tags=situation.tags,
        choice_effect=choice.effect,
        choice_skill=choice.skill,
    ):
        return 0
    return -definition.penalty


def compulsion_satisfied(character, profile, situation, choice, *, success: bool) -> bool:
    if active_compulsion(character, profile) is None or not success:
        return False
    return compulsion_aligned(
        character.clan_id,
        situation_tags=situation.tags,
        choice_effect=choice.effect,
        choice_skill=choice.skill,
    )


def beast_result_can_trigger_compulsion(dice) -> bool:
    return bool(dice.bestial_failure or dice.messy_critical)
