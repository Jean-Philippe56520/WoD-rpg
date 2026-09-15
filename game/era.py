from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CamarillaStage(str, Enum):
    ABSENT = "absent"
    PROJECT = "project"
    COALITION = "coalition"
    INSTITUTIONAL = "institutional"


@dataclass(frozen=True)
class EraRules:
    """Rules exposed to the engine for a given historical period.

    The chronology intentionally distinguishes local custom from universal law.
    A Prince, a council of elders, or a clan representative may exist before the
    Camarilla, but the engine must not present late-Camarilla institutions as if
    they were already standardized everywhere in 1435.
    """

    year: int
    label: str
    camarilla_stage: CamarillaStage
    anarch_revolt_active: bool
    mortal_hunters_severe: bool
    prince_is_local_office: bool
    primogen_council_standardized: bool
    masquerade_codified: bool
    accounting_customary: bool
    progeny_permission_local: bool
    high_low_clan_order_relevant: bool
    available_offices: tuple[str, ...]
    public_context: str


@dataclass(frozen=True)
class HistoricalMilestone:
    year: int
    id: str
    title: str
    public_text: str
    forced_convergence: bool = True


MILESTONES: tuple[HistoricalMilestone, ...] = (
    HistoricalMilestone(
        year=1435,
        id="hardestadt_project",
        title="Un projet d'ordre commun",
        public_text=(
            "Des anciens, autour de Hardestadt et de ses alliés, défendent plus ouvertement "
            "l'idée d'une coalition capable de contenir la révolte et les chasseurs. Rien n'est "
            "encore une autorité universelle."
        ),
        forced_convergence=False,
    ),
    HistoricalMilestone(
        year=1486,
        id="camarilla_consolidation",
        title="La coalition se structure",
        public_text=(
            "Les réseaux qui se réclament du nouvel ordre coordonnent davantage leurs décisions. "
            "Les usages locaux demeurent puissants, mais les pressions en faveur de règles communes augmentent."
        ),
    ),
    HistoricalMilestone(
        year=1493,
        id="convention_of_thorns",
        title="Convention des Épines",
        public_text=(
            "La Convention des Épines redéfinit l'équilibre entre anciens, révoltés et nouvelle "
            "Camarilla. Les choix, dettes et inimitiés accumulés avant cette date déterminent qui "
            "est entendu, toléré, soumis ou rejeté."
        ),
    ),
)


def era_for_year(year: int) -> EraRules:
    if year < 1435:
        return EraRules(
            year=year,
            label="Fin de la Longue Nuit",
            camarilla_stage=CamarillaStage.ABSENT,
            anarch_revolt_active=True,
            mortal_hunters_severe=True,
            prince_is_local_office=True,
            primogen_council_standardized=False,
            masquerade_codified=False,
            accounting_customary=True,
            progeny_permission_local=True,
            high_low_clan_order_relevant=True,
            available_offices=("none", "domain_holder", "clan_envoy", "prince"),
            public_context=(
                "Les Caïnites vivent sous des coutumes locales, des lignages, des serments et la force réelle "
                "des seigneurs nocturnes. La révolte contre les anciens fracture déjà de nombreuses régions."
            ),
        )
    if year < 1486:
        return EraRules(
            year=year,
            label="Naissance de la coalition",
            camarilla_stage=CamarillaStage.PROJECT,
            anarch_revolt_active=True,
            mortal_hunters_severe=True,
            prince_is_local_office=True,
            primogen_council_standardized=False,
            masquerade_codified=False,
            accounting_customary=True,
            progeny_permission_local=True,
            high_low_clan_order_relevant=True,
            available_offices=("none", "domain_holder", "clan_envoy", "prince"),
            public_context=(
                "Un projet de coalition entre anciens gagne des soutiens, sans constituer encore un gouvernement "
                "universel. Princes, conseils d'anciens, lignages et coutumes locales restent déterminants."
            ),
        )
    if year < 1493:
        return EraRules(
            year=year,
            label="Coalition proto-Camarilla",
            camarilla_stage=CamarillaStage.COALITION,
            anarch_revolt_active=True,
            mortal_hunters_severe=True,
            prince_is_local_office=True,
            primogen_council_standardized=False,
            masquerade_codified=False,
            accounting_customary=True,
            progeny_permission_local=True,
            high_low_clan_order_relevant=True,
            available_offices=("none", "domain_holder", "clan_envoy", "prince"),
            public_context=(
                "La coalition devient plus visible et tente d'harmoniser les pratiques, mais aucune ville ne doit "
                "être supposée appliquer mécaniquement les institutions de la Camarilla moderne."
            ),
        )
    return EraRules(
        year=year,
        label="Après la Convention des Épines",
        camarilla_stage=CamarillaStage.INSTITUTIONAL,
        anarch_revolt_active=False,
        mortal_hunters_severe=True,
        prince_is_local_office=True,
        primogen_council_standardized=True,
        masquerade_codified=True,
        accounting_customary=True,
        progeny_permission_local=True,
        high_low_clan_order_relevant=False,
        available_offices=("none", "domain_holder", "clan_envoy", "primogen", "prince"),
        public_context=(
            "La Camarilla devient une institution identifiable. Les usages locaux subsistent, mais la Mascarade, "
            "les représentations de clan et les structures de Cour prennent une forme beaucoup plus familière."
        ),
    )


def milestones_crossed(previous_year: int, next_year: int) -> tuple[HistoricalMilestone, ...]:
    if next_year < previous_year:
        raise ValueError("Historical time cannot move backwards")
    return tuple(item for item in MILESTONES if previous_year < item.year <= next_year)


def milestone_for_year(year: int) -> HistoricalMilestone | None:
    for item in MILESTONES:
        if item.year == year:
            return item
    return None
