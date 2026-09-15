from dataclasses import replace

from game.config import DEFAULT_RULES
from game.embrace import (
    childe_character_id,
    create_embrace_request,
    decide_embrace_request,
)
from game.factions import initialize_factions
from game.models import Candidate, ClanFactionSide, PoliticalAmbition, PrimogenPosition
from game.offices import install_prince
from game.resolution import resolve_night
from game.world import create_initial_game_state


def test_resolve_night_propagates_custom_clandestine_embrace_threshold():
    state = create_initial_game_state()
    install_prince(
        state,
        Candidate("primogen_ventrue", "Adrien de Keravel", "ventrue", True),
    )
    camille = state.characters["toreador_camille"]
    camille.political_ambition = PoliticalAmbition.OBTAIN_EMBRACE
    camille.ambition = 65
    camille.relation_to_primogen = 0
    state.clan_states["toreador"].faction_memberships[camille.id] = ClanFactionSide.OPPOSITION
    initialize_factions(state)

    state = create_embrace_request(
        state,
        camille.id,
        "Mila",
        PrimogenPosition.SUPPORT,
    )
    state = decide_embrace_request(state, "embrace_1", False)

    custom_rules = replace(
        DEFAULT_RULES,
        clandestine_embrace_ambition_threshold=60.0,
    )
    result = resolve_night(
        state,
        actions=(),
        votes={},
        candidates=(),
        rules=custom_rules,
    )

    assert childe_character_id("embrace_1") in result.state.characters
