from __future__ import annotations

from dataclasses import dataclass

from .lore_catalog import PARIS_CORPUS_SOURCES
from .paris_lore import PARIS_1435_FACTIONS, PARIS_1435_NPCS


ROSTER_KINDS = {"named_vampire", "collective"}
ROSTER_STATUSES = {"present", "external", "absent", "historical", "unverified"}
ROSTER_CERTAINTIES = {"certain", "high", "medium", "low", "contested"}
SIMULATION_POLICIES = {"active_named", "context_only", "forbidden"}


@dataclass(frozen=True)
class Paris1435RosterEntry:
    id: str
    label: str
    kind: str
    clan_id: str | None
    status: str
    location: str
    certainty: str
    source_keys: tuple[str, ...]
    simulation_policy: str = "context_only"
    note: str = ""

    @property
    def can_act_as_named_npc(self) -> bool:
        return self.kind == "named_vampire" and self.simulation_policy == "active_named"


@dataclass(frozen=True)
class Paris1435FactionRoster:
    faction_id: str
    label: str
    member_entry_ids: tuple[str, ...]
    certainty: str
    source_keys: tuple[str, ...]
    note: str = ""


@dataclass(frozen=True)
class RosterConflict:
    id: str
    title: str
    source_keys: tuple[str, ...]
    claims: tuple[str, ...]
    preferred_interpretation: str | None = None
    note: str = ""


def _named(
    id: str,
    label: str,
    clan_id: str | None,
    status: str,
    location: str,
    certainty: str,
    source_keys: tuple[str, ...],
    policy: str,
    note: str = "",
) -> Paris1435RosterEntry:
    return Paris1435RosterEntry(
        id=id,
        label=label,
        kind="named_vampire",
        clan_id=clan_id,
        status=status,
        location=location,
        certainty=certainty,
        source_keys=source_keys,
        simulation_policy=policy,
        note=note,
    )


def _collective(
    id: str,
    label: str,
    clan_id: str,
    status: str,
    location: str,
    certainty: str,
    source_keys: tuple[str, ...],
    policy: str = "context_only",
    note: str = "",
) -> Paris1435RosterEntry:
    return Paris1435RosterEntry(
        id=id,
        label=label,
        kind="collective",
        clan_id=clan_id,
        status=status,
        location=location,
        certainty=certainty,
        source_keys=source_keys,
        simulation_policy=policy,
        note=note,
    )


# The eight active_named entries deliberately mirror the historical NPC seed.
# A character can be historically interesting without being eligible for runtime
# injection in 1435.
NAMED_ROSTER: tuple[Paris1435RosterEntry, ...] = (
    _named(
        "npc_alexandre", "Alexandre", "ventrue", "present", "Paris", "certain",
        ("alexandre", "alexandre_pouvoir", "chronologie"), "active_named",
        "Prince reconnu mais pouvoir effectif contesté en 1435.",
    ),
    _named(
        "npc_saviarre", "Saviarre", "ventrue", "present", "Paris", "high",
        ("alexandre", "alexandre_pouvoir", "lignees_ventrue"), "active_named",
        "Conseillère et infante d'Alexandre dans la continuité retenue.",
    ),
    _named(
        "npc_beatrix", "Béatrix", "toreador", "present", "Paris", "high",
        ("beatrix", "alexandre_pouvoir"), "active_named",
    ),
    _named(
        "npc_villon", "François Villon", "toreador", "present", "Paris", "high",
        ("francois_villon", "chronologie"), "active_named",
    ),
    _named(
        "npc_violetta", "Violetta", "toreador", "present", "Paris", "medium",
        ("violetta", "alexandre_pouvoir"), "active_named",
        "Présence cohérente avec la continuité retenue, mais preuve ponctuelle 1435 moins directe.",
    ),
    _named(
        "npc_magnerius", "Magnerius de Sens", "ventrue", "present",
        "Paris / réseau français d'Alexandre", "medium",
        ("magnerius", "alexandre_pouvoir", "chronologie"), "active_named",
        "Réseau fidèle solide ; localisation exacte pendant toute l'année 1435 moins directe.",
    ),
    _named(
        "npc_pompignan", "Pierre Emmanuel de Pompignan", "ventrue", "present",
        "Paris / réseau français d'Alexandre", "medium",
        ("pompignan", "alexandre_pouvoir", "chronologie"), "active_named",
        "Présence conservée prudemment ; contradiction documentée autour de sa torpeur en 1481.",
    ),
    _named(
        "npc_henri_preux", "Henri le Preux", "ventrue", "external", "Bourges", "high",
        ("henri_preux", "alexandre_pouvoir", "chronologie"), "active_named",
        "Acteur extérieur du réseau français, jamais traité comme résident parisien.",
    ),
    _named(
        "npc_childeberd", "Childeberd", "brujah", "unverified", "Paris ?", "low",
        ("principaux_clans_an_mil", "chronologie"), "forbidden",
        "Rôle confirmé en 1148 ; survie et présence 1435 non établies.",
    ),
    _named(
        "npc_mithras", "Mithras", "ventrue", "external", "Londres / réseaux anglais", "high",
        ("alexandre_pouvoir", "chronologie"), "context_only",
        "Puissance extérieure liée aux offensives contre Alexandre, pas résident parisien.",
    ),
    _named(
        "npc_anne_bourgogne", "Anne de Bourgogne", None, "historical", "Réseau bourguignon", "medium",
        ("chronologie",), "forbidden",
        "Prince vampire influente en 1392 ; activité personnelle exacte en 1435 non démontrée.",
    ),
    _named(
        "npc_louis_orleans", "Louis d'Orléans", None, "historical", "Réseau d'Orléans", "high",
        ("chronologie",), "forbidden",
        "Prince vampire influent en 1392 ; statut personnel exact en 1435 non établi.",
    ),
    _named(
        "npc_henri_orleans", "Henri d'Orléans", None, "unverified", "Réseau d'Orléans", "medium",
        ("chronologie",), "forbidden",
        "Allié d'Alexandre après 1407 ; activité exacte en 1435 à confirmer.",
    ),
    _named(
        "npc_helene", "Hélène", "toreador", "unverified", "Localisation 1435 inconnue", "medium",
        ("francois_villon",), "forbidden",
        "Sire de Villon ; le lien de lignée ne prouve pas une résidence parisienne en 1435.",
    ),
)


# Collective entries are first-class roster data. They allow a clan/faction to
# exist politically without fabricating a leader when the exact individual roster
# is not documented.
COLLECTIVE_ROSTER: tuple[Paris1435RosterEntry, ...] = (
    _collective(
        "collective_ventrue_paris", "Ventrue de Paris", "ventrue", "present",
        "Paris et réseau princier", "certain", ("alexandre", "alexandre_pouvoir", "lignees_ventrue"),
    ),
    _collective(
        "collective_toreador_paris", "Toréador de Paris", "toreador", "present", "Paris", "high",
        ("alexandre_pouvoir", "beatrix", "francois_villon", "violetta"),
    ),
    _collective(
        "collective_brujah_paris", "Brujah de Paris", "brujah", "present",
        "Paris / Cour des Miracles", "high", ("alexandre_pouvoir", "chronologie"),
        note="Alexandre renforce les Brujah en 1407 ; ils participent au contre-pouvoir des Miracles.",
    ),
    _collective(
        "collective_malkavian_paris", "Malkaviens de Paris", "malkavian", "present",
        "Paris / Cour des Miracles", "high", ("alexandre_pouvoir",),
    ),
    _collective(
        "collective_gangrel_paris", "Gangrels de Paris", "gangrel", "present",
        "Paris / Cour des Miracles", "high", ("alexandre_pouvoir", "chronologie"),
        note="Réconciliation de principe avec Alexandre après 1407 puis présence dans le contre-pouvoir.",
    ),
    _collective(
        "collective_nosferatu_paris", "Nosferatus de Paris", "nosferatu", "present",
        "Paris / Cour des Miracles", "high", ("alexandre_pouvoir",),
    ),
    _collective(
        "collective_tremere_paris", "Tremeres de Paris", "tremere", "unverified", "Paris ?", "medium",
        ("chronologie", "alexandre_pouvoir", "paris_tremere"),
        note=(
            "Implantation ancienne et revers de 1307 établis ; la page de clan confirme une histoire parisienne "
            "ancienne mais ne suffit pas à démontrer une présence continue exactement en 1435."
        ),
    ),
    _collective(
        "collective_gargoyle_paris", "Gargouilles de Paris", "gargoyle", "present",
        "Paris / service des Magi Tremeres", "high", ("paris_gargouille", "chronologie"),
        note="La page indique une présence continue de deux ou trois Gargouilles depuis Goratrix.",
    ),
    _collective(
        "collective_lasombra_paris", "Lasombra de Paris", "lasombra", "absent",
        "Hors de la capitale", "high", ("chronologie",), "forbidden",
        "Tous les Lasombra sont chassés de la capitale en 1226 ; aucune réinstallation pré-1435 auditée.",
    ),
)


PARIS_1435_ROSTER: tuple[Paris1435RosterEntry, ...] = NAMED_ROSTER + COLLECTIVE_ROSTER
ROSTER_BY_ID = {entry.id: entry for entry in PARIS_1435_ROSTER}


PARIS_1435_FACTION_ROSTER: tuple[Paris1435FactionRoster, ...] = (
    Paris1435FactionRoster(
        "faction_princely_court",
        "Cour fidèle d'Alexandre",
        ("npc_alexandre", "npc_saviarre", "npc_magnerius", "npc_pompignan"),
        "high",
        ("alexandre_pouvoir", "chronologie"),
    ),
    Paris1435FactionRoster(
        "faction_toreador_paris",
        "Réseaux toréador parisiens",
        ("npc_beatrix", "npc_villon", "npc_violetta"),
        "high",
        ("alexandre_pouvoir", "beatrix", "francois_villon", "violetta"),
    ),
    Paris1435FactionRoster(
        "faction_court_miracles",
        "Cour des Miracles",
        (
            "collective_brujah_paris",
            "collective_malkavian_paris",
            "collective_gangrel_paris",
            "collective_nosferatu_paris",
        ),
        "high",
        ("alexandre_pouvoir",),
        "Clans composants sourcés ; aucun dirigeant nommé n'est inventé.",
    ),
)


ROSTER_CONFLICTS: tuple[RosterConflict, ...] = (
    RosterConflict(
        "pompignan_torpor_vs_1481",
        "Torpeur de Pierre Emmanuel de Pompignan et activité autour de 1481",
        ("pompignan", "chronologie"),
        (
            "La fiche personnelle le fait tomber en torpeur puis se réveiller vingt ans après la mort d'Alexandre.",
            "La chronologie générale le place parmi les Ventrue provinciaux impliqués dans la succession de 1481.",
        ),
        None,
        "Aucune version n'est effacée ; son activité de 1481 ne doit pas être traitée comme certaine.",
    ),
)


OPEN_ROSTER_GAPS: tuple[str, ...] = (
    "Aucun membre Brujah de la Cour des Miracles n'est nommé avec une preuve spécifique à 1435.",
    "Aucun membre Malkavien de la Cour des Miracles n'est nommé avec une preuve spécifique à 1435.",
    "Aucun membre Gangrel de la Cour des Miracles n'est nommé avec une preuve spécifique à 1435.",
    "Aucun membre Nosferatu de la Cour des Miracles n'est nommé avec une preuve spécifique à 1435.",
    "La présence et le roster individuel Tremere en 1435 restent à confirmer après le revers de 1307.",
    "Les Gargouilles sont attestées collectivement, mais aucun individu parisien de 1435 n'est identifié avec certitude.",
    "Le statut exact en 1435 de Louis d'Orléans, Anne de Bourgogne, Henri d'Orléans et Childeberd reste à établir.",
    "La localisation exacte de Magnerius et Pompignan pendant toute l'année 1435 reste moins directe que leur réseau politique.",
)


def roster_entry(entry_id: str) -> Paris1435RosterEntry:
    try:
        return ROSTER_BY_ID[entry_id]
    except KeyError as exc:
        raise ValueError(f"Unknown Paris 1435 roster entry: {entry_id}") from exc


def validate_paris_1435_roster() -> None:
    ids = [entry.id for entry in PARIS_1435_ROSTER]
    if len(ids) != len(set(ids)):
        raise ValueError("Paris 1435 roster ids must be unique")

    for entry in PARIS_1435_ROSTER:
        if entry.kind not in ROSTER_KINDS:
            raise ValueError(f"Unsupported roster kind: {entry.id}")
        if entry.status not in ROSTER_STATUSES:
            raise ValueError(f"Unsupported roster status: {entry.id}")
        if entry.certainty not in ROSTER_CERTAINTIES:
            raise ValueError(f"Unsupported roster certainty: {entry.id}")
        if entry.simulation_policy not in SIMULATION_POLICIES:
            raise ValueError(f"Unsupported simulation policy: {entry.id}")
        if not entry.source_keys:
            raise ValueError(f"Roster entry has no source: {entry.id}")
        for source_key in entry.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for roster entry {entry.id}")
        if entry.simulation_policy == "active_named":
            if entry.kind != "named_vampire":
                raise ValueError(f"Only named vampires can be active NPCs: {entry.id}")
            if entry.status not in {"present", "external"}:
                raise ValueError(f"Unavailable actor cannot be active in simulation: {entry.id}")
        if entry.status in {"absent", "unverified", "historical"} and entry.simulation_policy == "active_named":
            raise ValueError(f"Unsafe active roster entry: {entry.id}")

    active_seed_ids = {seed.id for seed in PARIS_1435_NPCS}
    audited_active_ids = {entry.id for entry in NAMED_ROSTER if entry.simulation_policy == "active_named"}
    if active_seed_ids != audited_active_ids:
        raise ValueError(
            "Simulation seed/roster mismatch; "
            f"missing={sorted(active_seed_ids - audited_active_ids)}, "
            f"extra={sorted(audited_active_ids - active_seed_ids)}"
        )

    seed_by_id = {seed.id: seed for seed in PARIS_1435_NPCS}
    for actor_id in active_seed_ids:
        seed = seed_by_id[actor_id]
        entry = ROSTER_BY_ID[actor_id]
        expected_status = "present" if seed.location_1435 == "Paris" else "external"
        if entry.status != expected_status:
            raise ValueError(f"Seed location is incompatible with roster status: {actor_id}")
        if entry.certainty not in {"certain", "high", "medium"}:
            raise ValueError(f"Active seed certainty is too low: {actor_id}")

    faction_seed_ids = {faction.id for faction in PARIS_1435_FACTIONS}
    faction_roster_ids = {faction.faction_id for faction in PARIS_1435_FACTION_ROSTER}
    if faction_seed_ids != faction_roster_ids:
        raise ValueError("Faction seed/roster mismatch")

    for faction in PARIS_1435_FACTION_ROSTER:
        if faction.certainty not in ROSTER_CERTAINTIES:
            raise ValueError(f"Unsupported faction certainty: {faction.faction_id}")
        for source_key in faction.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for faction {faction.faction_id}")
        for member_id in faction.member_entry_ids:
            if member_id not in ROSTER_BY_ID:
                raise ValueError(f"Unknown roster member {member_id} in {faction.faction_id}")

    miracles = next(item for item in PARIS_1435_FACTION_ROSTER if item.faction_id == "faction_court_miracles")
    miracle_members = tuple(ROSTER_BY_ID[member_id] for member_id in miracles.member_entry_ids)
    if {item.clan_id for item in miracle_members} != {"brujah", "malkavian", "gangrel", "nosferatu"}:
        raise ValueError("Court of Miracles collective clan roster is incomplete")
    if any(item.kind != "collective" or item.status != "present" for item in miracle_members):
        raise ValueError("Court of Miracles must use confirmed collective entries")

    for conflict in ROSTER_CONFLICTS:
        if len(conflict.claims) < 2:
            raise ValueError(f"Roster conflict needs at least two claims: {conflict.id}")
        for source_key in conflict.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for roster conflict {conflict.id}")


def roster_audit_report() -> dict[str, int]:
    validate_paris_1435_roster()
    return {
        "entries_total": len(PARIS_1435_ROSTER),
        "named_total": len(NAMED_ROSTER),
        "named_present": sum(entry.status == "present" for entry in NAMED_ROSTER),
        "named_external": sum(entry.status == "external" for entry in NAMED_ROSTER),
        "named_unverified": sum(entry.status == "unverified" for entry in NAMED_ROSTER),
        "named_historical": sum(entry.status == "historical" for entry in NAMED_ROSTER),
        "collective_total": len(COLLECTIVE_ROSTER),
        "collective_present": sum(entry.status == "present" for entry in COLLECTIVE_ROSTER),
        "collective_absent": sum(entry.status == "absent" for entry in COLLECTIVE_ROSTER),
        "collective_unverified": sum(entry.status == "unverified" for entry in COLLECTIVE_ROSTER),
        "simulation_active_named": sum(entry.simulation_policy == "active_named" for entry in NAMED_ROSTER),
        "factions": len(PARIS_1435_FACTION_ROSTER),
        "roster_conflicts": len(ROSTER_CONFLICTS),
        "open_gaps": len(OPEN_ROSTER_GAPS),
    }
