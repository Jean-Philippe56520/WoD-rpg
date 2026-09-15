from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
)
from game.chronicle_simulation import ensure_character_links, initial_simulation
from game.dice import difficulty_band, difficulty_hint
from game.night_cycle import resolve_night_event
from game.night_cycle_ui import _step_notice
from game.relationship_memory import record_relationship_memory
from game.situations import (
    Situation,
    SituationChoice,
    action_risk_preview,
    effective_difficulty,
    generate_situations,
)
from game.vampire_profile import default_profile


def make_character(clan_id: str = "ventrue"):
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-v048b",
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=CLAN_DISCIPLINES[clan_id][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Obtenir un Domaine",
        chapter_goal="Gagner mon autonomie",
        progress=progress,
    )


def test_hidden_difficulty_bands_follow_validated_scale():
    assert difficulty_band(1) == "facile"
    assert difficulty_band(2) == "standard"
    assert difficulty_band(3) == "standard"
    assert difficulty_band(4) == "difficile"
    assert difficulty_band(5) == "difficile"
    assert difficulty_band(6) == "extrême"
    assert difficulty_band(9) == "extrême"


def test_difficulty_hint_never_exposes_target_number():
    for difficulty in range(1, 9):
        hint = difficulty_hint(difficulty)
        assert hint
        assert str(difficulty) not in hint


def test_preview_exposes_approach_and_band_but_not_numeric_target():
    character = make_character()
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = generate_situations(character, profile, simulation, year=1435)[0]
    choice = situation.choices[0]

    preview = action_risk_preview(character, simulation, situation, choice)

    assert preview.attribute == choice.attribute
    assert preview.skill == choice.skill
    assert preview.band in {"facile", "standard", "difficile", "extrême"}
    assert not hasattr(preview, "difficulty")


def test_favorable_relationship_changes_context_not_character_pool():
    character = make_character()
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    simulation = record_relationship_memory(
        simulation,
        character,
        character.sire_id,
        year=1435,
        disposition_delta=3,
        trust_delta=3,
        respect_delta=2,
        awareness_delta=0,
    )
    choice = SituationChoice(
        id="appeal",
        label="Plaider sa cause",
        description="S'appuyer sur une confiance déjà acquise.",
        attribute="manipulation",
        skill="politics",
        difficulty=4,
        legacy_action=PersonalAction.ELYSIUM,
        effect="political_voice",
    )
    situation = Situation(
        id="relationship_test",
        title="Une faveur délicate",
        body="Votre sire écoute votre demande.",
        source_actor_id=character.sire_id,
        tags=("politics",),
        choices=(choice,),
    )

    difficulty, adjustment = effective_difficulty(character, simulation, situation, choice)
    preview = action_risk_preview(character, simulation, situation, choice)

    assert adjustment == -1
    assert difficulty == 3
    assert preview.band == "standard"


def test_resolution_keeps_exact_target_internal_and_ui_notice_hides_it():
    character = make_character("toreador")
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = generate_situations(character, profile, simulation, year=1435)[0]
    choice = situation.choices[0]

    result = resolve_night_event(
        character,
        profile,
        simulation,
        situation,
        choice.id,
        nights_per_segment=3,
    )
    notice = _step_notice(result)

    assert result.resolution.dice.difficulty >= 1
    assert f"difficulté {result.resolution.dice.difficulty}" not in notice
    assert "risque " in notice
