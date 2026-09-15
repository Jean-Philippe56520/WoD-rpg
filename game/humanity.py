from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

from .chronicle import PlayerCharacter
from .vampire_profile import VampireProfile


@dataclass(frozen=True)
class PrincipeChronique:
    id: str
    label: str
    description: str


# Principes par défaut de la chronique solo. Ils restent des données afin de
# pouvoir devenir configurables sans modifier le moteur de résolution.
PRINCIPES_CHRONIQUE: tuple[PrincipeChronique, ...] = (
    PrincipeChronique(
        "vie_sans_necessite",
        "Ne détruis pas une vie sans nécessité",
        "Prendre une vie pour la simple commodité du prédateur éloigne le vampire de ce qu'il fut.",
    ),
    PrincipeChronique(
        "bete_pas_alibi",
        "La Bête n'efface pas la responsabilité",
        "Céder volontairement à une atrocité reste un choix même lorsque la Faim ou la colère l'encourage.",
    ),
    PrincipeChronique(
        "proteger_dependants",
        "Ne trahis pas ceux qui dépendent de ta protection",
        "Exploiter puis abandonner sciemment un mortel ou un Caïnite placé sous sa protection laisse une trace morale.",
    ),
)


@dataclass(frozen=True)
class ResultatFletrissures:
    profile: VampireProfile
    demandees: int
    mitigees: int
    ajoutees: int
    debordement: int


@dataclass(frozen=True)
class ResultatRemords:
    personnage: PlayerCharacter
    profile: VampireProfile
    pool: int
    des: tuple[int, ...]
    succes: bool
    humanite_perdue: int
    wassail: bool


def capacite_fletrissures(humanity: int) -> int:
    if not 0 <= humanity <= 10:
        raise ValueError("L'Humanité doit être comprise entre 0 et 10")
    return 10 - humanity


def appliquer_fletrissures(
    character: PlayerCharacter,
    profile: VampireProfile,
    amount: int,
    *,
    conviction_protege: bool = False,
) -> ResultatFletrissures:
    """Ajoute des Flétrissures à la piste morale persistée dans le profil.

    Une Conviction explicitement pertinente peut réduire de 1 les Flétrissures
    reçues pour l'acte. Le débordement est signalé plutôt que transformé
    silencieusement en une autre ressource : la piste de Volonté de WoD-rpg est
    encore simplifiée et sera harmonisée ultérieurement.
    """

    if amount < 0:
        raise ValueError("Le nombre de Flétrissures ne peut pas être négatif")
    mitigees = 1 if conviction_protege and amount > 0 else 0
    effectives = max(0, amount - mitigees)
    capacity = capacite_fletrissures(character.humanity)
    disponible = max(0, capacity - profile.humanity_stains)
    ajoutees = min(disponible, effectives)
    debordement = max(0, effectives - ajoutees)
    updated = replace(
        profile,
        humanity_stains=min(capacity, profile.humanity_stains + ajoutees),
    )
    return ResultatFletrissures(
        profile=updated,
        demandees=amount,
        mitigees=mitigees,
        ajoutees=ajoutees,
        debordement=debordement,
    )


def pool_remords(character: PlayerCharacter, profile: VampireProfile) -> int:
    """Dés de Remords : cases non marquées de la piste, avec un minimum d'un dé."""

    capacity = capacite_fletrissures(character.humanity)
    return max(1, capacity - profile.humanity_stains)


def _des_remords(pool: int, seed: str) -> tuple[int, ...]:
    values: list[int] = []
    for index in range(pool):
        digest = hashlib.sha256(f"{seed}:remords:{index}".encode("utf-8")).digest()
        values.append(digest[0] % 10 + 1)
    return tuple(values)


def resoudre_remords(
    character: PlayerCharacter,
    profile: VampireProfile,
    *,
    seed: str,
) -> ResultatRemords:
    """Résout le Remords en fin de Cycle, adaptation de la fin de session V5."""

    if profile.humanity_stains <= 0:
        return ResultatRemords(
            personnage=character,
            profile=profile,
            pool=0,
            des=(),
            succes=True,
            humanite_perdue=0,
            wassail=character.humanity <= 0,
        )

    pool = pool_remords(character, profile)
    dice = _des_remords(pool, seed)
    success = any(value >= 6 for value in dice)
    humanity_loss = 0 if success else 1
    new_humanity = max(0, character.humanity - humanity_loss)
    updated_character = replace(character, humanity=new_humanity)
    updated_profile = replace(profile, humanity_stains=0)
    return ResultatRemords(
        personnage=updated_character,
        profile=updated_profile,
        pool=pool,
        des=dice,
        succes=success,
        humanite_perdue=humanity_loss,
        wassail=new_humanity <= 0,
    )
