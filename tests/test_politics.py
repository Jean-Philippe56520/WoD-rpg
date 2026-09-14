from game.models import PrimogenVote
from game.politics import determine_current_stances, resolve_praxis_vote
from game.world import create_initial_game_state, seed_candidates


def self_votes(state):
    return {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, cs.clan.primogen_id)
        for cs in state.clan_states.values()
    }


def test_plurality_without_majority_is_disputed_when_all_currents_support():
    state = create_initial_game_state()
    result = resolve_praxis_vote(state, {}, self_votes(state), seed_candidates())
    assert result.primogen_weights["primogen_ventrue"] == 67
    assert result.primogen_weights["primogen_toreador"] == 72
    assert result.primogen_weights["primogen_brujah"] == 60
    assert result.total_cast_influence == 199
    assert result.recognition_threshold == 99.5
    assert result.winner_id is None


def test_current_stances_are_autonomous_and_ideology_sensitive():
    state = create_initial_game_state()
    stances = determine_current_stances(state)
    assert stances["ventrue__humanist_reformist"].supports_primogen is False
    assert stances["ventrue__humanist_traditional"].supports_primogen is True
    assert stances["toreador__predatory_radical"].supports_primogen is False


def test_dissent_transfers_half_of_each_current_to_its_allied_primogen():
    state = create_initial_game_state()
    stances = determine_current_stances(state)
    result = resolve_praxis_vote(state, stances, self_votes(state), seed_candidates())
    transfer = next(
        item for item in result.current_transfers
        if item["from_current_id"] == "ventrue__humanist_reformist"
    )
    assert transfer["amount"] == 7.5
    assert transfer["to_primogen_id"] == "primogen_toreador"
    assert result.primogen_weights["primogen_ventrue"] == 59.5
    assert result.primogen_weights["primogen_toreador"] == 81.5


def test_different_dissenting_currents_can_support_different_external_primogens():
    state = create_initial_game_state()
    result = resolve_praxis_vote(
        state,
        determine_current_stances(state),
        self_votes(state),
        seed_candidates(),
    )
    transfers = {
        (item["from_current_id"], item["to_primogen_id"])
        for item in result.current_transfers
    }
    assert ("ventrue__humanist_reformist", "primogen_toreador") in transfers
    assert ("toreador__predatory_radical", "primogen_brujah") in transfers
    assert ("brujah__predatory_radical", "primogen_toreador") in transfers


def test_transferred_influence_follows_allied_primogens_candidate_choice():
    state = create_initial_game_state()
    votes = self_votes(state)
    votes["primogen_toreador"] = PrimogenVote(
        "primogen_toreador", "primogen_brujah"
    )
    result = resolve_praxis_vote(
        state,
        determine_current_stances(state),
        votes,
        seed_candidates(),
    )
    assert result.candidate_totals["primogen_brujah"] == 139.5
    assert result.winner_id == "primogen_brujah"


def test_coalition_majority_recognises_candidate():
    state = create_initial_game_state()
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_ventrue"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }
    result = resolve_praxis_vote(state, {}, votes, seed_candidates())
    assert result.candidate_totals["primogen_ventrue"] == 139
    assert result.winner_id == "primogen_ventrue"
    assert result.disputed is False


def test_same_loyalty_scores_differ_because_of_ideological_affinity():
    state = create_initial_game_state()
    clan_state = state.clan_states["ventrue"]
    clan_state.current_loyalties["ventrue__humanist_reformist"] = 50
    clan_state.current_loyalties["ventrue__humanist_traditional"] = 50
    stances = determine_current_stances(state)
    assert (
        stances["ventrue__humanist_traditional"].support_score
        > stances["ventrue__humanist_reformist"].support_score
    )


def test_no_votes_yields_disputed_praxis():
    state = create_initial_game_state()
    result = resolve_praxis_vote(state, {}, {}, seed_candidates())
    assert result.disputed is True
    assert result.winner_id is None
