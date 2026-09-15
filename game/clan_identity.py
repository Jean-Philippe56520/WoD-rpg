"""Identités claniques stratégiques propres à WoD-rpg.

Ces règles sont inspirées des thèmes V5 mais ne prétendent pas reproduire mot pour
mot les Banes ou Compulsions du jeu de rôle sur table. Elles traduisent les mêmes
fantasmes dans un moteur politique asynchrone : colère Brujah, obsession Toreador
et goût raffiné Ventrue.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import ActionType, Character, Domain, GameAction, GameState


@dataclass(frozen=True)
class ClanImpulse:
    name: str
    description: str


CLAN_IMPULSES: dict[str, ClanImpulse] = {
    "brujah": ClanImpulse(
        "Rébellion",
        "À forte Faim, les Brujah supportent moins bien les missions exigeant retenue, discipline et compromis.",
    ),
    "toreador": ClanImpulse(
        "Obsession",
        "À forte Faim, les Toreador se fixent plus facilement et perdent en efficacité sur les tâches diffuses ou administratives.",
    ),
    "ventrue": ClanImpulse(
        "Goût raffiné",
        "Un accès territorial ne suffit pas toujours : la chasse de routine exige un réseau mortel assez structuré pour sélectionner une proie convenable.",
    ),
}


def clan_impulse(clan_id: str | None) -> ClanImpulse | None:
    return CLAN_IMPULSES.get(clan_id or "")


def routine_feeding_allowed(character: Character, domain: Domain) -> bool:
    """Indique si un accès légal est réellement exploitable en chasse de routine.

    Pour les Ventrue, ``Servage >= 2`` représente l'existence d'un réseau mortel
    assez structuré pour satisfaire leur goût sélectif. C'est une abstraction
    stratégique WoD-rpg du thème V5 des préférences alimentaires Ventrue.
    """

    if character.clan_id == "ventrue":
        return domain.servage >= 2
    return True


def clan_action_penalty(character: Character, action: GameAction) -> tuple[int, str | None]:
    """Malus supplémentaire de clan à forte Faim, au-delà du malus général de Faim."""

    if character.hunger < 4:
        return 0, None

    if character.clan_id == "brujah" and action.action_type in {
        ActionType.DIPLOMACY,
        ActionType.CONSOLIDATE_RELATION,
    }:
        return 1, "Rébellion Brujah : la Faim rend la retenue et le compromis plus difficiles"

    if character.clan_id == "toreador" and action.action_type in {
        ActionType.BUILD_INFLUENCE,
        ActionType.DOMAIN_STEWARD,
    }:
        return 1, "Obsession Toreador : la Faim détourne l'attention des tâches diffuses"

    return 0, None


def apply_clan_action_penalty(
    state: GameState,
    action: GameAction,
) -> str | None:
    """Applique temporairement le malus au snapshot d'une mission.

    ``simultaneous.py`` ne fusionne pas les caractéristiques brutes après la mission :
    cette modification est donc strictement locale à la résolution de l'action.
    """

    actor_id = action.actor_character_id or state.clan_states[action.clan_id].clan.primogen_id
    actor = state.characters[actor_id]
    penalty, note = clan_action_penalty(actor, action)
    if penalty <= 0:
        return None
    actor.social = max(0, actor.social - penalty)
    actor.mental = max(0, actor.mental - penalty)
    return note


def brujah_rebellion_refusal(character: Character, action: GameAction) -> bool:
    """Pression de la Bête qui peut faire refuser un ordre non désiré à un Brujah."""

    return (
        character.clan_id == "brujah"
        and character.hunger >= 4
        and action.action_type in {ActionType.DIPLOMACY, ActionType.CONSOLIDATE_RELATION}
    )
