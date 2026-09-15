from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalPoliticalPressure:
    """A collective historical pressure without inventing a named NPC leader."""

    id: str
    target_id: str
    category: str
    intensity: int
    public_label: str
    internal_reason: str
    source_keys: tuple[str, ...]
    valid_from: int
    valid_to: int

    def active_in(self, year: int) -> bool:
        return self.valid_from <= year <= self.valid_to


# Paris by Night describes Alexandre as having lost effective control after the
# English occupation and the Cour des Miracles as more effective than any other
# vampiric force in the chaotic capital. Independent mortal history confirms that
# Paris remains outside Charles VII's control throughout 1435 and is recovered in
# 1436. We model those facts as pressures, not as fictional leaders or forced
# succession outcomes.
PARIS_HISTORICAL_POLITICAL_PRESSURES: tuple[HistoricalPoliticalPressure, ...] = (
    HistoricalPoliticalPressure(
        id="pressure_english_occupation_1435",
        target_id="npc_alexandre",
        category="external_occupation",
        intensity=4,
        public_label="Occupation anglaise et recomposition des appuis bourguignons",
        internal_reason=(
            "Paris demeure hors du contrôle de Charles VII en 1435 ; l'occupation mortelle prive Alexandre "
            "d'une grande partie des relais qui soutenaient son autorité."
        ),
        source_keys=("alexandre_pouvoir", "chronologie"),
        valid_from=1435,
        valid_to=1435,
    ),
    HistoricalPoliticalPressure(
        id="pressure_court_miracles_1435",
        target_id="npc_alexandre",
        category="parallel_court",
        intensity=5,
        public_label="Cour des Miracles et contre-pouvoir des clans marginalisés",
        internal_reason=(
            "La Cour des Miracles rassemble Brujah, Malkaviens, Gangrels et Nosferatus et exerce, "
            "dans la crise, une influence parisienne supérieure à celle de la Cour officielle."
        ),
        source_keys=("alexandre_pouvoir",),
        valid_from=1435,
        valid_to=1435,
    ),
)


def active_historical_political_pressures(
    year: int,
    *,
    target_id: str | None = None,
) -> tuple[HistoricalPoliticalPressure, ...]:
    return tuple(
        pressure
        for pressure in PARIS_HISTORICAL_POLITICAL_PRESSURES
        if pressure.active_in(year)
        and (target_id is None or pressure.target_id == target_id)
    )
