from __future__ import annotations

from dataclasses import dataclass
import hashlib

from .chronicle import CLAN_DISCIPLINES, SireProfile, sire_candidates


@dataclass(frozen=True)
class MortalOrigin:
    id: str
    label: str
    description: str


@dataclass(frozen=True)
class ConvictionDefinition:
    id: str
    label: str
    description: str
    favored_skill: str


MORTAL_ORIGINS: tuple[MortalOrigin, ...] = (
    MortalOrigin("noble", "Noble", "Vous avez connu les obligations de lignage, de terre et de cour."),
    MortalOrigin("clergy", "Clerc ou religieux", "Vous avez vécu parmi les institutions religieuses, les textes et les serments."),
    MortalOrigin("merchant", "Marchand", "Votre ancienne vie dépendait des routes, des contrats et des réseaux."),
    MortalOrigin("artisan", "Artisan", "Votre place venait d'un métier, d'un atelier et de relations concrètes."),
    MortalOrigin("soldier", "Soldat ou homme d'armes", "Vous avez appris la discipline, le danger et les rapports de force."),
    MortalOrigin("scholar", "Érudit", "Vous avez vécu par les livres, l'enseignement ou l'observation."),
    MortalOrigin("commoner", "Gens du commun", "Vous connaissez les dépendances ordinaires que les puissants voient rarement."),
    MortalOrigin("outlaw", "Hors-la-loi", "Vous avez survécu en marge d'un ordre qui vous refusait sa protection."),
)

ORIGIN_LABELS = {item.id: item.label for item in MORTAL_ORIGINS}
ORIGIN_DESCRIPTIONS = {item.id: item.description for item in MORTAL_ORIGINS}


CONVICTIONS: tuple[ConvictionDefinition, ...] = (
    ConvictionDefinition(
        "keep_word",
        "Tenir ma parole",
        "Quand vous vous engagez, rompre votre parole doit avoir un coût réel.",
        "etiquette",
    ),
    ConvictionDefinition(
        "protect_innocents",
        "Protéger les innocents",
        "Vous refusez que les faibles paient simplement pour faciliter votre survie.",
        "insight",
    ),
    ConvictionDefinition(
        "never_abandon_own",
        "Ne jamais abandonner les miens",
        "Loyauté et solidarité priment lorsque ceux que vous avez reconnus sont menacés.",
        "persuasion",
    ),
    ConvictionDefinition(
        "resist_tyranny",
        "Refuser la tyrannie",
        "Vous supportez mal qu'un pouvoir exige l'obéissance uniquement parce qu'il est ancien ou fort.",
        "politics",
    ),
    ConvictionDefinition(
        "repay_debts",
        "Toujours payer mes dettes",
        "Une dette reconnue crée une obligation que vous refusez d'ignorer.",
        "politics",
    ),
    ConvictionDefinition(
        "avoid_needless_killing",
        "Ne tuer qu'en dernier recours",
        "Vous pouvez être un prédateur sans considérer la mort comme une solution ordinaire.",
        "survival",
    ),
)

CONVICTION_BY_ID = {item.id: item for item in CONVICTIONS}
CONVICTION_BY_LABEL = {item.label: item for item in CONVICTIONS}


VENTRUE_FEEDING_PREFERENCES: tuple[str, ...] = (
    "Nobles et membres de leur maison",
    "Membres du clergé",
    "Soldats et gens d'armes",
    "Marchands et changeurs",
    "Artisans qualifiés",
    "Hors-la-loi et criminels",
    "Gens du commun liés à la terre",
)


_SIRE_ORIGIN_WEIGHTS: dict[str, dict[str, int]] = {
    "sire_ventrue_aymon": {"noble": 4, "soldier": 2, "clergy": 1},
    "sire_ventrue_heloise": {"merchant": 4, "artisan": 2, "scholar": 1, "commoner": 1},
    "sire_toreador_isabeau": {"noble": 3, "clergy": 2, "scholar": 2, "artisan": 1},
    "sire_toreador_matteo": {"artisan": 4, "merchant": 2, "scholar": 2, "outlaw": 1},
    "sire_brujah_guilhem": {"scholar": 4, "clergy": 2, "noble": 1, "soldier": 1},
    "sire_brujah_ysabeau": {"outlaw": 4, "soldier": 3, "commoner": 2, "artisan": 1},
}

_SIRE_CONVICTION_WEIGHTS: dict[str, dict[str, int]] = {
    "sire_ventrue_aymon": {"keep_word": 3, "repay_debts": 3, "never_abandon_own": 1},
    "sire_ventrue_heloise": {"repay_debts": 3, "protect_innocents": 1, "resist_tyranny": 1},
    "sire_toreador_isabeau": {"protect_innocents": 3, "keep_word": 2, "avoid_needless_killing": 1},
    "sire_toreador_matteo": {"resist_tyranny": 3, "protect_innocents": 1, "never_abandon_own": 1},
    "sire_brujah_guilhem": {"keep_word": 3, "never_abandon_own": 2, "avoid_needless_killing": 1},
    "sire_brujah_ysabeau": {"resist_tyranny": 4, "never_abandon_own": 2, "protect_innocents": 1},
}

_SIRE_DISCIPLINE_WEIGHTS: dict[str, dict[str, int]] = {
    "sire_ventrue_aymon": {"Domination": 2, "Force d'âme": 1},
    "sire_ventrue_heloise": {"Présence": 2, "Domination": 1},
    "sire_toreador_isabeau": {"Auspex": 2, "Présence": 1},
    "sire_toreador_matteo": {"Célérité": 2, "Présence": 1},
    "sire_brujah_guilhem": {"Présence": 2, "Célérité": 1},
    "sire_brujah_ysabeau": {"Puissance": 2, "Célérité": 1},
}


def mortal_origin(origin_id: str) -> MortalOrigin:
    for item in MORTAL_ORIGINS:
        if item.id == origin_id:
            return item
    raise ValueError(f"Unknown mortal origin: {origin_id}")


def conviction(conviction_id: str) -> ConvictionDefinition:
    try:
        return CONVICTION_BY_ID[conviction_id]
    except KeyError as exc:
        raise ValueError(f"Unknown conviction: {conviction_id}") from exc


def conviction_from_label(label: str) -> ConvictionDefinition | None:
    return CONVICTION_BY_LABEL.get(label)


def apply_conviction_skill_bonus(skills: dict[str, int], conviction_id: str) -> dict[str, int]:
    selected = conviction(conviction_id)
    updated = dict(skills)
    if selected.favored_skill not in updated:
        raise ValueError(f"Conviction skill is unavailable: {selected.favored_skill}")
    updated[selected.favored_skill] = min(5, updated[selected.favored_skill] + 1)
    return updated


def sire_score(
    sire: SireProfile,
    *,
    origin_id: str,
    conviction_id: str,
    starting_discipline: str,
) -> int:
    return (
        _SIRE_ORIGIN_WEIGHTS.get(sire.id, {}).get(origin_id, 0)
        + _SIRE_CONVICTION_WEIGHTS.get(sire.id, {}).get(conviction_id, 0)
        + _SIRE_DISCIPLINE_WEIGHTS.get(sire.id, {}).get(starting_discipline, 0)
    )


def choose_sire_from_creation(
    *,
    clan_id: str,
    origin_id: str,
    conviction_id: str,
    starting_discipline: str,
    stable_key: str,
) -> SireProfile:
    mortal_origin(origin_id)
    conviction(conviction_id)
    if starting_discipline not in CLAN_DISCIPLINES.get(clan_id, ()):
        raise ValueError("Starting discipline must belong to the selected clan")
    candidates = sire_candidates(clan_id)
    if not candidates:
        raise ValueError(f"No sire available for clan {clan_id}")

    scores = {
        sire.id: sire_score(
            sire,
            origin_id=origin_id,
            conviction_id=conviction_id,
            starting_discipline=starting_discipline,
        )
        for sire in candidates
    }
    best = max(scores.values())
    tied = sorted((sire for sire in candidates if scores[sire.id] == best), key=lambda item: item.id)
    if len(tied) == 1:
        return tied[0]

    digest = hashlib.sha256(stable_key.encode("utf-8")).digest()
    return tied[digest[0] % len(tied)]


def concept_from_origin(origin_id: str, detail: str = "") -> str:
    origin = mortal_origin(origin_id)
    cleaned = " ".join(detail.strip().split())
    if not cleaned:
        return origin.label
    return f"{origin.label} — {cleaned[:120]}"
