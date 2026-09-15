from __future__ import annotations

from dataclasses import dataclass

from .historical_sources import HISTORICAL_SOURCES
from .lore_catalog import PARIS_CORPUS_SOURCES


@dataclass(frozen=True)
class HistoricalPoliticalPressure:
    """A collective historical pressure without inventing a named NPC leader."""

    id: str
    target_office: str
    category: str
    intensity: int
    public_label: str
    internal_reason: str
    lore_source_keys: tuple[str, ...]
    historical_source_keys: tuple[str, ...]
    valid_from: int
    valid_to: int

    def active_in(self, year: int) -> bool:
        return self.valid_from <= year <= self.valid_to


# Paris by Night describes Alexandre as having lost effective control after the
# English occupation and the Cour des Miracles as more effective than any other
# vampiric force in the chaotic capital. Independent mortal history confirms that
# Paris remains outside Charles VII's control throughout 1435 and is recovered in
# 1436. We model those facts as pressures on the Praxis, not as fictional leaders
# or forced succession outcomes.
PARIS_HISTORICAL_POLITICAL_PRESSURES: tuple[HistoricalPoliticalPressure, ...] = (
    HistoricalPoliticalPressure(
        id="pressure_english_occupation_1435",
        target_office="prince",
        category="external_occupation",
        intensity=4,
        public_label="Occupation anglaise et recomposition des appuis bourguignons",
        internal_reason=(
            "Paris demeure hors du contrôle de Charles VII en 1435 ; l'occupation mortelle prive la Praxis "
            "d'une grande partie des relais institutionnels et aristocratiques qui soutenaient son autorité."
        ),
        lore_source_keys=("alexandre_pouvoir", "chronologie"),
        historical_source_keys=("bnf_hundred_years_war",),
        valid_from=1435,
        valid_to=1435,
    ),
    HistoricalPoliticalPressure(
        id="pressure_court_miracles_1435",
        target_office="prince",
        category="parallel_court",
        intensity=5,
        public_label="Cour des Miracles et contre-pouvoir des clans marginalisés",
        internal_reason=(
            "La Cour des Miracles rassemble Brujah, Malkaviens, Gangrels et Nosferatus et exerce, "
            "dans la crise, une influence parisienne supérieure à celle de la Cour officielle."
        ),
        lore_source_keys=("alexandre_pouvoir",),
        historical_source_keys=(),
        valid_from=1435,
        valid_to=1435,
    ),
)


def validate_historical_political_pressures() -> None:
    ids = [pressure.id for pressure in PARIS_HISTORICAL_POLITICAL_PRESSURES]
    if len(ids) != len(set(ids)):
        raise ValueError("Historical political pressure ids must be unique")
    for pressure in PARIS_HISTORICAL_POLITICAL_PRESSURES:
        if not 1 <= pressure.intensity <= 5:
            raise ValueError(f"Invalid pressure intensity: {pressure.id}")
        if pressure.valid_from > pressure.valid_to:
            raise ValueError(f"Invalid pressure period: {pressure.id}")
        for key in pressure.lore_source_keys:
            if key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown lore source {key} for pressure {pressure.id}")
        for key in pressure.historical_source_keys:
            if key not in HISTORICAL_SOURCES:
                raise ValueError(f"Unknown historical source {key} for pressure {pressure.id}")


def active_historical_political_pressures(
    year: int,
    *,
    target_office: str | None = None,
) -> tuple[HistoricalPoliticalPressure, ...]:
    validate_historical_political_pressures()
    return tuple(
        pressure
        for pressure in PARIS_HISTORICAL_POLITICAL_PRESSURES
        if pressure.active_in(year)
        and (target_office is None or pressure.target_office == target_office)
    )
