import pytest

from game.models import (
    ActionType,
    ClanNightOrders,
    ClanNightReport,
    GameAction,
    NightStatus,
    PrimogenVote,
)
from game.persistence import SQLiteGameRepository
from game.world import REQUIRED_CLANS, create_initial_game_state


def make_repo(tmp_path):
    repo = SQLiteGameRepository(tmp_path / "game.sqlite3")
    repo.ensure_game("main", "Test", create_initial_game_state(), REQUIRED_CLANS)
    return repo


def orders_for(state, clan_id):
    primogen_id = state.clan_states[clan_id].clan.primogen_id
    return ClanNightOrders(
        clan_id=clan_id,
        actions=(GameAction(clan_id, ActionType.BUILD_INFLUENCE),),
        vote=PrimogenVote(primogen_id, primogen_id),
    )


def test_one_player_can_claim_only_one_clan_and_clan_is_unique(tmp_path):
    repo = make_repo(tmp_path)
    repo.claim_clan("main", "p1", "Alice", "ventrue")
    with pytest.raises(ValueError, match="only one clan"):
        repo.claim_clan("main", "p1", "Alice", "toreador")
    with pytest.raises(ValueError, match="already controlled"):
        repo.claim_clan("main", "p2", "Bob", "ventrue")


def test_night_becomes_ready_only_after_all_three_submissions(tmp_path):
    repo = make_repo(tmp_path)
    state = repo.get_game_state("main")
    for player_id, clan_id in zip(("p1", "p2", "p3"), REQUIRED_CLANS):
        repo.claim_clan("main", player_id, player_id, clan_id)

    assert repo.submit_orders("main", "p1", orders_for(state, "ventrue")) == NightStatus.OPEN
    assert repo.submit_orders("main", "p2", orders_for(state, "toreador")) == NightStatus.OPEN
    assert repo.submit_orders("main", "p3", orders_for(state, "brujah")) == NightStatus.READY


def test_resolution_lock_can_be_acquired_only_once(tmp_path):
    repo = make_repo(tmp_path)
    state = repo.get_game_state("main")
    for player_id, clan_id in zip(("p1", "p2", "p3"), REQUIRED_CLANS):
        repo.claim_clan("main", player_id, player_id, clan_id)
        repo.submit_orders("main", player_id, orders_for(state, clan_id))

    bundle = repo.try_begin_resolution("main")
    assert bundle is not None
    assert repo.try_begin_resolution("main") is None
    repo.abort_resolution("main", bundle.night)
    assert repo.try_begin_resolution("main") is not None


def test_finalize_creates_next_open_night_and_reports(tmp_path):
    repo = make_repo(tmp_path)
    state = repo.get_game_state("main")
    for player_id, clan_id in zip(("p1", "p2", "p3"), REQUIRED_CLANS):
        repo.claim_clan("main", player_id, player_id, clan_id)
        repo.submit_orders("main", player_id, orders_for(state, clan_id))

    bundle = repo.try_begin_resolution("main")
    assert bundle is not None
    state.night = 2
    reports = {
        clan_id: ClanNightReport("main", 1, clan_id, (f"rapport {clan_id}",))
        for clan_id in REQUIRED_CLANS
    }
    repo.finalize_resolution(bundle, state, reports)
    info = repo.get_game_info("main")
    assert info["current_night"] == 2
    assert info["night_status"] == NightStatus.OPEN
    assert repo.get_report("main", 1, "ventrue").items == ("rapport ventrue",)


def test_elysium_is_independent_from_night_submission(tmp_path):
    repo = make_repo(tmp_path)
    repo.claim_clan("main", "p1", "Alice", "ventrue")
    repo.post_elysium_message("main", "p1", "ventrue", "Bonsoir, Cour.")
    messages = repo.list_elysium_messages("main")
    assert messages[-1]["body"] == "Bonsoir, Cour."
