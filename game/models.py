from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AxisPolarity(str, Enum):
    PLUS = "+"
    MINUS = "-"


class IdeologyQuadrant(str, Enum):
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
    humanity_axis: AxisPolarity = AxisPolarity.PLUS
    tradition_axis: AxisPolarity = AxisPolarity.PLUS
    physical: int = 1
    social: int = 1
    mental: int = 1
    expertises: tuple[str, ...] = ()
    disciplines: dict[str, int] = field(default_factory=dict)
    blood_rank: BloodRank = BloodRank.NEWBORN
    backgrounds: dict[str, int] = field(default_factory=dict)
    loyalty: float = 50.0
    ambition: float = 50.0
    is_primogen: bool = False

    def __post_init__(self) -> None:
        self.humanity_axis = AxisPolarity(self.humanity_axis)
        self.tradition_axis = AxisPolarity(self.tradition_axis)
        self.blood_rank = BloodRank(self.blood_rank)

        for label, value in (
            ("Physical", self.physical),
            ("Social", self.social),
            ("Mental", self.mental),
        ):
            _validate_zero_to_two(label, value)

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
    current_loyalties: dict[str, float] = field(default_factory=dict)
    current_allies: dict[str, str] = field(default_factory=dict)
    relations: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class GameEvent:
    night: int
    category: str
    message: str
    audience_clan_ids: tuple[str, ...] | None = None

    def visible_to(self, clan_id: str) -> bool:
        return self.audience_clan_ids is None or clan_id in self.audience_clan_ids


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
    events: list[GameEvent] = field(default_factory=list)


class ActionType(str, Enum):
    CONSOLIDATE = "consolidate"
    RALLY_OPPOSITION = "rally_opposition"
    BUILD_INFLUENCE = "build_influence"
    DIPLOMACY = "diplomacy"


@dataclass(frozen=True)
class GameAction:
    clan_id: str
    action_type: ActionType
    target_clan_id: Optional[str] = None
    target_current_id: Optional[str] = None


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
class ClanNightOrders:
    clan_id: str
    actions: tuple[GameAction, ...]
    vote: PrimogenVote | None = None
    embrace_petitions: tuple[EmbracePetitionOrder, ...] = ()


@dataclass(frozen=True)
class ClanNightReport:
    game_id: str
    night: int
    clan_id: str
    items: tuple[str, ...]
