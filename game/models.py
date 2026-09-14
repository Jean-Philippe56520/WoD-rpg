from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class IdeologyQuadrant(str, Enum):
    HUMANIST_TRADITIONAL = "humanist_traditional"
    HUMANIST_REFORMIST = "humanist_reformist"
    PREDATORY_TRADITIONAL = "predatory_traditional"
    PREDATORY_RADICAL = "predatory_radical"


@dataclass
class Character:
    id: str
    name: str
    clan_id: Optional[str] = None
    personal_influence: float = 0.0
    humanity: int = 7
    humanism: float = 0.0
    tradition: float = 0.0
    loyalty: float = 50.0
    ambition: float = 50.0
    is_primogen: bool = False

    def __post_init__(self) -> None:
        if not 0 <= self.humanity <= 10:
            raise ValueError("Humanity must be between 0 and 10")
        if not -100 <= self.humanism <= 100:
            raise ValueError("Humanism must be between -100 and 100")
        if not -100 <= self.tradition <= 100:
            raise ValueError("Tradition must be between -100 and 100")
        if self.personal_influence < 0:
            raise ValueError("Personal influence cannot be negative")


@dataclass(frozen=True)
class PoliticalCurrent:
    id: str
    clan_id: str
    name: str
    quadrant: IdeologyQuadrant
    influence: float
    leader_id: Optional[str]
    member_ids: tuple[str, ...]
    centroid_humanism: float
    centroid_tradition: float


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
