from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .chronicle import (
    CLAN_DISCIPLINES,
    SUPPORTED_CLANS,
    ChronicleProgress,
    create_player_character,
)
from .chronicle_instance import personal_chronicle_game_id
from .chronicle_simulation import ensure_character_links, grant_boon
from .chronicle_simulation_store import ChronicleSimulationStore
from .chronicle_store import ChronicleStore
from .models import GameState
from .relationship_memory import record_relationship_memory
from .vampire_profile import