from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SOURCE_TIERS = {
    "A": "Information issue d'une source WoD officielle identifiée ou explicitement référencée.",
    "B": "Information issue de Paris by Night / Kaotic enrichi, utilisée comme continuité parisienne de référence.",
    "C": "Déduction WoD-rpg à partir de plusieurs sources cohérentes.",
    "D": "Création WoD-rpg nécessaire à la simulation ; ne doit jamais être présentée comme canon externe.",
}

AUDIT_STATUSES = {"audited", "partial", "indexed", "linked_unverified"}


@dataclass(frozen=True)
class LoreSourceRef:
    key: str
    label: str
    url: str
    tier: str
    note: str = ""
    source_type: str = "wiki_page"
    categories: tuple[str, ...] = ()
    periods: tuple[str, ...] = ()
    audit_status: str = "indexed"
    relevant_from: int | None = None
    relevant_to: int | None = None
    official_refs: tuple[str, ...] = ()

    def relevant_in(self, year: int) -> bool:
        if self.relevant_from is not None and year < self.relevant_from:
            return False
        if self.relevant_to is not None and year > self.relevant_to:
            return False
        return True


PARIS_BY_NIGHT_ROOT = LoreSourceRef(
    key="pbn_root",
    label="Paris by Night — wiki",
    url="https://parisbynight.quelquesmots.fr/",
    tier="B",
    note=(
        "Source récurrente majeure pour la continuité parisienne. Le wiki reprend et étoffe le contenu Kaotic ; "
        "chaque fait important doit être recoupé avec la fiche, la chronologie, la lignée et les sources officielles citées."
    ),
    source_type="wiki_root",
    categories=("corpus", "provenance"),
    periods=("all",),
    audit_status="audited",
)

WOD_RPG_ERA_MODEL = LoreSourceRef(
    key="wod_rpg_era_model",
    label="WoD-rpg — modèle d'ères",
    url="https://github.com/Jean-Philippe56520/WoD-rpg/blob/main/game/era.py",
    tier="C",
    note="Arbitrage interne du moteur ; ne constitue pas une source canonique externe.",
    source_type="internal_model",
    categories=("timeline", "era", "arbitration"),
    periods=("all",),
    audit_status="audited",
)


def _pbn_url(slug: str) -> str:
    if slug.startswith("index.php?"):
        return f"https://parisbynight.quelquesmots.fr/{slug}"
    return f"https://parisbynight.quelquesmots.fr/index.php/{slug}"


def _pbn(
    key: str,
    label: str,
    slug: str,
    *,
    categories: tuple[str, ...],
    periods: tuple[str, ...] = ("all",),
    audit_status: str = "indexed",
    note: str = "",
    relevant_from: int | None = None,
    relevant_to: int | None = None,
    official_refs: tuple[str, ...] = (),
    tier: str = "B",
) -> LoreSourceRef:
    return LoreSourceRef(
        key=key,
        label=label,
        url=_pbn_url(slug),
        tier=tier,
        note=note,
        categories=categories,
        periods=periods,
        audit_status=audit_status,
        relevant_from=relevant_from,
        relevant_to=relevant_to,
        official_refs=official_refs,
    )


# This manifest is deliberately broader than the facts currently injected into the
# simulation. An indexed source is known to exist; an audited source has been read
# for the fields used by WoD-rpg. This distinction prevents an incomplete audit from
# silently becoming canon.
PARIS_BY_NIGHT_PAGES: dict[str, LoreSourceRef] = {
    "paris_vampire": _pbn(
        "paris_vampire",
        "Paris Vampire",
        "Paris_Vampire",
        categories=("index", "history", "society", "places", "relations"),
        audit_status="audited",
    ),
    "chronologie": _pbn(
        "chronologie",
        "Chronologie",
        "Chronologie",
        categories=("history", "timeline"),
        periods=("medieval", "early_modern", "modern"),
        audit_status="audited",
    ),
    "alexandre_pouvoir": _pbn(
        "alexandre_pouvoir",
        "Alexandre au pouvoir",
        "Alexandre_au_pouvoir",
        categories=("history", "politics", "factions", "characters"),
        periods=("medieval",),
        audit_status="audited",
        relevant_to=1481,
    ),
    "beatrix_pouvoir": _pbn(
        "beatrix_pouvoir",
        "Beatrix au pouvoir",
        "Beatrix_au_pouvoir",
        categories=("history", "politics", "characters"),
        periods=("early_modern",),
        audit_status="indexed",
        relevant_from=1481,
        relevant_to=1789,
    ),
    "villon_pouvoir": _pbn(
        "villon_pouvoir",
        "Villon au pouvoir",
        "Villon_au_pouvoir",
        categories=("history", "politics", "characters"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1789,
    ),
    "principaux_clans_an_mil": _pbn(
        "principaux_clans_an_mil",
        "Les principaux clans de l'an mil",
        "Les_principaux_clans_de_l%27an_mil",
        categories=("history", "clans", "factions"),
        periods=("medieval",),
        audit_status="audited",
    ),
    "alexandre": _pbn(
        "alexandre",
        "Alexandre",
        "index.php?title=Alexandre",
        categories=("character", "ventrue", "lineage", "office"),
        periods=("medieval",),
        audit_status="audited",
        relevant_to=1481,
        tier="A",
        official_refs=(
            "Vampire: The Dark Ages p.93",
            "Transylvania Chronicles I: Dark Tides Rising p.77-82",
            "Clan Novel Dark Ages: Assamite",
            "Clan Novel Dark Ages: Toreador",
            "Clan Novel Dark Ages: Gangrel",
        ),
        note="La fiche signale explicitement plusieurs références officielles Vampire: Dark Ages / romans de clan.",
    ),
    "francois_villon": _pbn(
        "francois_villon",
        "François Villon",
        "index.php?title=Fran%C3%A7ois_Villon",
        categories=("character", "toreador", "lineage", "office"),
        periods=("medieval", "early_modern", "modern"),
        audit_status="audited",
    ),
    "violetta": _pbn(
        "violetta",
        "Violetta",
        "Violetta",
        categories=("character", "toreador", "lineage", "office"),
        periods=("medieval", "early_modern", "modern"),
        audit_status="audited",
        tier="A",
        official_refs=("Giovanni Chronicles II p.80", "Giovanni Chronicles III p.16"),
        note="La fiche cite GC2 et GC3 ; ses dates de fonction doivent être distinguées de la continuité Paris by Night.",
    ),
    "beatrix": _pbn(
        "beatrix",
        "Beatrix",
        "Beatrix",
        categories=("character", "toreador", "office"),
        periods=("medieval", "early_modern"),
        audit_status="audited",
        relevant_to=1789,
    ),
    "magnerius": _pbn(
        "magnerius",
        "Magnerius de Sens",
        "Magnerius_de_Sens",
        categories=("character", "ventrue", "lineage", "office"),
        periods=("medieval", "early_modern"),
        audit_status="audited",
    ),
    "henri_preux": _pbn(
        "henri_preux",
        "Henri le Preux",
        "Henri_le_Preux",
        categories=("character", "ventrue", "lineage", "external_power"),
        periods=("medieval",),
        audit_status="audited",
    ),
    "pompignan": _pbn(
        "pompignan",
        "Pierre Emmanuel de Pompignan",
        "index.php?title=Pierre_Emmanuel_de_Pompignan",
        categories=("character", "ventrue", "lineage", "faction"),
        periods=("medieval", "early_modern", "modern"),
        audit_status="audited",
        note="Sa chronologie personnelle présente une tension avec la chronologie générale autour de 1481 ; conserver le conflit.",
    ),
    "lignees_ventrue": _pbn(
        "lignees_ventrue",
        "Lignées Ventrue",
        "index.php?title=Lign%C3%A9es_Ventrue",
        categories=("lineage", "ventrue", "characters"),
        periods=("all",),
        audit_status="audited",
    ),
    "paris_tremere": _pbn(
        "paris_tremere",
        "Paris Tremere",
        "index.php?title=Paris_tremere",
        categories=("clan", "tremere", "history", "faction"),
        periods=("medieval", "modern"),
        audit_status="partial",
    ),
    "paris_gargouille": _pbn(
        "paris_gargouille",
        "Paris Gargouille",
        "index.php?title=Paris_gargouille",
        categories=("bloodline", "gargoyle", "tremere", "history"),
        periods=("medieval", "modern"),
        audit_status="partial",
    ),
    "us_coutumes": _pbn(
        "us_coutumes",
        "Us et coutumes de Paris",
        "Us_et_coutumes_de_Paris",
        categories=("society", "customs", "law"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
        note="Ne jamais rétroprojeter automatiquement ces usages modernes vers 1435.",
    ),
    "secrets": _pbn(
        "secrets",
        "Secrets",
        "index.php?title=Secrets",
        categories=("information", "secrets", "fog_of_war"),
        periods=("modern",),
        audit_status="audited",
        note="L'échelle A-E inspire la profondeur de connaissance sans être copiée comme règle 1435.",
    ),
    "dettes_prestations": _pbn(
        "dettes_prestations",
        "Liste des Dettes et Prestations",
        "Liste_des_Dettes_et_Prestations",
        categories=("boons", "relations", "politics"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
    ),
    "liens_sang": _pbn(
        "liens_sang",
        "Liste des liens de Sang",
        "Liste_des_liens_de_Sang",
        categories=("blood_bonds", "relations"),
        periods=("modern",),
        audit_status="linked_unverified",
        relevant_from=1804,
        note="La page est liée depuis Paris Vampire ; son contenu reste à auditer explicitement.",
    ),
    "influences": _pbn(
        "influences",
        "Liste des influences",
        "Liste_des_influences",
        categories=("influence", "politics", "mortal_networks"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
    ),
    "salons": _pbn(
        "salons",
        "Salons",
        "Salons",
        categories=("factions", "society", "politics"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
    ),
    "exercice_pouvoir": _pbn(
        "exercice_pouvoir",
        "L'Exercice du Pouvoir à Paris",
        "index.php?title=L%27Exercice_du_Pouvoir_%C3%A0_Paris",
        categories=("politics", "influence", "territory"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
    ),
    "paris_archontes": _pbn(
        "paris_archontes",
        "Paris Archontes",
        "index.php?title=Paris_Archontes",
        categories=("office", "camarilla", "history"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1794,
    ),
    "idees_scenarii": _pbn(
        "idees_scenarii",
        "Idées de scénarii",
        "index.php?title=Id%C3%A9es_de_sc%C3%A9narii",
        categories=("story_hooks", "secrets", "agendas"),
        periods=("modern",),
        audit_status="partial",
        relevant_from=1804,
        note="Réservoir d'amorces ; ne constitue jamais à lui seul une preuve canonique.",
    ),
}

PARIS_CORPUS_SOURCES: dict[str, LoreSourceRef] = {
    PARIS_BY_NIGHT_ROOT.key: PARIS_BY_NIGHT_ROOT,
    WOD_RPG_ERA_MODEL.key: WOD_RPG_ERA_MODEL,
    **PARIS_BY_NIGHT_PAGES,
}


def lore_source(key: str) -> LoreSourceRef:
    try:
        return PARIS_CORPUS_SOURCES[key]
    except KeyError as exc:
        raise ValueError(f"Unknown lore source: {key}") from exc


def sources_for_year(year: int) -> tuple[LoreSourceRef, ...]:
    return tuple(source for source in PARIS_CORPUS_SOURCES.values() if source.relevant_in(year))


def validate_source_catalog(sources: Iterable[LoreSourceRef] | None = None) -> None:
    selected = tuple(sources or PARIS_CORPUS_SOURCES.values())
    keys = [source.key for source in selected]
    if len(keys) != len(set(keys)):
        raise ValueError("Lore source keys must be unique")
    for source in selected:
        if source.tier not in SOURCE_TIERS:
            raise ValueError(f"Unsupported lore source tier: {source.tier}")
        if source.audit_status not in AUDIT_STATUSES:
            raise ValueError(f"Unsupported lore audit status: {source.audit_status}")
        if not source.url.startswith("https://"):
            raise ValueError(f"Lore source must use https: {source.key}")
        if source.relevant_from is not None and source.relevant_to is not None:
            if source.relevant_from > source.relevant_to:
                raise ValueError(f"Invalid lore source period: {source.key}")


def corpus_audit_report(year: int = 1435) -> dict[str, int]:
    validate_source_catalog()
    values = tuple(PARIS_CORPUS_SOURCES.values())
    relevant = tuple(source for source in values if source.relevant_in(year))
    return {
        "sources_total": len(values),
        "audited": sum(source.audit_status == "audited" for source in values),
        "partial": sum(source.audit_status == "partial" for source in values),
        "indexed": sum(source.audit_status == "indexed" for source in values),
        "linked_unverified": sum(source.audit_status == "linked_unverified" for source in values),
        "relevant_year": year,
        "relevant_total": len(relevant),
        "relevant_audited": sum(source.audit_status == "audited" for source in relevant),
    }
