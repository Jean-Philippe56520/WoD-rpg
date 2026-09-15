from game.chronicle import CHRONICLE_GAME_ID, CLAN_DISCIPLINES, ChronicleProgress, create_player_character
from game.chronicle_store import ChronicleStore
from game.models import GameState
from game.persistence import SQLiteGameRepository
from game.vampire_profile import ATTRIBUTE_NAMES, SKILL_NAMES, default_profile
from game.vampire_profile_store import VampireProfileStore


def make_character(progress, clan_id="ventrue"):
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-1",
        player_name="Joueur",
        character_id="pc-1",
        name="Jehan",
        clan_id=clan_id,
        concept="Noble déchu",
        starting_discipline=CLAN_DISCIPLINES[clan_id][0],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Obtenir un Domaine",
        chapter_goal="Gagner mon autonomie",
        progress=progress,
    )


def test_default_profile_adds_vampire_sheet_without_mutating_core_character():
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    character = make_character(progress)
    profile = default_profile(character)

    assert profile.generation > 0
    assert profile.blood_potency == 1
    assert set(profile.attributes) == set(ATTRIBUTE_NAMES)
    assert set(profile.skills) == set(SKILL_NAMES)
    assert profile.convictions
    assert profile.touchstones
    assert profile.feeding_preference is not None
    assert character.status == 0


def test_profile_store_roundtrip_is_backward_compatible(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "profile.sqlite3")
    repo.ensure_game(CHRONICLE_GAME_ID, "Chronique", GameState(), ("ventrue", "toreador", "brujah"))
    chronicle_store = ChronicleStore(repo)
    progress = chronicle_store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    character = make_character(progress, clan_id="brujah")
    chronicle_store.create_character(character)

    store = VampireProfileStore(repo)
    created = store.ensure_for_character(character)
    loaded = store.get(CHRONICLE_GAME_ID, character.character_id)

    assert loaded == created
    assert loaded is not None
    assert loaded.road_affinity
    assert loaded.disciplines
