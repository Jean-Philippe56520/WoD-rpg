from game.models import PrimogenVote
from game.politics import determine_current_stances, resolve_praxis_vote
from game.world import create_initial_game_state, seed_candidates


def self_votes(state):
    return {
        cs.clan.primogen_id: PrimogenVote(cs.clan.primogen_id, cs.clan.primogen_id)
        for cs in state.clan_states.values()
    }


def test_plurality_without_majority_is_disputed_when_all_oppositions_support():
    state = create_initial_game_state()
    result = resolve_praxis_vote(state, {}, self_votes(state), seed_candidates())
    assert result.primogen_weights["primogen_ventrue"] == 67
    assert result.primogen_weights["primogen_toreador"] == 72
    assert result.primogen_weights["primogen_brujah"] == 60
    assert result.total_cast_influence == 199
    assert result.recognition_threshold == 99.5
    assert result.winner_id is None


def test_opposition_stances_follow_leader_effective_relation():
    state = create_initial_game_state()
    stances = determine_current_stances(state)
    assert stances["ventrue"].supports_primogen is False
    assert stances["toreador"].supports_primogen is True
    assert stances["brujah"].supports_primogen is False


def test_dissent_transfers_half_of_opposition_influence_to_allied_primogen():
    state = create_initial_game_state()
    result = resolve_praxis_vote(
        state,
        determine_current_stances(state),
        self_votes(state),
        seed_candidates(),
    )
    transfers = {item["from_clan_id"]: item for item in result.current_transfers}
    assert transfers["ventrue"]["amount"] == 13.5
    assert transfers["ventrue"]["to_primogen_id"] == "primogen_brujah"
    assert transfers["brujah"]["amount"] == 7.5
    assert transfers["brujah"]["to_primogen_id"] == "primogen_ventrue"
    assert result.primogen_weights == {
        "primogen_ventrue": 61.0,
        "primogen_toreador": 72.0,
        "primogen_brujah": 66.0,
    }


def test_transferred_influence_follows_allied_primogens_candidate_choice():
    state = create_initial_game_state()
    votes = self_votes(state)
    votes["primogen_brujah"] = PrimogenVote("primogen_brujah", "primogen_toreador")
    result = resolve_praxis_vote(
        state,
        determine_current_stances(state),
        votes,
        seed_candidates(),
    )
    # Le poids Brujah complet, qui inclut les 13,5 points transférés par
    # l'opposition Ventrue, suit ensuite le choix de vote du Primogène Brujah.
    assert result.candidate_totals["primogen_toreador"] == 138.0


def test_configurable_opposition_transfer_ratio_is_respected():
    state = create_initial_game_state()
    result = resolve_praxis_vote(
        state,
        determine_current_stances(state),
        self_votes(state),
        seed_candidates(),
        opposition_transfer_ratio=0.25,
    )
    transfers = {item["from_clan_id"]: item["amount"] for item in result.current_transfers}
    assert transfers == {"ventrue": 6.75, "brujah": 3.75}
    assert result.primogen_weights["primogen_ventrue"] == 64.0
    assert result.primogen_weights["primogen_brujah"] == 63.0


def test_improving_opposition_leader_relation_can_restore_support():
    state = create_initial_game_state()
    claire = state.characters["ventrue_claire"]
    assert determine_current_stances(state)["ventrue"].supports_primogen is False
    claire.relation_to_primogen = 2
    stance = determine_current_stances(state)["ventrue"]
    assert stance.supports_primogen is True
    assert stance.support_score == 60.0


def test_no_votes_yields_disputed_praxis():
    state = create_initial_game_state()
    result = resolve_praxis_vote(state, {}, {}, seed_candidates())
    assert result.disputed is True
    assert result.winner_id is None
