from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    clan_id: Optional[str] = None
    is_primogen: bool = False


@dataclass
class PoliticalCurrent:
    id: str
    name: str
    influence: float
    leader_name: str

    def __post_init__(self) -> None:
        if self.influence < 0:
            raise ValueError("Current influence cannot be negative")


@dataclass
class Clan:
    id: str
    name: str
    primogen_id: str
    dominant_current: PoliticalCurrent
    opposition_current: PoliticalCurrent

    @property
    def total_influence(self) -> float:
        return self.dominant_current.influence + self.opposition_current.influence


@dataclass(frozen=True)
class OppositionStance:
    clan_id: str
    supports_primogen: bool
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
    opposition_loyalty: float
    opposition_ally_id: str
    relations: dict[str, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.opposition_loyalty = max(0.0, min(100.0, self.opposition_loyalty))


@dataclass(frozen=True)
class GameEvent:
    night: int
    category: str
    message: str


@dataclass
class GameState:
    night: int = 1
    camarilla_stability: float = 100.0
    masquerade_integrity: float = 100.0
    prince_id: Optional[str] = None
    praxis_status: str = "vacant"
    clan_states: dict[str, ClanPoliticalState] = field(default_factory=dict)
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
