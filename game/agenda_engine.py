from __future__ import annotations

from .chronicle_simulation import NpcState
from .narrative_state import AGENDA_STAGES


AGENDA_STAGE_SIZE = 3


def agenda_stage_index(npc: NpcState) -> int:
    return min(len(AGENDA_STAGES) - 1, max(0, npc.agenda_progress) // AGENDA_STAGE_SIZE)


def agenda_stage(npc: NpcState) -> str:
    return AGENDA_STAGES[agenda_stage_index(npc)]


def agenda_effect(npc: NpcState, deterministic_score: int) -> int:
    """Return the social action family selected by the NPC's current plan stage.

    Effects match ``paris_simulation._social_action``:
      0 alliance, 1 rivalry, 2 Prestation, 3 patronage/access.

    Early plans probe relationships; mature plans increasingly spend political
    resources. The agenda counter is already persisted in SimulationState, so no
    new storage or migration is required.
    """

    stage = agenda_stage(npc)
    if stage == "probe":
        options = (0, 1)
    elif stage == "recruit":
        options = (0, 2, 1)
    elif stage == "commit":
        options = (1, 2, 3)
    else:
        options = (0, 2, 3)
    return options[deterministic_score % len(options)]
