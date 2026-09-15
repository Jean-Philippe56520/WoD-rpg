import pytest

from game.character_rules import action_score
from game.models import CharacterAttribute
from game.world import create_initial_game_state


def test_action_score_adds_attribute_expertise_and_discipline():
    state = create_initial_game_state()
    adrien = state.characters["primogen_ventrue"]
    assert action_score(
        adrien,
        CharacterAttribute.SOCIAL,
        expertise="Politique",
        discipline="presence",
    ) == 5


def test_action_score_adds_attribute_expertise_and_background():
    state = create_initial_game_state()
    adrien = state.characters["primogen_ventrue"]
    assert action_score(
        adrien,
        CharacterAttribute.SOCIAL,
        expertise="Finance",
        background="Ressources",
    ) == 5


def test_missing_expertise_gives_no_bonus():
    state = create_initial_game_state()
    victor = state.characters["ventrue_victor"]
    assert action_score(victor, CharacterAttribute.MENTAL, expertise="Occultisme") == 1


def test_discipline_and_background_cannot_stack():
    state = create_initial_game_state()
    adrien = state.characters["primogen_ventrue"]
    with pytest.raises(ValueError, match="discipline or a background"):
        action_score(
            adrien,
            CharacterAttribute.SOCIAL,
            discipline="presence",
            background="Influence politique",
        )
