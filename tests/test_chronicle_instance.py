from game.chronicle import (
    CHRONICLE_GAME_ID,
    CLAN_DISCIPLINES,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
    resolve_personal_night,
)
from game.chronicle_instance import ensure_personal_chronicle, personal_chronicle_game_id
from game.chronicle_service import ChronicleService
from game.chronicle_simulation import ensure_character_links
from game.chronicle_simulation_store import ChronicleSimulationStore
from game.chronicle_store import ChronicleStore
from game.models import GameState
from game.persistence import SQLiteGameRepository
from game.vampire_profile_store import VampireProfileStore


def make_character(progress, *, player_id: str, character_id: str, name: str):
    return create_player_character(
        game_id=progress.game_id,
        player_id=player_id,
        player_name=player_id,
        character_id=character_id,
        name=name,
        clan_id="brujah",
        concept="Chevalier déchu",
        starting_discipline=CLAN_DISCIPLINES["brujah"][0],
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Me faire une place",
        chapter_goal="Comprendre mon sire",
        progress=progress,
    )


def test_personal_chronicle_game_id_is_stable_and_does_not_expose_player_id():
    first = personal_chronicle_game_id("user-123")
    second = personal_chronicle_game_id("user-123")
    other = personal_chronicle_game_id("user-456")

    assert first == second
    assert first != other
    assert first.startswith("chronicle_solo_")
    assert "user-123" not in first


def test_personal_chronicles_are_isolated_and_advance_independently(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "solo.sqlite3")

    first_context = ensure_personal_chronicle(repo, player_id="player-1")
    second_context = ensure_personal_chronicle(repo, player_id="player-2")

    assert first_context.game_id != second_context.game_id

    store = ChronicleStore(repo)
    first_progress = store.get_progress(first_context.game_id)
    second_progress = store.get_progress(second_context.game_id)
    assert first_progress is not None
    assert second_progress is not None

    first = make_character(
        first_progress,
        player_id="player-1",
        character_id="pc-1",
        name="Jehan",
    )
    second = make_character(
        second_progress,
        player_id="player-2",
        character_id="pc-2",
        name="Aelis",
    )
    store.create_character(first)
    store.create_character(second)

    assert [item.player_id for item in store.list_characters(first_context.game_id)] == ["player-1"]
    assert [item.player_id for item in store.list_characters(second_context.game_id)] == ["player-2"]

    current = first
    for action in (PersonalAction.HUNT, PersonalAction.INVESTIGATE, PersonalAction.ELYSIUM):
        outcome = resolve_personal_night(current, action)
        current = store.advance_personal_night(current, outcome)

    assert current.ready_for_convergence
    result = ChronicleService(repo).resolve_convergence(first_context.game_id)
    assert result.next_progress.segment == 2

    untouched = store.get_progress(second_context.game_id)
    assert untouched is not None
    assert untouched.segment == 1
    assert untouched.chapter == 1
    assert untouched.year == 1435

    second_after = store.get_character(second_context.game_id, "player-2")
    assert second_after is not None
    assert second_after.local_night == 1
    assert not second_after.ready_for_convergence


def test_legacy_shared_character_is_copied_to_personal_chronicle_without_deleting_source(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "migration.sqlite3")
    repo.ensure_game(
        CHRONICLE_GAME_ID,
        "Chronique 1435 legacy",
        GameState(),
        ("ventrue", "toreador", "brujah"),
    )
    store = ChronicleStore(repo)
    legacy_progress = store.ensure_progress(ChronicleProgress(game_id=CHRONICLE_GAME_ID))
    legacy_character = make_character(
        legacy_progress,
        player_id="player-1",
        character_id="pc-legacy",
        name="Jehan",
    )
    other_legacy_character = make_character(
        legacy_progress,
        player_id="player-2",
        character_id="pc-other",
        name="Aelis",
    )
    store.create_character(legacy_character)
    store.create_character(other_legacy_character)

    profile_store = VampireProfileStore(repo)
    legacy_profile = profile_store.ensure_for_character(legacy_character)

    simulation_store = ChronicleSimulationStore(repo)
    legacy_simulation = simulation_store.ensure(CHRONICLE_GAME_ID, year=legacy_progress.year)
    legacy_simulation = ensure_character_links(legacy_simulation, legacy_character)
    legacy_simulation = ensure_character_links(legacy_simulation, other_legacy_character)
    simulation_store.save(legacy_simulation)

    outcome = resolve_personal_night(legacy_character, PersonalAction.INVESTIGATE)
    legacy_after_night = store.advance_personal_night(legacy_character, outcome)
    assert legacy_after_night.local_night == 2

    context = ensure_personal_chronicle(repo, player_id="player-1")
    assert context.migrated_legacy
    assert context.game_id != CHRONICLE_GAME_ID

    migrated = store.get_character(context.game_id, "player-1")
    assert migrated is not None
    assert migrated.character_id == legacy_character.character_id
    assert migrated.local_night == 2
    assert migrated.game_id == context.game_id
    assert store.get_character(context.game_id, "player-2") is None

    migrated_profile = profile_store.get(context.game_id, migrated.character_id)
    assert migrated_profile is not None
    assert migrated_profile.game_id == context.game_id
    assert migrated_profile.generation == legacy_profile.generation

    migrated_history = store.list_history(context.game_id, migrated.character_id)
    assert len(migrated_history) == 1
    assert migrated_history[0]["action"] == PersonalAction.INVESTIGATE.value

    source = store.get_character(CHRONICLE_GAME_ID, "player-1")
    source_other = store.get_character(CHRONICLE_GAME_ID, "player-2")
    assert source is not None
    assert source_other is not None
    assert source.game_id == CHRONICLE_GAME_ID
    assert source.local_night == 2

    migrated_simulation = simulation_store.get(context.game_id)
    assert migrated_simulation is not None
    assert migrated_simulation.game_id == context.game_id
    assert any(
        right.beneficiary_id == migrated.character_id
        for right in migrated_simulation.hunting_rights.values()
    )
    assert all(
        right.beneficiary_id != other_legacy_character.character_id
        and right.granted_by_id != other_legacy_character.character_id
        for right in migrated_simulation.hunting_rights.values()
    )
    assert all(
        domain.holder_id != other_legacy_character.character_id
        for domain in migrated_simulation.domains.values()
    )
    assert all(
        holder_id != other_legacy_character.character_id
        for holder_id in migrated_simulation.offices.values()
    )
