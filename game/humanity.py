from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib

from .chronicle import PlayerCharacter


@dataclass(frozen=True)
class PrincipeChronique:
    id: str
    label: str
    description: str


# Principes par défaut de la chronique solo. Ils sont volontairement définis
# comme des données afin de pouvoir être configurés sans réécrire le moteur.
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
    personnage: PlayerCharacter
    demandees: int
    mitigees: int
    ajoutees: int
    debordement: int


@dataclass(frozen=True)
class ResultatRemords:
    personnage: PlayerCharacter
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
    amount: int,
    *,
    conviction_protege: bool = False,
) -> ResultatFletrissures:
    """Ajoute des Flétrissures et applique la mitigation simplifiée d'une Conviction.

    Dans WoD-rpg, une Conviction explicitement pertinente peut réduire de 1 les
    Flétrissures d'un acte, sans jamais les annuler au-delà de ce montant.
    Le débordement est signalé au moteur appelant ; la Volonté reste volontairement
    séparée car son suivi est actuellement simplifié par rapport à la piste V5 complète.
    """

    if amount < 0:
        raise ValueError("Le nombre de Flétrissures ne peut pas être négatif")
    mitigees = 1 if conviction_protege and amount > 0 else 0
    effectives = max(0, amount - mitigees)
    capacity = capacite_fletrissures(character.humanity)
    disponible = max(0, capacity - character.humanity_stains)
    ajoutees = min(disponible, effectives)
    debordement = max(0, effectives - ajoutees)
    updated = replace(
        character,
        humanity_stains=min(capacity, character.humanity_stains + ajoutees),
    )
    return ResultatFletrissures(
        personnage=updated,
        demandees=amount,
        mitigees=mitigees,
        ajoutees=ajoutees,
        debordement=debordement,
    )


def pool_remords(character: PlayerCharacter) -> int:
    """Dés de Remords V5 : cases non marquées de la piste, minimum 1 dé."""

    capacity = capacite_fletrissures(character.humanity)
    return max(1, capacity - character.humanity_stains)


def _des_remords(pool: int, seed: str) -> tuple[int, ...]:
    values: list[int] = []
    for index in range(pool):
        digest = hashlib.sha256(f"{seed}:remords:{index}".encode("utf-8")).digest()
        values.append(digest[0] % 10 + 1)
    return tuple(values)


def resoudre_remords(character: PlayerCharacter, *, seed: str) -> ResultatRemords:
    """Résout le Remords en fin de Cycle si le vampire porte des Flétrissures."""

    if character.humanity_stains <= 0:
        return ResultatRemords(
            personnage=character,
            pool=0,
            des=(),
            succes=True,
            humanite_perdue=0,
            wassail=character.humanity <= 0,
        )

    pool = pool_remords(character)
    dice = _des_remords(pool, seed)
    success = any(value >= 6 for value in dice)
    humanity_loss = 0 if success else 1
    new_humanity = max(0, character.humanity - humanity_loss)
    updated = replace(character, humanity=new_humanity, humanity_stains=0)
    return ResultatRemords(
        personnage=updated,
        pool=pool,
        des=dice,
        succes=success,
        humanite_perdue=humanity_loss,
        wassail=new_humanity <= 0,
    )
