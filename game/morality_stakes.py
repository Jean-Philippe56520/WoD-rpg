from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


@dataclass(frozen=True)
class EnjeuMoral:
    situation_id: str
    choice_id: str
    stains: int
    tenet_id: str
    convictions_mitigantes: tuple[str, ...] = ()
    reason: str = ""


# Les Flétrissures ne sont jamais déduites d'un simple échec, d'un échec bestial
# ou d'un critique bestial. Elles doivent être attachées explicitement à une
# décision dont le contenu transgresse un Principe de chronique.
#
# Cette table commence vide : les situations actuellement en production ne
# décrivent pas encore un meurtre volontaire, une trahison de protégé ou une
# transgression équivalente assez explicite pour justifier automatiquement une
# Flétrissure. Les nouveaux choix moralement coûteux devront être ajoutés ici et
# couverts par un test de contenu.
ENJEUX_MORAUX: tuple[EnjeuMoral, ...] = ()


def enjeu_moral(situation_id: str, choice_id: str) -> EnjeuMoral | None:
    for item in ENJEUX_MORAUX:
        if item.situation_id == situation_id and item.choice_id == choice_id:
            return item
    return None


def enjeu_pour_entree_log(entry: Mapping[str, object]) -> EnjeuMoral | None:
    return enjeu_moral(str(entry.get("situation_id", "")), str(entry.get("choice_id", "")))


def conviction_protege(enjeu: EnjeuMoral, convictions: tuple[str, ...]) -> bool:
    return bool(set(enjeu.convictions_mitigantes).intersection(convictions))
