from __future__ import annotations

from dataclasses import dataclass, replace

from .consequences import consequence_graduee


BONUS_COUP_DE_SANG = {
    0: 1,
    1: 2,
    2: 2,
    3: 3,
    4: 3,
    5: 4,
    6: 4,
    7: 5,
    8: 5,
    9: 6,
    10: 6,
}

# Table V5 corrigée (Companion / Player's Guide) : la Sévérité du Fléau
# n'est pas identique au bonus de Coup de Sang pour Puissance 0.
BANE_SEVERITY = {
    0: 0,
    1: 2,
    2: 2,
    3: 3,
    4: 3,
    5: 4,
    6: 4,
    7: 5,
    8: 5,
    9: 6,
    10: 6,
}


@dataclass(frozen=True)
class UsageDiscipline:
    discipline: str
    pouvoir: str
    bonus_des: int
    description: str


def bonus_coup_de_sang(puissance_du_sang: int) -> int:
    if puissance_du_sang not in BONUS_COUP_DE_SANG:
        raise ValueError("Puissance du Sang hors plage prise en charge")
    return BONUS_COUP_DE_SANG[puissance_du_sang]


def severite_fleau(puissance_du_sang: int) -> int:
    if puissance_du_sang not in BANE_SEVERITY:
        raise ValueError("Puissance du Sang hors plage prise en charge")
    return BANE_SEVERITY[puissance_du_sang]


def perte_volonte_apres_echec(choice, dice) -> int:
    """Délègue l'usure de Volonté à la couche de conséquences graduées."""

    return consequence_graduee(choice, dice).usure_volonte


def recuperer_volonte_fin_nuit(profile) -> tuple[object, int]:
    """Récupère l'usure superficielle entre deux Nuits significatives.

    Le rythme asynchrone assimile une Nuit significative à une séance de jeu :
    la récupération est donc plafonnée par le meilleur score entre Résolution
    et Sang-froid, sans dépasser la Volonté maximale.
    """

    manque = max(0, profile.volonte_maximale - profile.willpower)
    recuperation = min(
        manque,
        max(profile.attributes["resolve"], profile.attributes["composure"]),
    )
    if recuperation <= 0:
        return profile, 0
    return replace(profile, willpower=profile.willpower + recuperation), recuperation


def _niveau(profile, nom: str) -> int:
    cible = nom.casefold()
    for discipline, niveau in profile.disciplines.items():
        if discipline.casefold() == cible:
            return int(niveau)
    return 0


def usage_discipline(profile, situation, choice) -> UsageDiscipline | None:
    """Retourne uniquement un pouvoir dont l'effet V5 est cohérent avec l'action.

    Aucun bonus générique n'est accordé pour le simple fait de posséder une
    Discipline. Les pouvoirs non encore représentés par les scènes restent sans
    effet mécanique jusqu'à leur intégration explicite.
    """

    presence = _niveau(profile, "Présence")
    if presence > 0 and choice.skill == "persuasion":
        return UsageDiscipline(
            discipline="Présence",
            pouvoir="Révérence",
            bonus_des=presence,
            description="Votre présence surnaturelle renforce une tentative de persuasion.",
        )

    auspex = _niveau(profile, "Auspex")
    if auspex > 0 and choice.skill in {"awareness", "insight"}:
        return UsageDiscipline(
            discipline="Auspex",
            pouvoir="Sens accrus",
            bonus_des=auspex,
            description="Vos sens surnaturels affinent l'observation et la lecture des détails.",
        )

    fortitude = _niveau(profile, "Force d'âme")
    if fortitude > 0 and choice.effect in {"sire_refuse", "cautious_distance"}:
        return UsageDiscipline(
            discipline="Force d'âme",
            pouvoir="Esprit résolu",
            bonus_des=fortitude,
            description="Votre esprit résiste mieux à la pression et à la coercition.",
        )

    # Grâce féline, Corps létal et Contrainte produisent des effets qualitatifs
    # qui exigent des scènes dédiées plutôt qu'un simple bonus de dés. Ils ne
    # sont donc volontairement pas convertis en bonus générique ici.
    return None
