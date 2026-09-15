from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AxisPolarity(str, Enum):
    """Compatibilité des sauvegardes V0.7/V0.8 uniquement."""

    PLUS = "+"
    MINUS = "-"


class MortalStance(str, Enum):
    HUMANIST = "humanist"
    PREDATORY = "predatory"


class OrderStance(str, Enum):
    ORTHODOX = "orthodox"
    REFORMIST = "reformist"


class IdeologyQuadrant(str, Enum):
    """Identifiants historiques conservés pour les anciennes APIs/tests."""

    HUMANIST_TRADITIONAL = "humanist_traditional"
    HUMANIST_REFORMIST = "humanist_reformist"
    PREDATORY_TRADITIONAL = "predatory_traditional"
    PREDATORY_RADICAL = "predatory_radical"


class BloodRank(str, Enum):
    NEWBORN = "newborn"
    ANCILLA = "ancilla"
    ELDER = "elder"


class CharacterAttribute(str, Enum):
    PHYSICAL = "physical"
    SOCIAL = "social"
    MENTAL = "mental"


class ClanFactionSide(str, Enum):
    PRIMOGEN = "primogen"
    OPPOSITION = "opposition"


# Alias V0.8 : le terme « coterie » ne doit plus désigner les factions internes du clan.
CoterieSide = ClanFactionSide


class PoliticalAmbition(str, Enum):
    INCREASE_INFLUENCE = "increase_influence"
    OBTAIN_EMBRACE = "obtain_embrace"
    GAIN_DOMAIN = "gain_domain"
    GAIN_BOON = "gain_boon"
    LEAD_OPPOSITION = "lead_opposition"
    WEAKEN_RIVAL = "weaken_rival"
    RAPPROCHEMENT = "rapprochement"
    ENFORCE_ORDER = "enforce_order"
    REFORM_CLAN = "reform_clan"
    BECOME_PRIMOGEN = "become_primogen"


class BoonLevel(str, Enum):
    MINOR = "minor"
    MAJOR = "major"
    LIFE = "life"


class BoonStatus(str, Enum):
    DUE = "due"
    CALLED = "called"
    FULFILLED = "fulfilled"
    REFUSED = "refused"


class PoliticalRequestType(str, Enum):
    EMBRACE_SUPPORT = "embrace_support"
    RESPONSIBILITY = "responsibility"
    PATRONAGE = "patronage"
    INTERNAL_CONFLICT = "internal_conflict"
    BOON = "boon"
    MISSION = "mission"
    POLICY = "policy"


class PoliticalRequestStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    REFUSED = "refused"
    NEGOTIATED = "negotiated"
    PROMISED = "promised"
    RESOLVED = "resolved"


class RequestDecision(str, Enum):
    ACCEPT = "accept"
    REFUSE = "refuse"
    NEGOTIATE = "negotiate"
    PROMISE = "promise"


class PromiseStatus(str, Enum):
    PENDING = "pending"
    FULFILLED = "fulfilled"
    BROKEN = "broken"


CLAN_DISCIPLINES: dict[str, tuple[str, ...]] = {
    "brujah": ("celerite", "puissance", "presence"),
    "toreador": ("auspex", "celerite", "presence"),
    "ventrue": ("domination", "force_d_ame", "presence"),
}


def _validate_zero_to_two(label: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or not 0 <= value <= 2:
        raise ValueError(f"{label} must be an integer between 0 and 2")


@dataclass
class Character:
    id: str
    name: str
    clan_id: Optional[str] = None
    personal_influence: float = 0.0
    mortal_stance: MortalStance = MortalStance.HUMANIST
    order_stance: OrderStance = OrderStance.ORTHODOX
    humanity: int = 7
    status: int = 1
    reputation: int = 0
    political_ambition: PoliticalAmbition = PoliticalAmbition.INCREASE_INFLUENCE
    physical: int = 1
    social: int = 1
    mental: int = 1
    expertises: tuple[str, ...] = ()
    disciplines: dict[str, int] = field(default_factory=dict)
    blood_rank: BloodRank = BloodRank.NEWBORN
    backgrounds: dict[str, int] = field(default_factory=dict)
    relation_to_primogen: int = 1
    relations: dict[str, int] = field(default_factory=dict)
    loyalty: float = 50.0
    ambition: float = 50.0
    is_primogen: bool = False

    def __post_init__(self) -> None:
        self.mortal_stance = MortalStance(self.mortal_stance)
        self.order_stance = OrderStance(self.order_stance)
        self.blood_rank = BloodRank(self.blood_rank)
        self.political_ambition = PoliticalAmbition(self.political_ambition)

        for label, value in (
            ("Physical", self.physical),
            ("Social", self.social),
            ("Mental", self.mental),
            ("Relation to Primogen", self.relation_to_primogen),
        ):
            _validate_zero_to_two(label, value)

        if not isinstance(self.humanity, int) or isinstance(self.humanity, bool) or not 0 <= self.humanity <= 10:
            raise ValueError("Humanity must be an integer between 0 and 10")
        if not isinstance(self.status, int) or isinstance(self.status, bool) or not 0 <= self.status <= 5:
            raise ValueError("Status must be an integer between 0 and 5")
        if not isinstance(self.reputation, int) or isinstance(self.reputation, bool) or not -3 <= self.reputation <= 3:
            raise ValueError("Reputation must be an integer between -3 and 3")
        if self.personal_influence < 0:
            raise ValueError("Personal influence cannot be negative")
        if not 0 <= self.loyalty <= 100:
            raise ValueError("Loyalty must be between 0 and 100")
        if not 0 <= self.ambition <= 100:
            raise ValueError("Ambition must be between 0 and 100")

        cleaned_expertises = tuple(expertise.strip() for expertise in self.expertises)
        if any(not expertise for expertise in cleaned_expertises):
            raise ValueError("Expertises cannot contain empty values")
        if len({expertise.casefold() for expertise in cleaned_expertises}) != len(cleaned_expertises):
            raise ValueError("Expertises must be unique")
        self.expertises = cleaned_expertises

        for discipline, score in self.disciplines.items():
            if not discipline.strip():
                raise ValueError("Discipline names cannot be empty")
            _validate_zero_to_two(f"Discipline {discipline}", score)
        clan_disciplines = CLAN_DISCIPLINES.get(self.clan_id or "")
        if clan_disciplines is not None:
            invalid = set(self.disciplines) - set(clan_disciplines)
            if invalid:
                raise ValueError(
                    f"Invalid clan disciplines for {self.clan_id}: {', '.join(sorted(invalid))}"
                )

        for background, score in self.backgrounds.items():
            if not background.strip():
                raise ValueError("Background names cannot be empty")
            _validate_zero_to_two(f"Background {background}", score)
        for target_id, score in self.relations.items():
            if not target_id.strip():
                raise ValueError("Relation targets cannot be empty")
            _validate_zero_to_two(f"Relation {target_id}", score)

    @property
    def humanity_axis(self) -> AxisPolarity:
        """Compatibilité V0.8 : + = humaniste, - = prédateur."""

        return AxisPolarity.PLUS if self.mortal_stance == MortalStance.HUMANIST else AxisPolarity.MINUS

    @humanity_axis.setter
    def humanity_axis(self, value: AxisPolarity | str) -> None:
        polarity = AxisPolarity(value)
        self.mortal_stance = (
            MortalStance.HUMANIST if polarity == AxisPolarity.PLUS else MortalStance.PREDATORY
        )

    @property
    def tradition_axis(self) -> AxisPolarity:
        """Compatibilité V0.8 : + = orthodoxe, - = réformateur."""

        return AxisPolarity.PLUS if self.order_stance == OrderStance.ORTHODOX else AxisPolarity.MINUS

    @tradition_axis.setter
    def tradition_axis(self, value: AxisPolarity | str) -> None:
        polarity = AxisPolarity(value)
        self.order_stance = (
            OrderStance.ORTHODOX if polarity == AxisPolarity.PLUS else OrderStance.REFORMIST
        )


@dataclass(frozen=True)
class PoliticalCurrent:
    id: str
    clan_id: str
    name: str
    quadrant: IdeologyQuadrant
    influence: float
    leader_id: Optional[str]
    member_ids: tuple[str, ...]
    humanity_axis: AxisPolarity
    tradition_axis: AxisPolarity


@dataclass
class Clan:
    id: str
    name: str
    primogen_id: str


@dataclass(frozen=True)
class CurrentStance:
    clan_id: str
    current_id: str
    supports_primogen: bool
    support_score: float
    allied_primogen_id: Optional[str] = None


@dataclass(frozen=True)
class FactionStance:
    clan_id: str
    supports_primogen: bool
    support_score: float
    allied_primogen_id: Optional[str] = None


CoterieStance = FactionStance


@dataclass(frozen=True)
class PrimogenVote:
    primogen_id: str
    candidate_id: str


@dataclass(frozen=True)
class Candidate:
    id: str
    name: str
    clan_id: Optional[str] = None
    is_primogen: bool = False


@dataclass
class ClanPoliticalState:
    clan: Clan
    faction_memberships: dict[str, ClanFactionSide] = field(default_factory=dict)
    opposition_leader_id: Optional[str] = None
    opposition_allied_primogen_id: Optional[str] = None
    known_character_intel: dict[str, int] = field(default_factory=dict)
    relations: dict[str, float] = field(default_factory=dict)
    # Legacy V0.7 fields kept only so old states can be deserialized safely.
    current_loyalties: dict[str, float] = field(default_factory=dict)
    current_allies: dict[str, str] = field(default_factory=dict)

    @property
    def coterie_memberships(self) -> dict[str, ClanFactionSide]:
        """Alias de lecture/écriture V0.8."""

        return self.faction_memberships

    @coterie_memberships.setter
    def coterie_memberships(self, value: dict[str, ClanFactionSide]) -> None:
        self.faction_memberships = value


@dataclass(frozen=True)
class GameEvent:
    night: int
    category: str
    message: str
    audience_clan_ids: tuple[str, ...] | None = None

    def visible_to(self, clan_id: str) -> bool:
        return self.audience_clan_ids is None or clan_id in self.audience_clan_ids


@dataclass
class Boon:
    id: str
    creditor_id: str
    debtor_id: str
    level: BoonLevel
    origin: str
    created_night: int
    status: BoonStatus = BoonStatus.DUE
    public: bool = False
    called_night: Optional[int] = None
    resolved_night: Optional[int] = None


@dataclass
class Grievance:
    id: str
    owner_id: str
    target_id: str
    reason: str
    severity: int
    created_night: int
    resolved: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.severity, int) or isinstance(self.severity, bool) or not 1 <= self.severity <= 3:
            raise ValueError("Grievance severity must be between 1 and 3")


@dataclass
class PoliticalPromise:
    id: str
    promisor_id: str
    beneficiary_id: str
    description: str
    created_night: int
    due_night: int
    request_id: Optional[str] = None
    status: PromiseStatus = PromiseStatus.PENDING
    resolved_night: Optional[int] = None


@dataclass
class PoliticalRequest:
    id: str
    clan_id: str
    requester_id: str
    request_type: PoliticalRequestType
    description: str
    created_night: int
    target_id: Optional[str] = None
    offered_boon_level: Optional[BoonLevel] = None
    status: PoliticalRequestStatus = PoliticalRequestStatus.OPEN
    response_night: Optional[int] = None


class PrimogenPosition(str, Enum):
    SUPPORT = "support"
    NEUTRAL = "neutral"
    OPPOSE = "oppose"


class EmbraceStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REFUSED = "refused"


@dataclass
class EmbraceRequest:
    id: str
    requester_id: str
    proposed_childe_name: str
    primogen_position: PrimogenPosition
    political_cost: float
    created_night: int
    submitted_by_primogen_id: Optional[str] = None
    status: EmbraceStatus = EmbraceStatus.PENDING
    decision_night: Optional[int] = None


@dataclass
class GameState:
    night: int = 1
    camarilla_stability: float = 100.0
    masquerade_integrity: float = 100.0
    prince_id: Optional[str] = None
    prince_political_capital: float = 0.0
    prince_relations: dict[str, float] = field(default_factory=dict)
    praxis_status: str = "vacant"
    characters: dict[str, Character] = field(default_factory=dict)
    clan_states: dict[str, ClanPoliticalState] = field(default_factory=dict)
    embrace_requests: dict[str, EmbraceRequest] = field(default_factory=dict)
    boons: dict[str, Boon] = field(default_factory=dict)
    grievances: dict[str, Grievance] = field(default_factory=dict)
    political_requests: dict[str, PoliticalRequest] = field(default_factory=dict)
    promises: dict[str, PoliticalPromise] = field(default_factory=dict)
    events: list[GameEvent] = field(default_factory=list)


class ActionType(str, Enum):
    BUILD_INFLUENCE = "build_influence"
    DIPLOMACY = "diplomacy"
    CONSOLIDATE_RELATION = "consolidate_relation"
    RECRUIT = "recruit"
    UNDERMINE = "undermine"
    POACH = "poach"
    INVESTIGATE = "investigate"
    CALL_BOON = "call_boon"
    # Legacy order values accepted for already-submitted V0.7 nights.
    CONSOLIDATE = "consolidate"
    RALLY_OPPOSITION = "rally_opposition"


@dataclass(frozen=True)
class GameAction:
    clan_id: str
    action_type: ActionType
    # Legacy field order intentionally preserved for positional V0.7 callers.
    target_clan_id: Optional[str] = None
    target_current_id: Optional[str] = None
    actor_character_id: Optional[str] = None
    target_character_id: Optional[str] = None


class NightStatus(str, Enum):
    OPEN = "open"
    READY = "ready"
    RESOLVING = "resolving"
    RESOLVED = "resolved"


@dataclass(frozen=True)
class EmbracePetitionOrder:
    member_id: str
    proposed_childe_name: str


@dataclass(frozen=True)
class PoliticalRequestDecisionOrder:
    request_id: str
    decision: RequestDecision


@dataclass(frozen=True)
class ClanNightOrders:
    clan_id: str
    actions: tuple[GameAction, ...]
    vote: PrimogenVote | None = None
    embrace_petitions: tuple[EmbracePetitionOrder, ...] = ()
    request_decisions: tuple[PoliticalRequestDecisionOrder, ...] = ()
    version: int = 1


@dataclass(frozen=True)
class ClanNightReport:
    game_id: str
    night: int
    clan_id: str
    items: tuple[str, ...]
