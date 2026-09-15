from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .chronicle import PlayerCharacter
from .era import EraRules
from .vampire_profile import VampireProfile


class SireBondStage(str, Enum):
    ACCOUNTING = "accounting"
    NEGOTIATING_RELEASE = "negotiating_release"
    RELEASED = "released"


@dataclass(frozen=True)
class SireBond:
    stage: SireBondStage
    authority_text: str
    protection_text: str
    can_seek_release: bool


def sire_bond(character: PlayerCharacter, profile: VampireProfile, era: EraRules) -> SireBond:
    if profile.released_from_sire:
        return SireBond(
            stage=SireBondStage.RELEASED,
            authority_text=(
                "Votre sire ne répond plus automatiquement de vos fautes. Votre indépendance est reconnue, "
                "mais votre lignée, vos dettes et vos ennemis continuent d'exister."
            ),
            protection_text="Vous ne pouvez plus présumer que les droits et refuges de votre sire vous appartiennent.",
            can_seek_release=False,
        )
    can_seek = character.status >= 1 or character.personal_influence >= 2.0 or character.goal_progress >= 3
    if can_seek:
        return SireBond(
            stage=SireBondStage.NEGOTIATING_RELEASE,
            authority_text=(
                "Vous êtes encore sous la responsabilité de votre sire, mais votre réputation suffit désormais "
                "pour que la question de votre autonomie puisse être négociée devant témoins."
            ),
            protection_text="La protection du sire reste active tant que la libération n'est pas formellement reconnue.",
            can_seek_release=True,
        )
    return SireBond(
        stage=SireBondStage.ACCOUNTING,
        authority_text=(
            "Votre sire répond encore de vous et peut légitimement exiger des services, fixer des limites de chasse "
            "et vous présenter — ou refuser de vous présenter — aux puissants locaux."
        ),
        protection_text=(
            "Cette dépendance vous protège aussi : une attaque ouverte contre vous engage la réputation de votre sire."
        ),
        can_seek_release=False,
    )
