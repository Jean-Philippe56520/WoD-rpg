from __future__ import annotations

from .models import Character, CharacterAttribute


EXPERTISE_BONUS = 1


def attribute_value(character: Character, attribute: CharacterAttribute | str) -> int:
    attribute = CharacterAttribute(attribute)
    return {
        CharacterAttribute.PHYSICAL: character.physical,
        CharacterAttribute.SOCIAL: character.social,
        CharacterAttribute.MENTAL: character.mental,
    }[attribute]


def has_expertise(character: Character, expertise: str) -> bool:
    target = expertise.strip().casefold()
    return bool(target) and any(item.casefold() == target for item in character.expertises)


def action_score(
    character: Character,
    attribute: CharacterAttribute | str,
    *,
    expertise: str | None = None,
    discipline: str | None = None,
    background: str | None = None,
) -> int:
    """Calcule Caractéristique + Expertise (+1) + Discipline OU Historique.

    Discipline et Historique sont mutuellement exclusifs pour garder la résolution
    volontairement compacte. Une expertise non possédée n'ajoute aucun bonus.
    """
    if discipline is not None and background is not None:
        raise ValueError("An action may use a discipline or a background, not both")

    score = attribute_value(character, attribute)
    if expertise and has_expertise(character, expertise):
        score += EXPERTISE_BONUS

    if discipline is not None:
        if discipline not in character.disciplines:
            raise ValueError(f"Unknown discipline for character: {discipline}")
        score += character.disciplines[discipline]

    if background is not None:
        if background not in character.backgrounds:
            raise ValueError(f"Unknown background for character: {background}")
        score += character.backgrounds[background]

    return score
