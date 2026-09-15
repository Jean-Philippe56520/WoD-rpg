from game.config import DEFAULT_RULES
from game.embrace import (
    childe_character_id,
    create_embrace_request,
    decide_embrace_request,
    embrace_was_enacted,
    resolve_embrace_reactions,
)
from game.factions import initialize_factions
from game.models import (
    Candidate,
    ClanFactionSide,
    EmbraceStatus,
    PoliticalAmbition,
    PrimogenPosition,
)
from game.offices import install_prince
from game.serialization import game_state_from_json, game_state_to_json
from game.world import create_initial_game_state


def state_with_ventrue_prince():
    state = create_initial_game_state()
    install_prince(
        state,
        Candidate("primogen_ventrue", "Adrien de Keravel", "ventrue", True),
    )
    return state


def test_approved_embrace_creates_real_childe_in_sires_faction():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "toreador_camille",
        "Adele",
        PrimogenPosition.SUPPORT,
    )
    state = decide_embrace_request(state, "embrace_1", True)

    childe_id = childe_character_id("embrace_1")
    assert embrace_was_enacted(state, "embrace_1")
    assert childe_id in state.characters
    childe = state.characters[childe_id]
    sire = state.characters["toreador_camille"]
    assert childe.name == "Adele"
    assert childe.clan_id == "toreador"
    assert childe.hunger == DEFAULT_RULES.embrace_childe_initial_hunger
    assert childe.personal_influence == DEFAULT_RULES.embrace_childe_initial_influence
    assert childe.relations[sire.id] == 2
    assert sire.relations[childe.id] == 2
    assert (
        state.clan_states["toreador"].faction_memberships[childe.id]
        == state.clan_states["toreador"].faction_memberships[sire.id]
    )
    assert any("rejoint officiellement" in event.message for event in state.events)


def test_enacted_childe_survives_state_serialization():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "toreador_camille",
        "Adele",
        PrimogenPosition.SUPPORT,
    )
    state = decide_embrace_request(state, "embrace_1", True)

    restored = game_state_from_json(game_state_to_json(state))
    childe_id = childe_character_id("embrace_1")
    assert childe_id in restored.characters
    assert restored.characters[childe_id].name == "Adele"
    assert restored.characters[childe_id].relations["toreador_camille"] == 2


def test_old_approved_request_without_childe_is_enacted_once():
    state = state_with_ventrue_prince()
    state = create_embrace_request(
        state,
        "toreador_camille",
        "Adele",
        PrimogenPosition.SUPPORT,
    )
    request = state.embrace_requests["embrace_1"]
    request.status = EmbraceStatus.APPROVED
    request.decision_night = state.night

    events = resolve_embrace_reactions(state)
    assert len(events) == 1
    assert childe_character_id(request.id) in state.characters
    assert resolve_embrace_reactions(state) == []


def test_refused_highly_ambitious_detached_sire_can_embrace_clandestinely():
    state = state_with_ventrue_prince()
    camille = state.characters["toreador_camille"]
    camille.political_ambition = PoliticalAmbition.OBTAIN_EMBRACE
    camille.ambition = 90
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
    stability_before = state.camarilla_stability
    masquerade_before = state.masquerade_integrity
    prince_relation_before = state.prince_relations["toreador"]
    reputation_before = state.characters[camille.id].reputation

    events = resolve_embrace_reactions(state)

    childe_id = childe_character_id("embrace_1")
    assert childe_id in state.characters
    assert state.clan_states["toreador"].faction_memberships[childe_id] == ClanFactionSide.OPPOSITION
    assert state.camarilla_stability == stability_before - DEFAULT_RULES.clandestine_embrace_stability_loss
    assert state.masquerade_integrity == masquerade_before - DEFAULT_RULES.clandestine_embrace_masquerade_loss
    assert (
        state.prince_relations["toreador"]
        == prince_relation_before - DEFAULT_RULES.clandestine_embrace_prince_relation_loss
    )
    assert state.characters[camille.id].reputation == reputation_before - DEFAULT_RULES.clandestine_embrace_reputation_loss
    assert any("clandestine" in event.message for event in events)
    assert any(
        grievance.owner_id == state.prince_id and grievance.target_id == camille.id
        for grievance in state.grievances.values()
    )


def test_refused_loyal_or_insufficiently_ambitious_sire_does_not_defy_prince():
    state = state_with_ventrue_prince()
    camille = state.characters["toreador_camille"]
    camille.political_ambition = PoliticalAmbition.OBTAIN_EMBRACE
    camille.ambition = DEFAULT_RULES.clandestine_embrace_ambition_threshold - 1

    state = create_embrace_request(
        state,
        camille.id,
        "Mila",
        PrimogenPosition.SUPPORT,
    )
    state = decide_embrace_request(state, "embrace_1", False)

    assert resolve_embrace_reactions(state) == []
    assert not embrace_was_enacted(state, "embrace_1")
