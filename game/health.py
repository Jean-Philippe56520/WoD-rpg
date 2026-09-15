from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from .vampire_profile import VampireProfile


class TypeDegat(str, Enum):
    SUPERFICIEL = "superficiel"
    AGGRAVE = "aggravé"


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


def _points_appliques(amount: int, damage_type: TypeDegat, *, vampire: bool) -> int:
    if amount < 0:
        raise ValueError("Les dégâts ne peuvent pas être négatifs")
    if amount == 0:
        return 0
    if vampire and damage_type == TypeDegat.SUPERFICIEL:
        # V5 : les vampires divisent par deux les dégâts superficiels, arrondis au supérieur.
        return (amount + 1) // 2
    return amount


def appliquer_degats_sante(
    profile: VampireProfile,
    amount: int,
    damage_type: TypeDegat | str,
    *,
    vampire: bool = True,
) -> ResultatDegats:
    """Applique des dégâts à la piste V5 sans dépasser sa taille.

    Tant que la piste contient des cases libres, les dégâts remplissent ces cases.
    Une fois la piste pleine, chaque nouveau niveau de dégâts convertit un dégât
    superficiel déjà marqué en dégât aggravé. Une piste entièrement aggravée met
    un vampire en torpeur.
    """

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

        # Une piste pleine rend le personnage diminué. Les dégâts supplémentaires
        # convertissent alors les marques superficielles en aggravées un pour un.
        if superficiels > 0:
            superficiels -= 1
            aggraves += 1
            convertis += 1
            continue

        # La piste est déjà entièrement aggravée : aucun dépassement n'est stocké.
        break

    updated = replace(
        profile,
        health_superficial=superficiels,
        health_aggravated=aggraves,
    )
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
