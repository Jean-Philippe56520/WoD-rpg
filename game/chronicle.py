from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
import hashlib
from typing import Any


CHRONICLE_GAME_ID = "chronicle_1435"
CHRONICLE_NAME = "Chronique des Premières Nuits"
CHRONICLE_START_YEAR = 1435
DEFAULT_NIGHTS_PER_SEGMENT = 3
DEFAULT_SEGMENTS_PER_CHAPTER = 3
DEFAULT_ELLIPSE_YEARS = 2
SUPPORTED_CLANS = ("ventrue", "toreador", "brujah")

CLAN_LABELS = {
    "ventrue": "Ventrue",
    "toreador": "Toreador",
    "brujah": "Brujah",
}

CLAN_DISCIPLINES = {
    "ventrue": ("Domination", "Force d'âme", "Présence"),
    "toreador": ("Auspex", "Célérité", "Présence"),
    "brujah": ("Célérité", "Puissance", "Présence"),
}


class PersonalAction(str, Enum):
    HUNT = "hunt"
    VISIT_SIRE = "visit_sire"
    INVESTIGATE = "investigate"
    BUILD_RELATION = "build_relation"
    ELYSIUM = "elysium"
    PURSUE_GOAL = "pursue_goal"


class PoliticalOffice(str, Enum):
    NONE = "none"
    DOMAIN_HOLDER = "domain_holder"
    CLAN_ENVOY = "clan_envoy"
    PRIMOGEN = "primogen"
    PRINCE = "prince"


OFFICE_LABELS = {
    PoliticalOffice.NONE.value: "Aucune fonction",
    PoliticalOffice.DOMAIN_HOLDER.value: "Détenteur de Domaine",
    PoliticalOffice.CLAN_ENVOY.value: "Représentant du clan",
    PoliticalOffice.PRIMOGEN.value: "Primogène",
    PoliticalOffice.PRINCE.value: "Prince",
}


ACTION_LABELS = {
    PersonalAction.HUNT: "Chasser",
    PersonalAction.VISIT_SIRE: "Répondre à mon sire",
    PersonalAction.INVESTIGATE: "Enquêter",
    PersonalAction.BUILD_RELATION: "Cultiver une relation",
    PersonalAction.ELYSIUM: "Fréquenter l'Elysium",
    PersonalAction.PURSUE_GOAL: "Poursuivre mon objectif",
}


@dataclass(frozen=True)
class SireProfile:
    id: str
    name: str
    clan_id: str
    order_stance: str
    mortal_stance: str
    title: str
    description: str
    protection: str
    expectation: str


SIRES: tuple[SireProfile, ...] = (
    SireProfile(
        id="sire_ventrue_aymon",
        name="Aymon de Montfort",
        clan_id="ventrue",
        order_stance="orthodox",
        mortal_stance="predatory",
        title="Seigneur Ventrue",
        description=(
            "Un seigneur méthodique qui considère l'ordre féodal comme le reflet naturel "
            "de l'ordre du Sang."
        ),
        protection="Il garantit votre présentation aux puissants et votre sécurité initiale.",
        expectation="Il attend obéissance, retenue et résultats visibles.",
    ),
    SireProfile(
        id="sire_ventrue_heloise",
        name="Héloïse de Blois",
        clan_id="ventrue",
        order_stance="reformist",
        mortal_stance="humanist",
        title="Dame des routes et des chartes",
        description=(
            "Une Ventrue convaincue que les nouvelles cités et leurs bourgeois déplaceront "
            "les anciens rapports de pouvoir."
        ),
        protection="Elle vous ouvre ses relais marchands, ses messagers et ses introductions.",
        expectation="Elle attend initiative, discrétion et capacité à créer de nouvelles alliances.",
    ),
    SireProfile(
        id="sire_toreador_isabeau",
        name="Isabeau de Valois",
        clan_id="toreador",
        order_stance="orthodox",
        mortal_stance="humanist",
        title="Muse de la Cour nocturne",
        description=(
            "Une Toreador ancienne qui protège artistes, chroniqueurs et diplomates, tout en "
            "défendant strictement les usages de la haute société caïnite."
        ),
        protection="Elle vous offre accès aux salons, aux artistes et aux réseaux de cour.",
        expectation="Elle exige élégance, loyauté publique et maîtrise de vos passions.",
    ),
    SireProfile(
        id="sire_toreador_matteo",
        name="Matteo di Firenze",
        clan_id="toreador",
        order_stance="reformist",
        mortal_stance="predatory",
        title="Mécène itinérant",
        description=(
            "Un Toreador fasciné par les cités libres, les ateliers et les idées nouvelles, "
            "moins attaché aux hiérarchies anciennes qu'à l'influence réelle."
        ),
        protection="Il vous relie à des artistes, artisans, marchands et voyageurs.",
        expectation="Il attend curiosité, audace et informations utiles.",
    ),
    SireProfile(
        id="sire_brujah_guilhem",
        name="Guilhem d'Aquitaine",
        clan_id="brujah",
        order_stance="orthodox",
        mortal_stance="humanist",
        title="Gardien des anciennes disputes",
        description=(
            "Un Brujah érudit qui croit encore possible d'imposer une discipline commune aux "
            "Caïnites sans renoncer au débat."
        ),
        protection="Il vous enseigne les usages, vous présente aux érudits et garantit votre parole.",
        expectation="Il attend courage, argumentation et fidélité à vos engagements.",
    ),
    SireProfile(
        id="sire_brujah_ysabeau",
        name="Ysabeau des Cendres",
        clan_id="brujah",
        order_stance="reformist",
        mortal_stance="predatory",
        title="Voix des révoltés",
        description=(
            "Une Brujah marquée par les violences des anciens et proche des courants qui refusent "
            "leur domination absolue."
        ),
        protection="Elle vous donne des refuges, des combattants et des contacts parmi les mécontents.",
        expectation="Elle attend indépendance, solidarité et volonté de résister aux abus des anciens.",
    ),
)


@dataclass(frozen=True)
class ChronicleProgress:
    game_id: str
    year: int = CHRONICLE_START_YEAR
    chapter: int = 1
    segment: int = 1
    nights_per_segment: int = DEFAULT_NIGHTS_PER_SEGMENT
    segments_per_chapter: int = DEFAULT_SEGMENTS_PER_CHAPTER
    ellipse_years: int = DEFAULT_ELLIPSE_YEARS


@dataclass(frozen=True)
class PlayerCharacter:
    game_id: str
    player_id: str
    player_name: str
    character_id: str
    name: str
    clan_id: str
    concept: str
    sire_id: str
    sire_name: str
    embraced_year: int
    chronicle_year: int
    chapter: int
    segment: int
    local_night: int
    hunger: int
    humanity: int
    status: int
    reputation: int
    personal_influence: float
    sire_relation: int
    goal_progress: int
    long_term_goal: str
    chapter_goal: str
    starting_discipline: str
    mortal_stance: str
    order_stance: str
    experience: int = 0
    office: str = PoliticalOffice.NONE.value
    lineage_parent_id: str | None = None
    ready_for_convergence: bool = False
    is_active: bool = True

    def __post_init__(self) -> None:
        if self.clan_id not in SUPPORTED_CLANS:
            raise ValueError(f"Unsupported clan: {self.clan_id}")
        if not self.name.strip():
            raise ValueError("Character name is required")
        if not 0 <= self.hunger <= 5:
            raise ValueError("Hunger must be between 0 and 5")
        if not 0 <= self.humanity <= 10:
            raise ValueError("Humanity must be between 0 and 10")
        if not 0 <= self.status <= 5:
            raise ValueError("Status must be between 0 and 5")
        if not -3 <= self.reputation <= 3:
            raise ValueError("Reputation must be between -3 and 3")
        if not 0 <= self.sire_relation <= 3:
            raise ValueError("Sire relation must be between 0 and 3")
        if self.local_night < 1:
            raise ValueError("Local night must be positive")
        if self.chapter < 1 or self.segment < 1:
            raise ValueError("Chapter and segment must be positive")
        if self.experience < 0:
            raise ValueError("Experience cannot be negative")
        PoliticalOffice(self.office)


@dataclass(frozen=True)
class NightOutcome:
    action: PersonalAction
    roll: int
    summary: str
    detail: str
    updated_character: PlayerCharacter
    tags: tuple[str, ...] = ()
    steps: tuple[dict[str, Any], ...] = ()


def sire_for_id(sire_id: str) -> SireProfile:
    for sire in SIRES:
        if sire.id == sire_id:
            return sire
    raise ValueError(f"Unknown sire: {sire_id}")


def sire_candidates(clan_id: str) -> tuple[SireProfile, ...]:
    return tuple(sire for sire in SIRES if sire.clan_id == clan_id)


def choose_sire(clan_id: str, order_stance: str, mortal_stance: str) -> SireProfile:
    candidates = sire_candidates(clan_id)
    if not candidates:
        raise ValueError(f"No sire available for clan {clan_id}")
    ordered = sorted(
        candidates,
        key=lambda sire: (
            sire.order_stance != order_stance,
            sire.mortal_stance != mortal_stance,
            sire.id,
        ),
    )
    return ordered[0]


def create_player_character(
    *,
    game_id: str,
    player_id: str,
    player_name: str,
    character_id: str,
    name: str,
    clan_id: str,
    concept: str,
    starting_discipline: str,
    mortal_stance: str,
    order_stance: str,
    long_term_goal: str,
    chapter_goal: str,
    progress: ChronicleProgress,
    sire_id: str | None = None,
    sire_name: str | None = None,
    lineage_parent_id: str | None = None,
) -> PlayerCharacter:
    if clan_id not in SUPPORTED_CLANS:
        raise ValueError(f"Unsupported clan: {clan_id}")
    if starting_discipline not in CLAN_DISCIPLINES[clan_id]:
        raise ValueError("Starting discipline must belong to the selected clan")
    if sire_id is None:
        sire = choose_sire(clan_id, order_stance, mortal_stance)
        resolved_sire_id = sire.id
        resolved_sire_name = sire.name
    else:
        if not sire_name:
            raise ValueError("A named sire is required when using a custom sire id")
        resolved_sire_id = sire_id
        resolved_sire_name = sire_name
    return PlayerCharacter(
        game_id=game_id,
        player_id=player_id,
        player_name=player_name.strip() or "Joueur",
        character_id=character_id,
        name=name.strip(),
        clan_id=clan_id,
        concept=concept.strip() or "Nouveau-né en quête de place",
        sire_id=resolved_sire_id,
        sire_name=resolved_sire_name,
        embraced_year=progress.year - 2,
        chronicle_year=progress.year,
        chapter=progress.chapter,
        segment=progress.segment,
        local_night=1,
        hunger=2,
        humanity=7,
        status=0,
        reputation=0,
        personal_influence=0.0,
        sire_relation=2,
        goal_progress=0,
        long_term_goal=long_term_goal.strip() or "Me faire une place dans la société caïnite",
        chapter_goal=chapter_goal.strip() or "Comprendre ce que mon sire attend réellement de moi",
        starting_discipline=starting_discipline,
        mortal_stance=mortal_stance,
        order_stance=order_stance,
        experience=0,
        office=PoliticalOffice.NONE.value,
        lineage_parent_id=lineage_parent_id,
    )


def _stable_roll(character: PlayerCharacter, action: PersonalAction) -> int:
    raw = (
        f"{character.character_id}:{character.chapter}:{character.segment}:"
        f"{character.local_night}:{action.value}"
    )
    digest = hashlib.sha256(raw.encode("utf-8")).digest()
    return digest[0] % 10 + 1


def _free_intent_suffix(free_intent: str) -> str:
    text = " ".join(free_intent.strip().split())
    return f" Votre intention déclarée : « {text[:240]} »." if text else ""


def resolve_personal_night(
    character: PlayerCharacter,
    action: PersonalAction,
    *,
    nights_per_segment: int = DEFAULT_NIGHTS_PER_SEGMENT,
    free_intent: str = "",
) -> NightOutcome:
    if character.ready_for_convergence:
        raise ValueError("Character is already waiting for the convergence")
    if character.local_night > nights_per_segment:
        raise ValueError("Character night is outside the current segment")

    roll = _stable_roll(character, action)
    success = roll >= 5
    hunger = character.hunger
    reputation = character.reputation
    influence = character.personal_influence
    sire_relation = character.sire_relation
    goal_progress = character.goal_progress
    summary = ""
    detail = ""

    if action == PersonalAction.HUNT:
        if success:
            hunger = max(0, hunger - 1)
            summary = "La chasse apaise la Bête."
            detail = "Vous revenez avant l'aube avec la Faim sous contrôle."
        else:
            hunger = min(5, hunger + 1)
            summary = "La chasse tourne mal."
            detail = "La proie vous échappe et la Faim devient plus pressante."
    elif action == PersonalAction.VISIT_SIRE:
        sire_relation = min(3, sire_relation + (1 if success else 0))
        goal_progress += 1 if success else 0
        summary = "Votre sire mesure vos progrès."
        detail = (
            "Votre attitude renforce sa confiance et ouvre la voie à davantage d'autonomie."
            if success
            else "Votre sire reste protecteur, mais doute encore de votre capacité à agir seul."
        )
    elif action == PersonalAction.INVESTIGATE:
        goal_progress += 2 if success else 0
        summary = "Vous remontez une piste politique."
        detail = (
            "Vous identifiez un lien utile entre deux acteurs de la cité."
            if success
            else "Les rumeurs se contredisent et vous perdez du temps sans certitude."
        )
    elif action == PersonalAction.BUILD_RELATION:
        influence += 1.0 if success else 0.25
        summary = "Vous cultivez une relation."
        detail = (
            "Votre interlocuteur commence à vous considérer comme une relation utile."
            if success
            else "Le contact existe, mais aucun engagement solide n'en ressort encore."
        )
    elif action == PersonalAction.ELYSIUM:
        reputation = min(3, reputation + (1 if success else 0))
        influence += 0.5 if success else 0.0
        summary = "Vous paraissez dans les cercles nocturnes."
        detail = (
            "Votre nom circule favorablement après votre passage."
            if success
            else "Votre présence passe presque inaperçue, ce qui reste préférable à un faux pas."
        )
    elif action == PersonalAction.PURSUE_GOAL:
        goal_progress += 2 if success else 1
        summary = "Vous avancez votre objectif personnel."
        detail = (
            "Vous obtenez un résultat concret qui pourra compter lors du prochain bilan."
            if success
            else "Le résultat reste partiel, mais vous comprenez mieux ce qui vous bloque."
        )

    ready = character.local_night >= nights_per_segment
    next_night = character.local_night if ready else character.local_night + 1
    updated = replace(
        character,
        local_night=next_night,
        hunger=hunger,
        reputation=reputation,
        personal_influence=influence,
        sire_relation=sire_relation,
        goal_progress=goal_progress,
        ready_for_convergence=ready,
    )
    return NightOutcome(
        action=action,
        roll=roll,
        summary=summary,
        detail=detail + _free_intent_suffix(free_intent),
        updated_character=updated,
    )
