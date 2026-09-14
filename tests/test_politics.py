from game.models import OppositionStance, PrimogenVote
from game.politics import resolve_praxis_vote
from game.world import seed_candidates, seed_clans


def test_all_oppositions_support_their_primogen():
    clans = seed_clans()
    candidates = seed_candidates()
    stances = {
        clan.id: OppositionStance(clan_id=clan.id, supports_primogen=True)
        for clan in clans
    }
    votes = {
        clan.primogen_id: PrimogenVote(
            primogen_id=clan.primogen_id,
            candidate_id=clan.primogen_id,
        )
        for clan in clans
    }

    result = resolve_praxis_vote(clans, stances, votes, candidates)

    assert result.primogen_weights["primogen_ventrue"] == 100
    assert result.primogen_weights["primogen_toreador"] == 80
    assert result.primogen_weights["primogen_brujah"] == 70
    assert result.winner_id == "primogen_ventrue"
    assert result.disputed is False


def test_dissent_transfers_half_opposition_to_allied_primogen_vote_weight():
    clans = seed_clans()
    candidates = seed_candidates()
    stances = {
        "ventrue": OppositionStance(
            clan_id="ventrue",
            supports_primogen=False,
            allied_primogen_id="primogen_toreador",
        ),
        "toreador": OppositionStance(clan_id="toreador", supports_primogen=True),
        "brujah": OppositionStance(clan_id="brujah", supports_primogen=True),
    }
    votes = {
        "primogen_ventrue": PrimogenVote(
            primogen_id="primogen_ventrue", candidate_id="primogen_ventrue"
        ),
        "primogen_toreador": PrimogenVote(
            primogen_id="primogen_toreador", candidate_id="primogen_toreador"
        ),
        "primogen_brujah": PrimogenVote(
            primogen_id="primogen_brujah", candidate_id="primogen_brujah"
        ),
    }

    result = resolve_praxis_vote(clans, stances, votes, candidates)

    assert result.primogen_weights["primogen_ventrue"] == 80
    assert result.primogen_weights["primogen_toreador"] == 100
    assert result.candidate_totals["primogen_ventrue"] == 80
    assert result.candidate_totals["primogen_toreador"] == 100
    assert result.winner_id == "primogen_toreador"


def test_transferred_influence_follows_allied_primogens_candidate_choice():
    clans = seed_clans()
    candidates = seed_candidates()
    stances = {
        "ventrue": OppositionStance(
            clan_id="ventrue",
            supports_primogen=False,
            allied_primogen_id="primogen_toreador",
        )
    }
    votes = {
        "primogen_ventrue": PrimogenVote(
            primogen_id="primogen_ventrue", candidate_id="primogen_ventrue"
        ),
        "primogen_toreador": PrimogenVote(
            primogen_id="primogen_toreador", candidate_id="primogen_brujah"
        ),
        "primogen_brujah": PrimogenVote(
            primogen_id="primogen_brujah", candidate_id="primogen_brujah"
        ),
    }

    result = resolve_praxis_vote(clans, stances, votes, candidates)

    assert result.primogen_weights["primogen_toreador"] == 100
    assert result.candidate_totals["primogen_brujah"] == 170
    assert result.winner_id == "primogen_brujah"


def test_no_votes_yields_disputed_praxis():
    clans = seed_clans()
    candidates = seed_candidates()

    result = resolve_praxis_vote(clans, {}, {}, candidates)

    assert result.disputed is True
    assert result.winner_id is None
