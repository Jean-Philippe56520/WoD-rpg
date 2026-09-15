from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LoreSourceRef:
    key: str
    label: str
    url: str
    tier: str
    note: str = ""


SOURCE_TIERS = {
    "A": "Information issue d'une source WoD officielle identifiée ou explicitement signalée comme officielle.",
    "B": "Information issue de Paris by Night / Kaotic enrichi, utilisée comme continuité parisienne de référence.",
    "C": "Déduction WoD-rpg à partir de plusieurs sources cohérentes.",
    "D": "Création WoD-rpg nécessaire à la simulation ; ne doit pas être présentée comme canon externe.",
}

PARIS_BY_NIGHT_ROOT = LoreSourceRef(
    key="pbn_root",
    label="Paris by Night — wiki",
    url="https://parisbynight.quelquesmots.fr/",
    tier="B",
    note=(
        "Source récurrente majeure pour la continuité parisienne. Le wiki reprend et étoffe le contenu Kaotic ; "
        "chaque fait important doit être recoupé avec la fiche, la chronologie, la lignée et les sources officielles citées."
    ),
)

PARIS_BY_NIGHT_PAGES: dict[str, LoreSourceRef] = {
    "paris_vampire": LoreSourceRef(
        "paris_vampire",
        "Paris Vampire",
        "https://parisbynight.quelquesmots.fr/index.php/Paris_Vampire",
        "B",
    ),
    "chronologie": LoreSourceRef(
        "chronologie",
        "Chronologie",
        "https://parisbynight.quelquesmots.fr/index.php/Chronologie",
        "B",
    ),
    "alexandre_pouvoir": LoreSourceRef(
        "alexandre_pouvoir",
        "Alexandre au pouvoir",
        "https://parisbynight.quelquesmots.fr/index.php/Alexandre_au_pouvoir",
        "B",
    ),
    "alexandre": LoreSourceRef(
        "alexandre",
        "Alexandre",
        "https://parisbynight.quelquesmots.fr/index.php?title=Alexandre",
        "A",
        "La fiche signale explicitement des références officielles Vampire: Dark Ages / romans de clan.",
    ),
    "francois_villon": LoreSourceRef(
        "francois_villon",
        "François Villon",
        "https://parisbynight.quelquesmots.fr/index.php?title=Fran%C3%A7ois_Villon",
        "B",
    ),
    "violetta": LoreSourceRef(
        "violetta",
        "Violetta",
        "https://parisbynight.quelquesmots.fr/index.php/Violetta",
        "A",
        "La fiche cite notamment GC2 p.80 et GC3 p.16 pour son étreinte et son élection comme Justicar.",
    ),
    "beatrix": LoreSourceRef(
        "beatrix",
        "Beatrix",
        "https://parisbynight.quelquesmots.fr/index.php/Beatrix",
        "B",
    ),
    "magnerius": LoreSourceRef(
        "magnerius",
        "Magnerius de Sens",
        "https://parisbynight.quelquesmots.fr/index.php/Magnerius_de_Sens",
        "B",
    ),
    "henri_preux": LoreSourceRef(
        "henri_preux",
        "Henri le Preux",
        "https://parisbynight.quelquesmots.fr/index.php/Henri_le_Preux",
        "B",
    ),
    "pompignan": LoreSourceRef(
        "pompignan",
        "Pierre Emmanuel de Pompignan",
        "https://parisbynight.quelquesmots.fr/index.php?title=Pierre_Emmanuel_de_Pompignan",
        "B",
        "Sa chronologie personnelle présente une tension avec la chronologie générale autour de 1481 ; statut 1435 à arbitrer avec prudence.",
    ),
    "lignees_ventrue": LoreSourceRef(
        "lignees_ventrue",
        "Lignées Ventrue",
        "https://parisbynight.quelquesmots.fr/index.php?title=Lign%C3%A9es_Ventrue",
        "B",
    ),
    "principaux_clans_an_mil": LoreSourceRef(
        "principaux_clans_an_mil",
        "Les principaux clans de l'an mil",
        "https://parisbynight.quelquesmots.fr/index.php/Les_principaux_clans_de_l%27an_mil",
        "B",
    ),
}


def lore_source(key: str) -> LoreSourceRef:
    if key == PARIS_BY_NIGHT_ROOT.key:
        return PARIS_BY_NIGHT_ROOT
    try:
        return PARIS_BY_NIGHT_PAGES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown lore source: {key}") from exc
