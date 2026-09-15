from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .dice import rouse_check
from .vampire_profile import VampireProfile


class TypeDegat(str, Enum):
    SUPERFICIEL = "superficiel"
    AGGRAVE = "aggravé"


MENDING_SUPERFICIAL = {
    0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3,
    6: 3, 7: 3, 8: 4, 9: 4, 10: 5,
}


@dataclass(frozen=True)
class ResultatDegats:
    profile: VampireProfile
    type_degat: TypeDegat
    degats_bruts: int
    degats_appliques: int
    superficiels_ajoutes: int
    aggraves_ajoutes: int
    superficiels_convertis: int
    diminue: bool
    torpeur: bool


@dataclass(frozen=True)
class ResultatGuerison:
    profile: VampireProfile
    faim: int
    des_exaltation: tuple[int, ...]
    superficiels_soignes: int = 0
    aggraves_soignes: int = 0
    complete: bool = True


def _points_appliques(amount: int, damage_type: TypeDegat, *, vampire: bool) -> int:
    if amount < 0:
        raise ValueError("Les dégâts ne peuvent pas être négatifs")
    if amount == 0:
        return 0
    if vampire and damage_type == TypeDegat.SUPERFICIEL:
        return (amount + 1) // 2
    return amount


def appliquer_degats_sante(
    profile: VampireProfile,
    amount: int,
    damage_type: TypeDegat | str,
    *,
    vampire: bool = True,
) -> ResultatDegats:
    """Applique les dégâts V5 et convertit les marques lorsque la piste est pleine."""

    damage_type = TypeDegat(damage_type)
    points = _points_appliques(amount, damage_type, vampire=vampire)
    superficiels = profile.health_superficial
    aggraves = profile.health_aggravated
    maximum = profile.sante_maximale
    superficiels_ajoutes = 0
    aggraves_ajoutes = 0
    convertis = 0

    for _ in range(points):
        occupes = superficiels + aggraves
        if occupes < maximum:
            if damage_type == TypeDegat.SUPERFICIEL:
                superficiels += 1
                superficiels_ajoutes += 1
            else:
                aggraves += 1
                aggraves_ajoutes += 1
            continue
        if superficiels > 0:
            superficiels -= 1
            aggraves += 1
            convertis += 1
            continue
        break

    updated = replace(profile, health_superficial=superficiels, health_aggravated=aggraves)
    return ResultatDegats(
        profile=updated,
        type_degat=damage_type,
        degats_bruts=amount,
        degats_appliques=points,
        superficiels_ajoutes=superficiels_ajoutes,
        aggraves_ajoutes=aggraves_ajoutes,
        superficiels_convertis=convertis,
        diminue=updated.est_diminue,
        torpeur=updated.en_torpeur_par_degats,
    )


def montant_guerison_superficielle(blood_potency: int) -> int:
    try:
        return MENDING_SUPERFICIAL[blood_potency]
    except KeyError as exc:
        raise ValueError("Puissance du Sang hors plage prise en charge") from exc


def soigner_superficiels(
    profile: VampireProfile,
    *,
    hunger: int,
    seed: str,
) -> ResultatGuerison:
    """Un Test d'Exaltation soigne le montant corrigé par la Puissance du Sang."""

    if profile.health_superficial <= 0:
        return ResultatGuerison(profile=profile, faim=hunger, des_exaltation=())
    if hunger >= 5:
        raise ValueError("À Faim 5, le vampire ne peut plus volontairement Exalter le Sang pour guérir.")

    die, next_hunger = rouse_check(hunger=hunger, seed=f"{seed}:mend-superficial")
    healed = min(profile.health_superficial, montant_guerison_superficielle(profile.blood_potency))
    updated = replace(profile, health_superficial=profile.health_superficial - healed)
    return ResultatGuerison(
        profile=updated,
        faim=next_hunger,
        des_exaltation=(die,),
        superficiels_soignes=healed,
    )


def soigner_aggrave(
    profile: VampireProfile,
    *,
    hunger: int,
    seed: str,
) -> ResultatGuerison:
    """Trois Tests d'Exaltation permettent de guérir un dégât aggravé.

    Si la Faim atteint 5 avant que les trois Tests volontaires puissent être
    effectués, l'effort s'interrompt : la Faim gagnée reste acquise mais aucun
    dégât aggravé n'est retiré.
    """

    if profile.health_aggravated <= 0:
        return ResultatGuerison(profile=profile, faim=hunger, des_exaltation=())
    if hunger >= 5:
        raise ValueError("À Faim 5, le vampire ne peut plus volontairement Exalter le Sang pour guérir.")

    current_hunger = hunger
    dice: list[int] = []
    for index in range(3):
        if current_hunger >= 5:
            return ResultatGuerison(
                profile=profile,
                faim=current_hunger,
                des_exaltation=tuple(dice),
                complete=False,
            )
        die, current_hunger = rouse_check(
            hunger=current_hunger,
            seed=f"{seed}:mend-aggravated:{index}",
        )
        dice.append(die)

    updated = replace(profile, health_aggravated=profile.health_aggravated - 1)
    return ResultatGuerison(
        profile=updated,
        faim=current_hunger,
        des_exaltation=tuple(dice),
        aggraves_soignes=1,
    )
