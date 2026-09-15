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
    """Audited availability of one named actor or collective in Paris 1435.

    A collective entry is intentionally allowed. It lets the Chronicle represent
    a clan/faction that is certainly present without inventing a leader or named
    member when the source does not provide one for the exact date.
    """

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


# Named actors already used by the simulation. Exact physical presence is less
# certain for some provincial Ventrue than their membership in Alexandre's wider
# political network; this is represented by certainty rather than invented facts.
NAMED_ROSTER: tuple[Paris1435RosterEntry, ...] = (
    Paris1435RosterEntry(
        "npc_alexandre",
        "Alexandre",
        "named_vampire",
        "ventrue",
        "present",
        "Paris",
        "certain",
        ("alexandre", "alexandre_pouvoir", "chronologie"),
        "active_named",
        "Prince reconnu mais pouvoir effectif contesté en 1435.",
    ),
    Paris1435RosterEntry(
        "npc_saviarre",
        "Saviarre",
        "named_vampire",
        "ventrue",
        "present",
        "Paris",
        "high",
        ("alexandre", "alexandre_pouvoir", "lignees_ventrue"),
        "active_named",
        "Conseillère et infante d'Alexandre dans la continuité retenue.",
    ),
    Paris1435RosterEntry(
        "npc_beatrix",
        "Béatrix",
        "named_vampire",
        "toreador",
        "present",
        "Paris",
        "high",
        ("beatrix", "alexandre_pouvoir"),
        "active_named",
    ),
    Paris1435RosterEntry(
        "npc_villon",
        "François Villon",
        "named_vampire",
        "toreador",
        "present",
        "Paris",
        "high",
        ("francois_villon", "chronologie"),
        "active_named",
    ),
    Paris1435RosterEntry(
        "npc_violetta",
        "Violetta",
        "named_vampire",
        "toreador",
        "present",
        "Paris",
        "medium",
        ("violetta", "alexandre_pouvoir"),
        "active_named",
        "La continuité est cohérente avec sa présence, mais la preuve ponctuelle 1435 est moins directe.",
    ),
    Paris1435RosterEntry(
        "npc_magnerius",
        "Magnerius de Sens",
        "named_vampire",
        "ventrue",
        "present",
        "Paris / réseau français d'Alexandre",
        "medium",
        ("magnerius", "alexandre_pouvoir", "chronologie"),
        "active_named",
        "Son appartenance au réseau fidèle est solide ; sa localisation exacte pendant toute l'année 1435 est moins directe.",
    ),
    Paris1435RosterEntry(
        "npc_pompignan",
        "Pierre Emmanuel de Pompignan",
        "named_vampire",
        "ventrue",
        "present",
        "Paris / réseau français d'Alexandre",
        "medium",
        ("pompignan", "alexandre_pouvoir", "chronologie"),
        "active_named",
        "Présence 1435 conservée prudemment ; sa fiche personnelle et la chronologie générale divergent sur sa torpeur autour de 1481.",
    ),
    Paris1435RosterEntry(
        "npc_henri_preux",
        "Henri le Preux",
        "named_vampire",
        "ventrue",
        "external",
        "Bourges",
        "high",
        ("henri_preux", "alexandre_pouvoir", "chronologie"),
        "active_named",
        "Acteur extérieur du réseau français ; il peut agir politiquement mais n'est pas un résident parisien.",
    ),
    Paris1435RosterEntry(
        "npc_childeberd",
        "Childeberd",
        "named_vampire",
        "brujah",
        "unverified",
        "Paris ?",
        "low",
        ("principaux_clans_an_mil", "chronologie"),
        "forbidden",
        "Rôle documenté en 1148 ; aucune preuve auditée ne suffit encore à confirmer survie et présence en 1435.",
    ),
    Paris1435RosterEntry(
        "npc_mithras",
        "Mithras",
        "named_vampire",
        "ventrue",
        "external",
        "Londres / réseaux anglais et français",
        "high",
        ("alexandre_pouvoir", "chronologie"),
        "context_only",
        "Puissance extérieure pesant sur Paris ; ne doit pas être traité comme résident.",
    ),
    Paris1435RosterEntry(
        "npc_anne_bourgogne",
        "Anne de Bourgogne",
        "named_vampire",
        None,
        "external",
        "Réseau bourguignon",
        "medium",
        ("alexandre_pouvoir",),
        "context_only",
        "Prince vampirique extérieure citée comme influence majeure ; aucun clan n'est inventé.",
    ),
    Paris1435RosterEntry(
        "npc_louis_orleans",
        "Louis d'Orléans",
        "named_vampire",
        None,
        "historical",
        "Réseau d'Orléans",
        "high",
        ("alexandre_pouvoir",),
        "forbidden",
        "Influence extérieure explicitement attestée en 1392 ; son statut personnel exact en 1435 n'est pas établi.",
    ),
    Paris1435RosterEntry(
        "npc_henri_orleans",
        "Henri d'Orléans",
        "named_vampire",
        None,
        "unverified",
        "Réseau d'Orléans",
        "medium",
        ("alexandre_pouvoir",),
        "forbidden",
        "Allié d'Alexandre dans la recomposition postérieure à 1407 ; présence/activité exacte en 1435 à confirmer.",
    ),
    Paris1435RosterEntry(
        "npc_helene",
        "Hélène",
        "named_vampire",
        "toreador",
        "unverified",
        "Hors de Paris / localisation 1435 inconnue",
        "medium",
        ("francois_villon",),
        "forbidden",
        "Sire de Villon ; elle l'abandonne immédiatement après son Étreinte, sans preuve de résidence parisienne en 1435.",
    ),
)


# Collective presence is the safe default when sources establish a clan in Paris
# but do not provide a reliable named roster for 1435.
COLLECTIVE_ROSTER: tuple[Paris1435RosterEntry, ...] = (
    Paris1435RosterEntry(
        "collective_ventrue_paris",
        "Ventrue de Paris",
        "collective",
        "ventrue",
        "present",
        "Paris et réseau princier",
        "certain",
        ("alexandre", "alexandre_pouvoir", "lignees_ventrue"),
        "context_only",
    ),
    Paris1435RosterEntry(
        "collective_toreador_paris",
        "Toréador de Paris",
        "collective",
        "toreador",
        "present",
        "Paris",
        "high",
        ("alexandre_pouvoir", "beatrix", "francois_villon", "violetta"),
        "context_only",
    ),
    Paris1435RosterEntry(
        "collective_brujah_paris",
        "Brujah de Paris",
        "collective",
        "brujah",
        "present",
        "Paris / Cour des Miracles",
        "high",
        ("alexandre_pouvoir", "chronologie"),
        "context_only",
        "Le clan est explicitement renforcé par Alexandre après 1407 puis représenté dans la Cour des Miracles.",
    ),
    Paris1435RosterEntry(
        "collective_malkavian_paris",
        "Malkaviens de Paris",
        "collective",
        "malkavian",
        "present",
        "Paris / Cour des Miracles",
        "high",
        ("alexandre_pouvoir",),
        "context_only",
    ),
    Paris1435RosterEntry(
        "collective_gangrel_paris",
        "Gangrels de Paris",
        "collective",
        "gangrel",
        "present",
        "Paris / Cour des Miracles",
        "high",
        ("alexandre_pouvoir", "chronologie"),
        "context_only",
        "Alexandre se réconcilie avec les Gangrels après 1407 ; le clan participe ensuite au contre-pouvoir de la Cour des Miracles.",
    ),
    Paris1435RosterEntry(
        "collective_nosferatu_paris",
        "Nosferatus de Paris",
        "collective",
        "nosferatu",
        "present",
        "Paris / Cour des Miracles",
        "high",
        ("alexandre_pouvoir",),
        "context_only",
    ),
    Paris1435RosterEntry(
        "collective_tremere_paris",
        "Tremeres de Paris",
        "collective",
        "tremere",
        "present",
        "Paris",
        "medium",
        ("chronologie", "alexandre_pouvoir", "paris_tremere"),
        "context_only",
        "Implantation ancienne, revers majeur en 1307 puis continuité d'un clan parisien ; les individus et la puissance exacte en 1435 restent inconnus.",
    ),
    Paris1435RosterEntry(
        "collective_gargoyle_paris",
        "Gargouilles de Paris",
        "collective",
        "gargoyle",
        "present",
        "Paris / service des Magi Tremeres",
        "high",
        ("paris_gargouille", "chronologie"),
        "context_only",
        "Paris by Night indique une présence continue de deux ou trois Gargouilles depuis la prise de fonction de Goratrix.",
    ),
    Paris1435RosterEntry(
        "collective_lasombra_paris",
        "Lasombra de Paris",
        "collective",
        "lasombra",
        "absent",
        "Hors de la capitale",
        "high",
        ("chronologie",),
        "forbidden",
        "La chronologie indique l'expulsion de tous les Lasombra de la capitale en 1226 ; aucune réinstallation antérieure à 1435 n'est actuellement auditée.",
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
        "Les clans membres sont sourcés ; aucun chef ou membre individuel n'est inventé pour remplir le roster.",
    ),
)


ROSTER_CONFLICTS: tuple[RosterConflict, ...] = (
    RosterConflict(
        "pompignan_torpor_vs_1481",
        "Torpeur de Pierre Emmanuel de Pompignan et activité autour de 1481",
        ("pompignan", "chronologie"),
        (
            "La fiche personnelle indique qu'il tombe en torpeur et se réveille vingt ans après la mort d'Alexandre.",
            "La chronologie générale le place parmi les Ventrue provinciaux impliqués dans la succession ouverte en 1481.",
        ),
        None,
        "Aucune version n'est effacée. Le conflit n'empêche pas à lui seul une présence en 1435, mais interdit de traiter son activité de 1481 comme certaine.",
    ),
)


OPEN_ROSTER_GAPS: tuple[str, ...] = (
    "Aucun membre Brujah de la Cour des Miracles n'est encore nommé avec une preuve spécifique à 1435.",
    "Aucun membre Malkavien de la Cour des Miracles n'est encore nommé avec une preuve spécifique à 1435.",
    "Aucun membre Gangrel de la Cour des Miracles n'est encore nommé avec une preuve spécifique à 1435.",
    "Aucun membre Nosferatu de la Cour des Miracles n'est encore nommé avec une preuve spécifique à 1435.",
    "Le roster individuel Tremere de 1435 reste inconnu malgré une continuité collective suffisamment étayée.",
    "Les Gargouilles sont attestées collectivement, mais aucun individu parisien de 1435 n'est identifié avec certitude.",
    "Le statut exact en 1435 de Louis d'Orléans, Henri d'Orléans et Childeberd reste à établir.",
    "La localisation exacte de Magnerius et de Pompignan pendant toute l'année 1435 reste moins directe que leur appartenance au réseau d'Alexandre.",
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
        if entry.simulation_policy == "active_named" and entry.kind != "named_vampire":
            raise ValueError(f"Only named vampires can be active NPCs: {entry.id}")
        if entry.simulation_policy == "active_named" and entry.status not in {"present", "external"}:
            raise ValueError(f"Unavailable actor cannot be active in simulation: {entry.id}")
        if entry.status in {"absent", "unverified", "historical"} and entry.simulation_policy == "active_named":
            raise ValueError(f"Unsafe active roster entry: {entry.id}")

    active_seed_ids = {seed.id for seed in PARIS_1435_NPCS}
    audited_active_ids = {entry.id for entry in NAMED_ROSTER if entry.simulation_policy == "active_named"}
    if active_seed_ids != audited_active_ids:
        missing = sorted(active_seed_ids - audited_active_ids)
        extra = sorted(audited_active_ids - active_seed_ids)
        raise ValueError(f"Simulation seed/roster mismatch; missing={missing}, extra={extra}")

    seed_by_id = {seed.id: seed for seed in PARIS_1435_NPCS}
    for actor_id in active_seed_ids:
        seed = seed_by_id[actor_id]
        entry = ROSTER_BY_ID[actor_id]
        if seed.location_1435 == "Paris" and entry.status != "present":
            raise ValueError(f"Local seed is not audited present: {actor_id}")
        if seed.location_1435 != "Paris" and entry.status != "external":
            raise ValueError(f"External seed is not audited external: {actor_id}")
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
    miracle_clans = {ROSTER_BY_ID[member_id].clan_id for member_id in miracles.member_entry_ids}
    if miracle_clans != {"brujah", "malkavian", "gangrel", "nosferatu"}:
        raise ValueError("Court of Miracles collective clan roster is incomplete")
    if any(ROSTER_BY_ID[member_id].status != "present" for member_id in miracles.member_entry_ids):
        raise ValueError("Court of Miracles contains a collective not audited present in 1435")

    for conflict in ROSTER_CONFLICTS:
        if not conflict.source_keys:
            raise ValueError(f"Roster conflict has no source: {conflict.id}")
        for source_key in conflict.source_keys:
            if source_key not in PARIS_CORPUS_SOURCES:
                raise ValueError(f"Unknown source {source_key} for roster conflict {conflict.id}")
        if len(conflict.claims) < 2:
            raise ValueError(f"Roster conflict needs at least two claims: {conflict.id}")


def roster_audit_report() -> dict[str, int]:
    validate_paris_1435_roster()
    named = NAMED_ROSTER
    collectives = COLLECTIVE_ROSTER
    return {
        "entries_total": len(PARIS_1435_ROSTER),
        "named_total": len(named),
        "named_present": sum(entry.status == "present" for entry in named),
        "named_external": sum(entry.status == "external" for entry in named),
        "named_unverified": sum(entry.status == "unverified" for entry in named),
        "named_historical": sum(entry.status == "historical" for entry in named),
        "collective_total": len(collectives),
        "collective_present": sum(entry.status == "present" for entry in collectives),
        "collective_absent": sum(entry.status == "absent" for entry in collectives),
        "collective_unverified": sum(entry.status == "unverified" for entry in collectives),
        "simulation_active_named": sum(entry.simulation_policy == "active_named" for entry in named),
        "factions": len(PARIS_1435_FACTION_ROSTER),
        "roster_conflicts": len(ROSTER_CONFLICTS),
        "open_gaps": len(OPEN_ROSTER_GAPS),
    }
