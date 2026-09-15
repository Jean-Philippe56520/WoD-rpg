from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HistoricalSourceRef:
    key: str
    label: str
    url: str
    note: str = ""


HISTORICAL_SOURCES: dict[str, HistoricalSourceRef] = {
    "bnf_hundred_years_war": HistoricalSourceRef(
        key="bnf_hundred_years_war",
        label="Bibliothèque nationale de France — La fin de la guerre de Cent Ans",
        url="https://classes.bnf.fr/phebus/reperes/occ1.htm",
        note=(
            "Référence historique indépendante : paix entre Bourgogne et Charles VII en 1435, "
            "puis abandon de Paris et de sa région par les Anglais en 1436."
        ),
    ),
}


def historical_source(key: str) -> HistoricalSourceRef:
    try:
        return HISTORICAL_SOURCES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown historical source: {key}") from exc
