from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .lore_catalog import PARIS_CORPUS_SOURCES, SOURCE_TIERS


FACT_CERTAINTIES = {"certain", "high", "medium", "low", "contested"}
PRESENCE_STATUSES = {"present", "external", "historical", "unverified"}


@dataclass(frozen=True)
class LoreEntity:
    id: str
    name: str
    entity_type: str
    aliases: tuple[str, ...] = ()


@dataclass(frozen=True)
class LoreFact:
    id: str
    subject_id: str
    predicate: str
    value: str | int | float | bool
    source_keys: tuple[str, ...]
    tier: str
    certainty: str = "certain"
    valid_from: int | None = None
    valid_to: int | None = None
    reference_only: bool = False
    note: str = ""
    conflict_group: str | None = None

    def applies_in(self, year: int) -> bool:
        if self.valid_from is not None and year < self.valid_from:
            return False
        if self.valid_to is not None and year > self.valid_to:
            return False
        return True


@dataclass(frozen=True)
class LoreConflict:
    id: str
    title: str
    fact_ids: tuple[str, ...]
    preferred_fact_id: str | None
    reason: str


@dataclass(frozen=True)
class ParisPresence:
    entity_id: str
    status_1435: str
    location_1435: str
    certainty: str
    source_keys: tuple[str, ...]
    note: str = ""
    inject_into_simulation: bool = False


@dataclass(frozen=True)
class ParisFactionPresence:
    id: str
    name: str
    status_1435: str
    member_ids: tuple[str, ...]
    member_clans: tuple[str, ...]
    source_keys: tuple[str, ...]
    certainty: str = "high"
    note: str = ""


ENTITIES: tuple[LoreEntity, ...] = (
    LoreEntity("npc_alexandre", "Alexandre", "vampire"),
    LoreEntity("npc_saviarre", "Saviarre", "vampire", aliases=("Saviarre d'Auvergne",)),
    LoreEntity("npc_beatrix", "Béatrix", "vampire", aliases=("Beatrix",)),
    LoreEntity("npc_villon", "François Villon", "vampire"),
    LoreEntity("npc_violetta", "Violetta", "vampire"),
    LoreEntity("npc_magnerius", "Magnerius de Sens", "vampire"),
    LoreEntity("npc_henri_preux", "Henri le Preux", "vampire"),
    LoreEntity("npc_pompignan", "Pierre Emmanuel de Pompignan", "vampire", aliases=("Pierre-Emmanuel de Pompignan",)),
    LoreEntity("npc_childeberd", "Childeberd", "vampire"),
    LoreEntity("npc_mithras", "Mithras", "vampire"),
    LoreEntity("faction_princely_court", "Cour fidèle d'Alexandre", "faction"),
    LoreEntity("faction_toreador_paris", "Réseaux toréador parisiens", "faction"),
    LoreEntity("faction_court_miracles", "Cour des Miracles", "faction"),
    LoreEntity("collective_tremere_paris", "Tremeres de Paris", "collective"),
    LoreEntity("institution_camarilla", "Camarilla", "institution"),
)

ENTITY_BY_ID = {entity.id: entity for entity in ENTITIES}


FACTS: tuple[LoreFact, ...] = (
    LoreFact(
        "alexandre_clan",
        "npc_alexandre",
        "clan",
        "ventrue",
        ("alexandre",),
        "A",
    ),
    LoreFact(
        "alexandre_generation",
        "npc_alexandre",
        "generation",
        4,
        ("alexandre",),
        "A",
    ),
    LoreFact(
        "alexandre_embrace",
        "npc_alexandre",
        "embraced_year",
        -600,
        ("alexandre",),
        "A",
    ),
    LoreFact(
        "alexandre_prince_dark_ages",
        "npc_alexandre",
        "office",
        "prince_paris",
        ("alexandre", "alexandre_pouvoir"),
        "A",
        valid_from=1198,
        valid_to=1481,
        note="La référence officielle le donne Prince de Paris au début de l'Âge des Ténèbres ; Paris by Night prolonge le règne jusqu'à la crise de 1481.",
    ),
    LoreFact(
        "alexandre_reference_destruction",
        "npc_alexandre",
        "reference_destroyed_year",
        1481,
        ("chronologie", "alexandre_pouvoir"),
        "B",
        reference_only=True,
        note="Pression historique de référence uniquement : la simulation ne force jamais cette destruction.",
    ),
    LoreFact(
        "saviarre_clan",
        "npc_saviarre",
        "clan",
        "ventrue",
        ("lignees_ventrue",),
        "B",
        certainty="high",
    ),
    LoreFact(
        "saviarre_embrace",
        "npc_saviarre",
        "embraced_year",
        481,
        ("lignees_ventrue",),
        "B",
        certainty="high",
    ),
    LoreFact(
        "saviarre_adviser",
        "npc_saviarre",
        "role",
        "conseillere_alexandre",
        ("alexandre", "alexandre_pouvoir"),
        "A",
        valid_from=1000,
        valid_to=1481,
        certainty="high",
        note="Le début de validité est volontairement arrondi au XIe siècle, pas traité comme une date exacte.",
    ),
    LoreFact(
        "saviarre_reference_destruction",
        "npc_saviarre",
        "reference_destroyed_year",
        1481,
        ("chronologie", "alexandre_pouvoir", "lignees_ventrue"),
        "B",
        reference_only=True,
    ),
    LoreFact(
        "magnerius_clan",
        "npc_magnerius",
        "clan",
        "ventrue",
        ("magnerius",),
        "B",
    ),
    LoreFact(
        "magnerius_generation",
        "npc_magnerius",
        "generation",
        6,
        ("magnerius",),
        "B",
    ),
    LoreFact(
        "magnerius_embrace",
        "npc_magnerius",
        "embraced_year",
        987,
        ("magnerius",),
        "B",
    ),
    LoreFact(
        "pompignan_clan",
        "npc_pompignan",
        "clan",
        "ventrue",
        ("pompignan", "lignees_ventrue"),
        "B",
    ),
    LoreFact(
        "pompignan_generation",
        "npc_pompignan",
        "generation",
        6,
        ("pompignan", "lignees_ventrue"),
        "B",
    ),
    LoreFact(
        "pompignan_embrace",
        "npc_pompignan",
        "embraced_year",
        1206,
        ("pompignan", "lignees_ventrue"),
        "B",
    ),
    LoreFact(
        "childeberd_security_1148",
        "npc_childeberd",
        "role",
        "securite_interieure_terres_alexandre",
        ("principaux_clans_an_mil", "chronologie"),
        "B",
        valid_from=1148,
        certainty="high",
        note="Sa survie et sa présence effective en 1435 ne sont pas encore établies ; il n'est donc pas injecté dans la simulation.",
    ),
    LoreFact(
        "tremere_arrival_1133",
        "collective_tremere_paris",
        "historical_event",
        "goratrix_arrive_a_paris",
        ("chronologie",),
        "B",
        valid_from=1133,
        valid_to=1133,
    ),
    LoreFact(
        "tremere_defeat_1307",
        "collective_tremere_paris",
        "historical_event",
        "defaite_liee_au_demantelement_du_temple",
        ("chronologie", "alexandre_pouvoir"),
        "B",
        valid_from=1307,
        valid_to=1307,
    ),
    LoreFact(
        "court_miracles_parallel_power",
        "faction_court_miracles",
        "political_role",
        "contre_pouvoir_parisien",
        ("alexandre_pouvoir",),
        "B",
        valid_from=1420,
        valid_to=1453,
        certainty="high",
        note="Fenêtre de simulation prudente couvrant l'occupation anglaise et la crise de la Cour ; les bornes ne sont pas présentées comme dates canoniques exactes.",
    ),
    LoreFact(
        "court_miracles_member_clans",
        "faction_court_miracles",
        "member_clans",
        "brujah,malkavian,gangrel,nosferatu",
        ("alexandre_pouvoir",),
        "B",
        valid_from=1420,
        valid_to=1453,
        certainty="high",
    ),
    LoreFact(
        "mithras_offensive_1415",
        "npc_mithras",
        "pressure_on_paris",
        "offensive_contre_alexandre",
        ("chronologie", "alexandre_pouvoir"),
        "B",
        valid_from=1415,
        certainty="high",
    ),
    LoreFact(
        "camarilla_announcement_1435",
        "institution_camarilla",
        "announcement_year",
        1435,
        ("chronologie",),
        "B",
        valid_from=1435,
        valid_to=1435,
    ),
    LoreFact(
        "camarilla_effective_pbn_1444",
        "institution_camarilla",
        "effective_year",
        1444,
        ("chronologie",),
        "B",
        certainty="contested",
        conflict_group="camarilla_consolidation_timing",
        note="Date de mise en place effective dans la chronologie Paris by Night.",
    ),
    LoreFact(
        "camarilla_conclave_model_1486",
        "institution_camarilla",
        "first_national_conclave_year",
        1486,
        ("wod_rpg_era_model",),
        "C",
        certainty="contested",
        conflict_group="camarilla_consolidation_timing",
        note="Arbitrage WoD-rpg : 1435 reste l'annonce, 1486 une consolidation transrégionale, 1493 l'institutionnalisation après Thorns.",
    ),
    LoreFact(
        "camarilla_thorns_1493",
        "institution_camarilla",
        "institutional_milestone_year",
        1493,
        ("chronologie", "wod_rpg_era_model"),
        "B",
        valid_from=1493,
        valid_to=1493,
    ),
    LoreFact(
        "violetta_justicar_pbn_early",
        "npc_violetta",
        "office",
        "justicar",
        ("alexandre_pouvoir",),
        "B",
        certainty="contested",
        conflict_group="violetta_justicar_timing",
        note="Alexandre au pouvoir place sa nomination dans le cadre de l'instauration de la Camarilla.",
    ),
    LoreFact(
        "violetta_justicar_1666",
        "npc_violetta",
        "office",
        "justicar",
        ("violetta",),
        "A",
        certainty="contested",
        valid_from=1666,
        conflict_group="violetta_justicar_timing",
        note="La fiche cite Giovanni Chronicles II p.80 et III p.16 pour une élection en 1666.",
    ),
)

FACT_BY_ID = {fact.id: fact for fact in FACTS}


CONFLICTS: tuple[LoreConflict, ...] = (
    LoreConflict(
        id="violetta_justicar_timing",
        title="Date de l'accession de Violetta à la fonction de Justicar",
        fact_ids=("violetta_justicar_pbn_early", "violetta_justicar_1666"),
        preferred_fact_id="violetta_justicar_1666",
        reason=(
            "WoD-rpg privilégie pour l'état de simulation la date 1666 car la fiche Violetta renvoie explicitement "
            "à Giovanni Chronicles II/III. La version Paris by Night reste conservée comme continuité alternative documentée."
        ),
    ),
    LoreConflict(
        id="camarilla_consolidation_timing",
        title="Rythme d'institutionnalisation de la Camarilla",
        fact_ids=("camarilla_effective_pbn_1444", "camarilla_conclave_model_1486"),
        preferred_fact_id="camarilla_conclave_model_1486",
        reason=(
            "La chronologie Paris by Night indique une mise en place effective en 1444, tandis que le modèle WoD-rpg "
            "réserve 1486 à la consolidation transrégionale et 1493 à la forme institutionnelle. Les deux informations "
            "sont conservées afin de ne pas projeter trop tôt les institutions modernes sur Paris 1435."
        ),
    ),
)


PARIS_1435_PRESENCE: tuple[ParisPresence, ...] = (
    ParisPresence("npc_alexandre", "present", "Paris", "certain", ("alexandre", "alexandre_pouvoir", "chronologie"), inject_into_simulation=True),
    ParisPresence("npc_saviarre", "present", "Paris", "high", ("alexandre", "alexandre_pouvoir", "lignees_ventrue"), inject_into_simulation=True),
    ParisPresence("npc_beatrix", "present", "Paris", "high", ("beatrix", "alexandre_pouvoir"), inject_into_simulation=True),
    ParisPresence("npc_villon", "present", "Paris", "high", ("francois_villon", "chronologie"), inject_into_simulation=True),
    ParisPresence("npc_violetta", "present", "Paris", "medium", ("violetta", "alexandre_pouvoir"), note="Présence cohérente avec la continuité retenue, mais l'audit 1435 précis reste moins direct que pour Alexandre ou Béatrix.", inject_into_simulation=True),
    ParisPresence("npc_magnerius", "present", "Paris", "high", ("magnerius", "alexandre_pouvoir"), inject_into_simulation=True),
    ParisPresence("npc_pompignan", "present", "Paris", "high", ("pompignan", "alexandre_pouvoir"), inject_into_simulation=True),
    ParisPresence("npc_henri_preux", "external", "Bourges", "high", ("henri_preux", "alexandre_pouvoir"), inject_into_simulation=True),
    ParisPresence("npc_childeberd", "unverified", "Paris ?", "low", ("principaux_clans_an_mil", "chronologie"), note="Rôle confirmé en 1148 ; aucun fait audité ne suffit encore à confirmer sa survie et sa présence en 1435.", inject_into_simulation=False),
    ParisPresence("npc_mithras", "external", "Londres / réseau français", "high", ("alexandre_pouvoir", "chronologie"), note="Puissance extérieure exerçant une pression sur Paris, pas un résident parisien.", inject_into_simulation=False),
    ParisPresence("collective_tremere_paris", "unverified", "Paris", "medium", ("chronologie", "alexandre_pouvoir", "paris_tremere"), note="Implantation historique et défaite de 1307 établies ; le roster précis de 1435 reste à auditer avant injection.", inject_into_simulation=False),
)


PARIS_1435_FACTION_PRESENCE: tuple[ParisFactionPresence, ...] = (
    ParisFactionPresence(
        "faction_princely_court",
        "Cour fidèle d'Alexandre",
        "active",
        ("npc_alexandre", "npc_saviarre", "npc_magnerius", "npc_pompignan"),
        ("ventrue",),
        ("alexandre_pouvoir", "chronologie"),
    ),
    ParisFactionPresence(
        "faction_toreador_paris",
        "Réseaux toréador parisiens",
        "active",
        ("npc_beatrix", "npc_villon", "npc_violetta"),
        ("toreador",),
        ("alexandre_pouvoir", "beatrix", "francois_villon", "violetta"),
    ),
    ParisFactionPresence(
        "faction_court_miracles",
        "Cour des Miracles",
        "active",
        (),
        ("brujah", "malkavian", "gangrel", "nosferatu"),
        ("alexandre_pouvoir",),
        certainty="high",
        note="Les clans composants sont sourcés ; aucun dirigeant nommé n'est inventé tant que le corpus ne l'établit pas.",
    ),
)


def facts_for(subject_id: str, year: int | None = None) -> tuple[LoreFact, ...]:
    selected = tuple(fact for fact in FACTS if fact.subject_id == subject_id)
    if year is None:
        return selected
    return tuple(fact for fact in selected if fact.applies_in(year))


def presence_for(entity_id: str) -> ParisPresence:
    for presence in PARIS_1435_PRESENCE:
        if presence.entity_id == entity_id:
            return presence
    raise ValueError(f"Unknown Paris 1435 presence entity: {entity_id}")


def validate_paris_corpus() -> None:
    entity_ids = set(ENTITY_BY_ID)
    fact_ids = [fact.id for fact in FACTS]
    if len(fact_ids) != len(set(fact_ids)):
        raise ValueError("Lore fact ids must be unique")

    for fact in FACTS:
        if fact.subject_id not in entity_ids:
            raise ValueError(f"Unknown lore fact subject: {fact.subject_id}")
        if fact.tier not in SOURCE_TIERS:
            raise ValueError(f"Unsupported lore fact tier: {fact.tier}")
        if fact.certainty not in FACT_CERTAINTIES:
            raise ValueError(f"Unsupported lore fact certainty: {fact.certainty}")
        if fact.valid_from is not None and fact.valid_to is not None and fact.valid_from > fact.valid_to:
            raise ValueError(f"Invalid lore fact period: {fact.id}")
        if fact.tier in {"A", "B"} and not fact.source_keys:
            raise ValueError(f"Sourced lore fact has no source: {fact.id}")
        for source_key in fact.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for lore fact {fact.id}")

    for conflict in CONFLICTS:
        for fact_id in conflict.fact_ids:
            if fact_id not in FACT_BY_ID:
                raise ValueError(f"Unknown fact {fact_id} in conflict {conflict.id}")
        if conflict.preferred_fact_id is not None and conflict.preferred_fact_id not in conflict.fact_ids:
            raise ValueError(f"Preferred fact is not part of conflict {conflict.id}")

    for presence in PARIS_1435_PRESENCE:
        if presence.entity_id not in entity_ids:
            raise ValueError(f"Unknown presence entity: {presence.entity_id}")
        if presence.status_1435 not in PRESENCE_STATUSES:
            raise ValueError(f"Unsupported presence status: {presence.status_1435}")
        if presence.certainty not in FACT_CERTAINTIES:
            raise ValueError(f"Unsupported presence certainty: {presence.certainty}")
        for source_key in presence.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for presence {presence.entity_id}")

    for faction in PARIS_1435_FACTION_PRESENCE:
        if faction.id not in entity_ids:
            raise ValueError(f"Unknown faction entity: {faction.id}")
        if faction.certainty not in FACT_CERTAINTIES:
            raise ValueError(f"Unsupported faction certainty: {faction.certainty}")
        for member_id in faction.member_ids:
            if member_id not in entity_ids:
                raise ValueError(f"Unknown faction member {member_id} in {faction.id}")
        for source_key in faction.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for faction {faction.id}")


def paris_1435_audit_report() -> dict[str, int]:
    validate_paris_corpus()
    return {
        "entities": len(ENTITIES),
        "facts": len(FACTS),
        "conflicts": len(CONFLICTS),
        "presence_entries": len(PARIS_1435_PRESENCE),
        "confirmed_or_high_presence": sum(
            presence.status_1435 in {"present", "external"} and presence.certainty in {"certain", "high"}
            for presence in PARIS_1435_PRESENCE
        ),
        "unverified_presence": sum(presence.status_1435 == "unverified" for presence in PARIS_1435_PRESENCE),
        "factions": len(PARIS_1435_FACTION_PRESENCE),
    }
