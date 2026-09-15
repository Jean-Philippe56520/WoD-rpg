from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


ATTRIBUTS_PHYSIQUES = {"strength", "dexterity", "stamina"}
ATTRIBUTS_SOCIAUX = {"charisma", "manipulation", "composure"}
ATTRIBUTS_MENTAUX = {"intelligence", "wits", "resolve"}


class DegreIssue(str, Enum):
    REUSSITE_EXCEPTIONNELLE = "réussite exceptionnelle"
    REUSSITE_NETTE = "réussite nette"
    REUSSITE_COUTEUSE = "réussite coûteuse"
    REUSSITE_BESTIALE = "réussite bestiale"
    ECHEC_LIMITE = "échec limité"
    ECHEC_SERIEUX = "échec sérieux"
    ECHEC_GRAVE = "échec grave"


@dataclass(frozen=True)
class ConsequenceGraduee:
    degre: DegreIssue
    usure_volonte: int
    pression_faim: int
    intensite_relationnelle: int
    texte: str


def degre_issue(dice) -> DegreIssue:
    """Classe une résolution V5 sans remplacer ses règles de réussite.

    Le jet reste un jet V5 : cette couche sert uniquement à calibrer la portée
    des conséquences persistantes de WoD-rpg. Les anciens doubles de test sans
    marge restent acceptés afin de préserver les contrats historiques du moteur.
    """

    if bool(getattr(dice, "messy_critical", False)):
        return DegreIssue.REUSSITE_BESTIALE
    if bool(getattr(dice, "bestial_failure", False)):
        return DegreIssue.ECHEC_GRAVE

    success = bool(getattr(dice, "success", False))
    critical = bool(getattr(dice, "critical", False))
    margin = getattr(dice, "margin", None)

    if success:
        if critical:
            return DegreIssue.REUSSITE_EXCEPTIONNELLE
        if margin is None:
            return DegreIssue.REUSSITE_NETTE
        if margin >= 3:
            return DegreIssue.REUSSITE_EXCEPTIONNELLE
        if margin >= 1:
            return DegreIssue.REUSSITE_NETTE
        return DegreIssue.REUSSITE_COUTEUSE

    if margin is None:
        return DegreIssue.ECHEC_SERIEUX
    if margin == -1:
        return DegreIssue.ECHEC_LIMITE
    if margin >= -3:
        return DegreIssue.ECHEC_SERIEUX
    return DegreIssue.ECHEC_GRAVE


def famille_action(attribute: str) -> str:
    if attribute in ATTRIBUTS_PHYSIQUES:
        return "physique"
    if attribute in ATTRIBUTS_SOCIAUX:
        return "sociale"
    if attribute in ATTRIBUTS_MENTAUX:
        return "mentale"
    return "autre"


def consequence_graduee(choice, dice) -> ConsequenceGraduee:
    degre = degre_issue(dice)
    famille = famille_action(getattr(choice, "attribute", ""))

    usure_volonte = 0
    if not bool(getattr(dice, "success", False)) and famille in {"sociale", "mentale"}:
        if degre == DegreIssue.ECHEC_SERIEUX:
            usure_volonte = 1
        elif degre == DegreIssue.ECHEC_GRAVE:
            usure_volonte = 2

    pression_faim = 0
    if getattr(choice, "effect", "") in {"hunt", "hunt_social"} and not bool(
        getattr(dice, "success", False)
    ):
        if degre in {DegreIssue.ECHEC_SERIEUX, DegreIssue.ECHEC_GRAVE}:
            pression_faim = 1

    intensite_relationnelle = {
        DegreIssue.REUSSITE_EXCEPTIONNELLE: 2,
        DegreIssue.REUSSITE_NETTE: 1,
        DegreIssue.REUSSITE_COUTEUSE: 0,
        DegreIssue.REUSSITE_BESTIALE: 1,
        DegreIssue.ECHEC_LIMITE: 0,
        DegreIssue.ECHEC_SERIEUX: -1,
        DegreIssue.ECHEC_GRAVE: -2,
    }[degre]

    textes = {
        DegreIssue.REUSSITE_EXCEPTIONNELLE: "Le résultat dépasse nettement l'objectif immédiat et peut créer un avantage durable.",
        DegreIssue.REUSSITE_NETTE: "L'objectif est atteint sans coût majeur visible.",
        DegreIssue.REUSSITE_COUTEUSE: "L'objectif est atteint de justesse, avec une exposition ou un coût potentiel.",
        DegreIssue.REUSSITE_BESTIALE: "L'objectif est atteint, mais la Bête marque la manière dont vous y parvenez.",
        DegreIssue.ECHEC_LIMITE: "L'objectif échoue de peu ; la conséquence reste contenue.",
        DegreIssue.ECHEC_SERIEUX: "L'échec crée une conséquence persistante ou épuise vos ressources.",
        DegreIssue.ECHEC_GRAVE: "L'échec modifie durablement la situation et peut ouvrir une nouvelle crise.",
    }
    return ConsequenceGraduee(
        degre=degre,
        usure_volonte=usure_volonte,
        pression_faim=pression_faim,
        intensite_relationnelle=intensite_relationnelle,
        texte=textes[degre],
    )
