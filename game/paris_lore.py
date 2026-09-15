from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParisNpcSeed:
    """Backward-compatible aggregate used by the current Paris simulation.

    V0.47a no longer treats ``source_tier`` as the provenance of the whole
    object. Canon facts, dates and contradictions live in ``paris_corpus.py``
    with provenance per fact. The scores, agendas and relations below are
    explicitly WoD-rpg simulation seeds.
    """

    id: str
    name: str
    clan_id: str
    role_1435: str
    ambition_1435: str
    short_goal_1435: str
    loyalty: int
    aggression: int
    influence: float
    status: int
    camarilla_attitude: int
    location_1435: str = "Paris"
    birth_year: int | None = None
    embraced_year: int | None = None
    generation: int | None = None
    sire_id: str | None = None
    source_keys: tuple[str, ...] = ()
    source_tier: str = "B"
    territorial_interest: str = "Paris"
    active_plan: str = ""
    relations: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ParisFactionSeed:
    id: str
    name: str
    agenda_1435: str
    member_ids: tuple[str, ...]
    influence: float
    source_keys: tuple[str, ...]
    source_tier: str = "B"
    member_clans: tuple[str, ...] = ()


@dataclass(frozen=True)
class CanonicalPressure:
    """A future from the reference chronology, never a forced scripted result."""

    id: str
    around_year: int
    title: str
    premise: str
    required_state: tuple[str, ...]
    possible_divergences: tuple[str, ...]
    source_keys: tuple[str, ...]


PARIS_1435_NPCS: tuple[ParisNpcSeed, ...] = (
    ParisNpcSeed(
        id="npc_alexandre",
        name="Alexandre",
        clan_id="ventrue",
        role_1435="Prince de Paris",
        ambition_1435="Rétablir une autorité vampirique effective sur Paris sans abandonner la ville à Mithras ni aux cours rivales",
        short_goal_1435="Maintenir autour de lui une Cour suffisamment cohérente pour survivre à l'occupation anglaise et aux offensives de Mithras",
        loyalty=70,
        aggression=60,
        influence=10.0,
        status=5,
        camarilla_attitude=1,
        source_keys=("alexandre", "alexandre_pouvoir", "chronologie", "lignees_ventrue"),
        source_tier="A",
        territorial_interest="Paris et l'autorité sur les Princes de France",
        active_plan="Réconcilier les forces encore utilisables de sa Cour et empêcher les puissances extérieures de transformer Paris en satellite.",
        relations={"npc_saviarre": 3, "npc_beatrix": 1, "npc_magnerius": 2, "npc_pompignan": 1},
    ),
    ParisNpcSeed(
        id="npc_saviarre",
        name="Saviarre",
        clan_id="ventrue",
        role_1435="Conseillère d'Alexandre",
        ambition_1435="Préserver Alexandre et la continuité de son pouvoir dans une période où il délègue davantage",
        short_goal_1435="Maintenir les fidèles du Prince en contact et éviter l'effondrement de la Cour",
        loyalty=90,
        aggression=35,
        influence=7.0,
        status=4,
        camarilla_attitude=1,
        embraced_year=481,
        generation=5,
        sire_id="npc_alexandre",
        source_keys=("alexandre", "alexandre_pouvoir", "chronologie", "lignees_ventrue"),
        source_tier="B",
        territorial_interest="Cour d'Alexandre",
        active_plan="Coordonner les soutiens encore loyaux au Prince pendant que la situation mortelle fragilise son emprise.",
        relations={"npc_alexandre": 3},
    ),
    ParisNpcSeed(
        id="npc_beatrix",
        name="Béatrix",
        clan_id="toreador",
        role_1435="Figure dominante des Toréador parisiens",
        ambition_1435="Préserver la puissance toréador et faire de son clan un arbitre indispensable de la politique parisienne",
        short_goal_1435="Soutenir ce qui maintient Paris hors de l'emprise de Mithras sans abandonner l'autonomie toréador",
        loyalty=55,
        aggression=45,
        influence=8.0,
        status=4,
        camarilla_attitude=1,
        embraced_year=1124,
        generation=5,
        source_keys=("beatrix", "alexandre_pouvoir", "chronologie"),
        source_tier="B",
        territorial_interest="Cour toréador et réseaux religieux, artistiques et aristocratiques de Paris",
        active_plan="Renforcer la clientèle toréador tout en restant indispensable aux Ventrue affaiblis.",
        relations={"npc_alexandre": 1, "npc_villon": 1},
    ),
    ParisNpcSeed(
        id="npc_villon",
        name="François Villon",
        clan_id="toreador",
        role_1435="Ancien Toréador de Paris",
        ambition_1435="Accroître sa clientèle et son poids personnel sans se laisser enfermer dans l'obéissance à un seul ancien",
        short_goal_1435="Transformer sa connaissance de Paris et des milieux populaires en capital social vampirique",
        loyalty=45,
        aggression=55,
        influence=7.0,
        status=3,
        camarilla_attitude=0,
        birth_year=1197,
        embraced_year=1230,
        generation=5,
        sire_id="helene",
        source_keys=("francois_villon", "chronologie"),
        source_tier="B",
        territorial_interest="Paris, ses tavernes, ses rues et la sociabilité toréador",
        active_plan="Élargir un réseau personnel capable de survivre aux changements de Prince et de faction.",
        relations={"npc_violetta": 2, "npc_beatrix": 1},
    ),
    ParisNpcSeed(
        id="npc_violetta",
        name="Violetta",
        clan_id="toreador",
        role_1435="Infante ancienne de François Villon",
        ambition_1435="Construire une position propre sans rester seulement définie par son sire",
        short_goal_1435="Accumuler des alliés et des informations dans les cercles toréador et urbains",
        loyalty=60,
        aggression=30,
        influence=5.0,
        status=2,
        camarilla_attitude=1,
        birth_year=1231,
        embraced_year=1250,
        generation=6,
        sire_id="npc_villon",
        source_keys=("violetta", "francois_villon"),
        source_tier="A",
        territorial_interest="Réseaux sociaux et artistiques parisiens",
        active_plan="Développer une autorité indépendante de celle de Villon sans rompre leur lien.",
        relations={"npc_villon": 2},
    ),
    ParisNpcSeed(
        id="npc_magnerius",
        name="Magnerius de Sens",
        clan_id="ventrue",
        role_1435="Ancien Ventrue fidèle au pouvoir d'Alexandre",
        ambition_1435="Empêcher l'effondrement de la puissance ventrue française",
        short_goal_1435="Conserver une cohésion minimale entre les fidèles d'Alexandre",
        loyalty=80,
        aggression=50,
        influence=7.0,
        status=4,
        camarilla_attitude=1,
        embraced_year=987,
        generation=6,
        sire_id="geoffrey",
        source_keys=("magnerius", "alexandre_pouvoir", "chronologie"),
        source_tier="B",
        territorial_interest="Cour Ventrue et continuité dynastique du pouvoir parisien",
        active_plan="Maintenir les Ventrue fidèles capables de gouverner si Alexandre s'affaiblit encore.",
        relations={"npc_alexandre": 2, "npc_pompignan": 1},
    ),
    ParisNpcSeed(
        id="npc_henri_preux",
        name="Henri le Preux",
        clan_id="ventrue",
        role_1435="Prince installé à Bourges et ancien fidèle d'Alexandre",
        ambition_1435="Conserver un pôle de pouvoir loyal à la cause française hors de Paris occupée",
        short_goal_1435="Soutenir le Dauphin et préserver une capacité de retour politique vers Paris",
        loyalty=75,
        aggression=55,
        influence=7.0,
        status=4,
        camarilla_attitude=1,
        location_1435="Bourges",
        embraced_year=1087,
        generation=6,
        sire_id="geoffrey",
        source_keys=("henri_preux", "alexandre_pouvoir", "chronologie"),
        source_tier="B",
        territorial_interest="Bourges, Cour du Dauphin et retour d'influence vers Paris",
        active_plan="Préserver le camp du Dauphin jusqu'à ce que Paris redevienne politiquement accessible.",
        relations={"npc_alexandre": 1, "npc_beatrix": 1},
    ),
    ParisNpcSeed(
        id="npc_pompignan",
        name="Pierre Emmanuel de Pompignan",
        clan_id="ventrue",
        role_1435="Ancien Ventrue chevaleresque du réseau d'Alexandre",
        ambition_1435="Préserver une conception aristocratique, monarchique et disciplinée du pouvoir ventrue",
        short_goal_1435="Soutenir les forces capables de restaurer une autorité française durable",
        loyalty=75,
        aggression=70,
        influence=6.5,
        status=3,
        camarilla_attitude=1,
        birth_year=1170,
        embraced_year=1206,
        generation=6,
        sire_id="frenegonde",
        source_keys=("pompignan", "alexandre_pouvoir", "chronologie"),
        source_tier="B",
        territorial_interest="Noblesse guerrière, monarchie et réseau Ventrue français",
        active_plan="Renforcer les Ventrue les plus traditionalistes sans laisser les Toréador monopoliser la reconstruction de Paris.",
        relations={"npc_alexandre": 1, "npc_magnerius": 1, "npc_villon": -1},
    ),
)


PARIS_1435_FACTIONS: tuple[ParisFactionSeed, ...] = (
    ParisFactionSeed(
        id="faction_princely_court",
        name="Cour fidèle d'Alexandre",
        agenda_1435="Empêcher l'autorité d'Alexandre de disparaître malgré l'occupation et les ingérences extérieures.",
        member_ids=("npc_alexandre", "npc_saviarre", "npc_magnerius", "npc_pompignan"),
        influence=8.0,
        source_keys=("alexandre_pouvoir", "chronologie"),
        member_clans=("ventrue",),
    ),
    ParisFactionSeed(
        id="faction_toreador_paris",
        name="Réseaux toréador parisiens",
        agenda_1435="Préserver Paris de Mithras tout en augmentant l'autonomie et le poids politique du clan.",
        member_ids=("npc_beatrix", "npc_villon", "npc_violetta"),
        influence=7.5,
        source_keys=("alexandre_pouvoir", "beatrix", "francois_villon", "violetta"),
        member_clans=("toreador",),
    ),
    ParisFactionSeed(
        id="faction_court_miracles",
        name="Cour des Miracles",
        agenda_1435="Transformer le mécontentement des exclus et des clans marginalisés en contre-pouvoir parisien.",
        member_ids=(),
        influence=7.0,
        source_keys=("alexandre_pouvoir",),
        member_clans=("brujah", "malkavian", "gangrel", "nosferatu"),
    ),
)


CANONICAL_PRESSURES: tuple[CanonicalPressure, ...] = (
    CanonicalPressure(
        id="pressure_alexandre_1481",
        around_year=1481,
        title="Révolte des Écorcheurs et chute d'Alexandre",
        premise="La chronologie de référence détruit Alexandre et Saviarre lors d'une révolte anarch et ouvre une lutte de succession.",
        required_state=(
            "agitation anarch élevée",
            "autorité d'Alexandre suffisamment fragilisée",
            "Écorcheurs encore capables d'agir",
            "protection du refuge princier insuffisante",
        ),
        possible_divergences=(
            "Alexandre survit",
            "Saviarre seule disparaît",
            "la révolte échoue",
            "Alexandre perd Paris sans être détruit",
            "une autre faction détourne la crise",
        ),
        source_keys=("chronologie", "alexandre_pouvoir"),
    ),
    CanonicalPressure(
        id="pressure_violetta_1666",
        around_year=1666,
        title="Élection de Violetta comme Justicar",
        premise="La fiche de Violetta la donne élue Justicar en 1666.",
        required_state=("Violetta est toujours active", "sa réputation et ses appuis sont suffisants"),
        possible_divergences=("une autre candidate est choisie", "la fonction évolue autrement", "Violetta refuse ou est empêchée"),
        source_keys=("violetta",),
    ),
)


def paris_npc_seed(npc_id: str) -> ParisNpcSeed:
    for seed in PARIS_1435_NPCS:
        if seed.id == npc_id:
            return seed
    raise ValueError(f"Unknown Paris 1435 NPC: {npc_id}")
