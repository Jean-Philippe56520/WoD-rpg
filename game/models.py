from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    clan_id: Optional[str] = None
    is_primogen: bool = False


@dataclass(frozen=True)
class PoliticalCurrent:
    id: str
    name: str
    influence: float
    leader_name: str

    def __post_init__(self) -> None:
        if self.influence < 0:
            raise ValueError("Current influence cannot be negative")


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class WorldState:
    night: int = 1
    camarilla_stability: float = 100.0
    masquerade_integrity: float = 100.0
