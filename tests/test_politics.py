from game.models import OppositionStance, PrimogenVote
from game.politics import resolve_praxis_vote
from game.world import seed_candidates, seed_clans


def _self_votes(clans):
    return {
        clan.primogen_id: PrimogenVote(clan.primogen_id, clan.primogen_id)
        for clan in clans
    }


def test_plurality_without_majority_is_disputed():
    clans = seed_clans()
    result = resolve_praxis_vote(
        clans,
        {clan.id: OppositionStance(clan.id, True) for clan in clans},
        _self_votes(clans),
        seed_candidates(),
    )

    assert result.primogen_weights["primogen_ventrue"] == 100
    assert result.total_cast_influence == 250
    assert result.recognition_threshold == 125
    assert result.winner_id is None
    assert result.disputed is True


def test_dissent_transfers_half_opposition_to_allied_primogen_vote_weight():
    clans = seed_clans()
    stances = {
        "ventrue": OppositionStance("ventrue", False, "primogen_toreador"),
        "toreador": OppositionStance("toreador", True),
        "brujah": OppositionStance("brujah", True),
    }

    result = resolve_praxis_vote(clans, stances, _self_votes(clans), seed_candidates())

    assert result.primogen_weights["primogen_ventrue"] == 80
    assert result.primogen_weights["primogen_toreador"] == 100
    assert result.candidate_totals["primogen_ventrue"] == 80
    assert result.candidate_totals["primogen_toreador"] == 100


def test_transferred_influence_follows_allied_primogens_candidate_choice():
    clans = seed_clans()
    stances = {
        "ventrue": OppositionStance("ventrue", False, "primogen_toreador")
    }
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_brujah"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }

    result = resolve_praxis_vote(clans, stances, votes, seed_candidates())

    assert result.primogen_weights["primogen_toreador"] == 100
    assert result.candidate_totals["primogen_brujah"] == 170
    assert result.winner_id == "primogen_brujah"


def test_coalition_majority_recognises_candidate():
    clans = seed_clans()
    votes = {
        "primogen_ventrue": PrimogenVote("primogen_ventrue", "primogen_ventrue"),
        "primogen_toreador": PrimogenVote("primogen_toreador", "primogen_ventrue"),
        "primogen_brujah": PrimogenVote("primogen_brujah", "primogen_brujah"),
    }
    result = resolve_praxis_vote(clans, {}, votes, seed_candidates())

    assert result.candidate_totals["primogen_ventrue"] == 180
    assert result.winner_id == "primogen_ventrue"
    assert result.disputed is False


def test_no_votes_yields_disputed_praxis():
    result = resolve_praxis_vote(seed_clans(), {}, {}, seed_candidates())
    assert result.disputed is True
    assert result.winner_id is None
