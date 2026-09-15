from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .lore_catalog import PARIS_CORPUS_SOURCES


COVERAGE_STATUSES = {"structured", "partial", "indexed", "missing"}


@dataclass(frozen=True)
class CorpusArea:
    """A family of Paris data that the project must never forget.

    Coverage is deliberately separate from source-page audit state. A family can
    be structured in the engine while historical content remains partial, or be
    indexed because Paris by Night exposes it even though WoD-rpg has not yet
    extracted the relevant facts.
    """

    id: str
    label: str
    source_keys: tuple[str, ...]
    priority_1435: bool
    coverage_status: str
    engine_target: str
    modern_only_guard: bool = False
    note: str = ""


# The list mirrors the families exposed by Paris Vampire's master index and adds
# only engine-facing distinctions that matter to a persistent medieval Chronicle.
# A test locks these IDs so an entire data family cannot disappear silently.
PARIS_CORPUS_AREAS: tuple[CorpusArea, ...] = (
    CorpusArea(
        "history_timeline",
        "Histoire générale et chronologie vampirique",
        ("paris_vampire", "chronologie", "alexandre_pouvoir"),
        True,
        "structured",
        "paris_corpus.py / era.py / CanonicalPressure",
        note="La chronologie future reste une pression conditionnelle, jamais un script forcé.",
    ),
    CorpusArea(
        "mortal_history",
        "Chronologie et contexte mortels",
        ("paris_vampire", "chronologie"),
        True,
        "partial",
        "era.py / futurs contextes historiques",
        note="Doit relier occupation anglaise, Guerre de Cent Ans, institutions et transformations urbaines aux enjeux caïnites.",
    ),
    CorpusArea(
        "characters",
        "Personnages vampiriques et fiches individuelles",
        ("paris_vampire",),
        True,
        "partial",
        "paris_corpus.py / paris_lore.py",
        note="Le roster 1435 n'est pas encore exhaustif ; les acteurs incertains restent hors simulation active.",
    ),
    CorpusArea(
        "lineages",
        "Lignées, sires et infants",
        ("paris_vampire", "lignees_ventrue"),
        True,
        "partial",
        "LoreFact / graphe de lignées",
        note="Les lignées Ventrue sont amorcées ; les autres clans doivent être audités avec le même niveau de précision.",
    ),
    CorpusArea(
        "clans",
        "Clans, lignages et groupes de sang présents à Paris",
        ("paris_vampire", "principaux_clans_an_mil"),
        True,
        "partial",
        "paris_corpus.py / factions / seeds",
        note="Les trois clans jouables ne limitent jamais les clans PNJ du monde.",
    ),
    CorpusArea(
        "presence_location",
        "Présence, absence, torpeur, disparition et localisation des PNJ",
        ("paris_vampire",),
        True,
        "partial",
        "ParisPresence / chronologie de présence",
        note="Essentiel pour savoir qui peut réellement agir ou être rencontré à une date donnée.",
    ),
    CorpusArea(
        "anarchs",
        "Anarchs, révoltes et contre-pouvoirs",
        ("paris_vampire", "alexandre_pouvoir", "chronologie"),
        True,
        "partial",
        "factions / agendas / HistoricalPressure",
        note="Priorité 1435 élevée : Révolte Anarch, Cour des Miracles et futurs Écorcheurs.",
    ),
    CorpusArea(
        "sabbat",
        "Sabbat et groupes hostiles liés à son histoire",
        ("paris_vampire",),
        False,
        "indexed",
        "factions futures / chronologie longue",
        modern_only_guard=True,
        note="Le contenu parisien moderne ne doit pas être rétroprojeté vers 1435 ; suivre seulement les antécédents historiquement valides.",
    ),
    CorpusArea(
        "camarilla_institutions",
        "Naissance de la Camarilla et institutions",
        ("paris_vampire", "chronologie", "wod_rpg_era_model"),
        True,
        "structured",
        "era.py / offices / conflicts",
        note="1435 est une phase de naissance : aucune Cour moderne standardisée ne doit être projetée en arrière.",
    ),
    CorpusArea(
        "offices_power",
        "Prince, représentants, Primogènes et autres offices",
        ("paris_vampire", "alexandre_pouvoir", "exercice_pouvoir"),
        True,
        "partial",
        "chronicle_politics.py / chronicle_offices.py / praxis.py",
        note="Les chronologies modernes d'office restent utiles pour les siècles futurs, pas pour remplir artificiellement 1435.",
    ),
    CorpusArea(
        "praxis_succession",
        "Praxis, crises de succession et légitimité",
        ("alexandre_pouvoir", "chronologie"),
        True,
        "structured",
        "praxis.py / SimulationBeat",
        note="La succession émerge des rapports de force ; 1481 est une pression de référence, pas un résultat imposé.",
    ),
    CorpusArea(
        "factions_coteries",
        "Factions, coteries, salons et réseaux politiques",
        ("paris_vampire", "salons", "alexandre_pouvoir"),
        True,
        "partial",
        "ParisFactionPresence / agendas",
        note="Cour d'Alexandre, réseaux toréador et Cour des Miracles sont structurés ; le reste demeure à recenser par période.",
    ),
    CorpusArea(
        "relationships",
        "Alliances, rivalités, patronages et relations",
        ("paris_vampire",),
        True,
        "partial",
        "relationship_memory.py / NpcState.relations",
        note="Les relations historiques sourcées doivent rester distinctes des relations dynamiques créées par la partie.",
    ),
    CorpusArea(
        "prestations",
        "Dettes et Prestations",
        ("paris_vampire", "dettes_prestations"),
        True,
        "partial",
        "BoonState / grant_boon / hooks",
        modern_only_guard=True,
        note="La page moderne sert de famille de données ; aucune dette moderne n'est appliquée à 1435 sans preuve historique.",
    ),
    CorpusArea(
        "blood_bonds",
        "Liens de Sang",
        ("paris_vampire", "liens_sang"),
        True,
        "indexed",
        "futur registre relationnel / effets sociaux",
        modern_only_guard=True,
        note="Paris by Night indique lui-même que sa liste est partielle ; la mécanique 1435 reste à structurer sans importer des liens modernes.",
    ),
    CorpusArea(
        "mortal_influences",
        "Influences mortelles et réseaux institutionnels",
        ("paris_vampire", "influences"),
        True,
        "partial",
        "influence / agendas / futures ressources de réseau",
        modern_only_guard=True,
        note="Les catégories d'influence sont utiles, mais leurs détenteurs modernes ne valent pas pour le XVe siècle.",
    ),
    CorpusArea(
        "domains_territory",
        "Domaines, fiefs, droits de chasse et contrôle territorial",
        ("paris_vampire", "exercice_pouvoir"),
        True,
        "partial",
        "DomainState / HuntingAccessState / Viandis-Servage-Rempart",
        modern_only_guard=True,
        note="Les Bourgs modernes ne sont pas les Domaines de 1435. Le moteur médiéval utilise une géographie propre.",
    ),
    CorpusArea(
        "historical_geography",
        "Géographie historique, lieux, routes, ponts et quartiers",
        ("paris_vampire",),
        True,
        "partial",
        "DomainState / futur registre de lieux",
        note="Doit privilégier le Paris du XVe siècle : Cité, Louvre médiéval, Halles, Université, quais, portes, faubourgs et routes.",
    ),
    CorpusArea(
        "elysium_court_customs",
        "Cour, Elysium, ton politique et usages",
        ("paris_vampire", "us_coutumes"),
        True,
        "partial",
        "situations / era rules / futurs lieux sociaux",
        modern_only_guard=True,
        note="Les usages décrits pour la Cour moderne sont des références typologiques, pas des lois automatiques en 1435.",
    ),
    CorpusArea(
        "secrets_information",
        "Secrets, niveaux de connaissance, rumeurs et désinformation",
        ("paris_vampire", "secrets"),
        True,
        "structured",
        "world_situations.py / narrative_state.py",
        modern_only_guard=True,
        note="Le moteur utilise l'information imparfaite ; les secrets modernes du wiki restent liés à leur période.",
    ),
    CorpusArea(
        "events_incidents",
        "Événements, incidents, crises et faits divers",
        ("paris_vampire", "chronologie"),
        True,
        "partial",
        "ChronicleWorldStore / SimulationBeat / HistoricalPressure",
        note="Les incidents doivent devenir des conséquences persistantes ou des pressions conditionnelles.",
    ),
    CorpusArea(
        "external_powers",
        "Puissances extérieures influençant Paris",
        ("alexandre_pouvoir", "chronologie"),
        True,
        "partial",
        "ParisPresence external / factions / agendas",
        note="Mithras et Bourges sont amorcés ; Normandie, Bourgogne, Orléans et autres pôles doivent être audités.",
    ),
    CorpusArea(
        "other_supernaturals",
        "Autres créatures du Monde des Ténèbres",
        ("paris_vampire",),
        False,
        "indexed",
        "futures factions/menaces non vampiriques",
        note="Mages, Garous, Changelins, morts et humains sont indexés mais hors priorité du noyau vampirique actuel.",
    ),
    CorpusArea(
        "character_chronologies",
        "Chronologies individuelles des personnages",
        ("paris_vampire",),
        True,
        "indexed",
        "LoreFact valid_from/valid_to / conflicts",
        note="Nécessaire pour traverser les siècles sans conserver des rôles obsolètes.",
    ),
    CorpusArea(
        "office_chronologies",
        "Chronologies des détenteurs d'offices",
        ("paris_vampire",),
        False,
        "indexed",
        "office history / long chronicle",
        modern_only_guard=True,
        note="Bourgmestres, Archontes et Primogènes sont principalement utiles aux périodes postérieures ; leur apparition doit rester datée.",
    ),
    CorpusArea(
        "npc_presence_chronology",
        "Chronologie de présence des PNJ",
        ("paris_vampire",),
        True,
        "indexed",
        "ParisPresence temporelle / roster par date",
        note="Doit devenir le garde-fou principal contre les PNJ anachroniques lors des ellipses longues.",
    ),
    CorpusArea(
        "sun_calendar",
        "Horaires du soleil, saisons et contraintes calendaires",
        ("paris_vampire",),
        False,
        "indexed",
        "chronicle time / futures contraintes nocturnes",
        note="Pas nécessaire à V0.47, mais explicitement conservé dans le contrat de corpus.",
    ),
    CorpusArea(
        "story_seeds",
        "Amorces, scénarios et matière de chronique",
        ("paris_vampire", "idees_scenarii"),
        False,
        "indexed",
        "story hooks",
        modern_only_guard=True,
        note="Réservoir d'inspiration uniquement ; une amorce n'est jamais une preuve canonique.",
    ),
)


REQUIRED_AREA_IDS = frozenset(
    {
        "history_timeline",
        "mortal_history",
        "characters",
        "lineages",
        "clans",
        "presence_location",
        "anarchs",
        "sabbat",
        "camarilla_institutions",
        "offices_power",
        "praxis_succession",
        "factions_coteries",
        "relationships",
        "prestations",
        "blood_bonds",
        "mortal_influences",
        "domains_territory",
        "historical_geography",
        "elysium_court_customs",
        "secrets_information",
        "events_incidents",
        "external_powers",
        "other_supernaturals",
        "character_chronologies",
        "office_chronologies",
        "npc_presence_chronology",
        "sun_calendar",
        "story_seeds",
    }
)


def coverage_area(area_id: str) -> CorpusArea:
    for area in PARIS_CORPUS_AREAS:
        if area.id == area_id:
            return area
    raise ValueError(f"Unknown Paris corpus area: {area_id}")


def validate_paris_coverage(areas: Iterable[CorpusArea] | None = None) -> None:
    selected = tuple(areas or PARIS_CORPUS_AREAS)
    ids = [area.id for area in selected]
    if len(ids) != len(set(ids)):
        raise ValueError("Paris coverage area ids must be unique")
    missing_ids = REQUIRED_AREA_IDS - set(ids)
    if missing_ids:
        raise ValueError("Missing mandatory Paris coverage areas: " + ", ".join(sorted(missing_ids)))
    for area in selected:
        if area.coverage_status not in COVERAGE_STATUSES:
            raise ValueError(f"Unsupported coverage status for {area.id}: {area.coverage_status}")
        if not area.source_keys:
            raise ValueError(f"Coverage area has no source anchor: {area.id}")
        for source_key in area.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for coverage area {area.id}")
        if not area.engine_target.strip():
            raise ValueError(f"Coverage area has no engine target: {area.id}")


def coverage_report() -> dict[str, int]:
    validate_paris_coverage()
    values = PARIS_CORPUS_AREAS
    priority = tuple(area for area in values if area.priority_1435)
    incomplete_priority = tuple(area for area in priority if area.coverage_status != "structured")
    return {
        "areas_total": len(values),
        "structured": sum(area.coverage_status == "structured" for area in values),
        "partial": sum(area.coverage_status == "partial" for area in values),
        "indexed": sum(area.coverage_status == "indexed" for area in values),
        "missing": sum(area.coverage_status == "missing" for area in values),
        "priority_1435_total": len(priority),
        "priority_1435_structured": sum(area.coverage_status == "structured" for area in priority),
        "priority_1435_incomplete": len(incomplete_priority),
    }
