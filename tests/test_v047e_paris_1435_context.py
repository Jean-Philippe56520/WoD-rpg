from game.chronicle_simulation import initial_simulation
from game.historical_sources import historical_source
from game.paris_1435_context import (
    active_historical_political_pressures,
    validate_historical_political_pressures,
)
from game.paris_simulation import parisify_simulation
from game.praxis import assess_praxis_pressure, praxis_pressure_beat


def test_real_history_reference_is_separate_from_wod_lore_tiers():
    source = historical_source("bnf_hundred_years_war")
    assert source.url.startswith("https://classes.bnf.fr/")
    assert "1435" in source.note
    assert "1436" in source.note


def test_1435_collective_pressures_are_sourced_without_inventing_named_leaders():
    validate_historical_political_pressures()
    pressures = active_historical_political_pressures(1435, target_office="prince")
    assert {item.id for item in pressures} == {
        "pressure_english_occupation_1435",
        "pressure_court_miracles_1435",
    }
    assert all(item.target_office == "prince" for item in pressures)
    assert all(item.intensity >= 4 for item in pressures)


def test_1435_pressure_does_not_become_a_permanent_automatic_rule():
    assert active_historical_political_pressures(1434, target_office="prince") == ()
    assert active_historical_political_pressures(1436, target_office="prince") == ()


def test_audited_starting_context_contests_alexandre_without_forcing_his_fall():
    simulation = parisify_simulation(initial_simulation("v047e-context", year=1435))
    assessment = assess_praxis_pressure(simulation)
    beat = praxis_pressure_beat(simulation, ())

    assert simulation.offices["prince"] == "npc_alexandre"
    assert assessment.level == "contested"
    assert assessment.is_critical is False
    assert beat is not None
    assert beat.category == "praxis_pressure"
    assert "Cour des Miracles" not in beat.public_text
    assert "occupation" not in beat.public_text.lower()


def test_same_seed_without_1435_context_is_not_automatically_contested():
    simulation = parisify_simulation(initial_simulation("v047e-context-1436", year=1436))
    assessment = assess_praxis_pressure(simulation)
    assert assessment.level in {"stable", "strained"}
