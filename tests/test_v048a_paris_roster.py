from game.chronicle_simulation import initial_simulation
from game.paris_lore import PARIS_1435_NPCS
from game.paris_roster import (
    COLLECTIVE_ROSTER,
    NAMED_ROSTER,
    OPEN_ROSTER_GAPS,
    PARIS_1435_FACTION_ROSTER,
    ROSTER_BY_ID,
    ROSTER_CONFLICTS,
    roster_audit_report,
    roster_entry,
    validate_paris_1435_roster,
)
from game.paris_simulation import parisify_simulation
from scripts.lore_audit_report import build_report


def test_roster_is_valid_and_exactly_gates_named_simulation_seed():
    validate_paris_1435_roster()
    seeded = {seed.id for seed in PARIS_1435_NPCS}
    active = {entry.id for entry in NAMED_ROSTER if entry.simulation_policy == "active_named"}
    assert active == seeded
    assert all(ROSTER_BY_ID[actor_id].certainty in {"certain", "high", "medium"} for actor_id in active)


def test_uncertain_or_historical_named_actors_cannot_become_active_npcs():
    for actor_id in ("npc_childeberd", "npc_louis_orleans", "npc_henri_orleans", "npc_helene"):
        entry = roster_entry(actor_id)
        assert entry.status in {"unverified", "historical"}
        assert entry.simulation_policy == "forbidden"
        assert entry.can_act_as_named_npc is False

    state = parisify_simulation(initial_simulation("v048a-uncertain", year=1435))
    assert all(actor_id not in state.npcs for actor_id in (
        "npc_childeberd",
        "npc_louis_orleans",
        "npc_henri_orleans",
        "npc_helene",
    ))


def test_external_powers_remain_contextual_or_explicitly_external():
    mithras = roster_entry("npc_mithras")
    burgundy = roster_entry("npc_anne_bourgogne")
    henri = roster_entry("npc_henri_preux")

    assert mithras.status == "external"
    assert mithras.simulation_policy == "context_only"
    assert burgundy.status == "external"
    assert burgundy.clan_id is None
    assert burgundy.simulation_policy == "context_only"
    assert henri.status == "external"
    assert henri.simulation_policy == "active_named"


def test_court_of_miracles_is_represented_by_collectives_without_invented_leader():
    faction = next(item for item in PARIS_1435_FACTION_ROSTER if item.faction_id == "faction_court_miracles")
    members = tuple(ROSTER_BY_ID[member_id] for member_id in faction.member_entry_ids)

    assert {member.clan_id for member in members} == {"brujah", "malkavian", "gangrel", "nosferatu"}
    assert all(member.kind == "collective" for member in members)
    assert all(member.status == "present" for member in members)
    assert all(member.simulation_policy == "context_only" for member in members)
    assert not any(entry.kind == "named_vampire" and entry.id in faction.member_entry_ids for entry in NAMED_ROSTER)


def test_tremere_remain_collective_only_and_never_gain_a_fake_1435_member():
    tremere = roster_entry("collective_tremere_paris")
    assert tremere.kind == "collective"
    assert tremere.certainty == "medium"
    assert tremere.simulation_policy == "context_only"

    state = parisify_simulation(initial_simulation("v048a-tremere", year=1435))
    assert "collective_tremere_paris" not in state.npcs
    assert not any(npc.clan_id == "tremere" for npc in state.npcs.values())


def test_gargoyles_are_collective_context_only_not_named_ferox_by_assumption():
    gargoyles = roster_entry("collective_gargoyle_paris")
    assert gargoyles.status == "present"
    assert gargoyles.kind == "collective"
    assert gargoyles.simulation_policy == "context_only"
    assert "npc_ferox" not in ROSTER_BY_ID


def test_lasombra_are_explicitly_absent_instead_of_silently_omitted():
    lasombra = roster_entry("collective_lasombra_paris")
    assert lasombra.status == "absent"
    assert lasombra.simulation_policy == "forbidden"

    state = parisify_simulation(initial_simulation("v048a-lasombra", year=1435))
    assert not any(npc.clan_id == "lasombra" for npc in state.npcs.values())


def test_roster_preserves_known_conflict_and_open_gaps():
    assert any(conflict.id == "pompignan_torpor_vs_1481" for conflict in ROSTER_CONFLICTS)
    assert len(OPEN_ROSTER_GAPS) >= 8
    assert any("Brujah" in gap for gap in OPEN_ROSTER_GAPS)
    assert any("Tremere" in gap for gap in OPEN_ROSTER_GAPS)


def test_roster_report_counts_named_collective_and_uncertain_entries():
    report = roster_audit_report()
    assert report["entries_total"] == len(NAMED_ROSTER) + len(COLLECTIVE_ROSTER)
    assert report["named_total"] >= 14
    assert report["collective_total"] >= 9
    assert report["simulation_active_named"] == len(PARIS_1435_NPCS)
    assert report["named_unverified"] >= 3
    assert report["collective_present"] >= 7
    assert report["collective_absent"] >= 1
    assert report["open_gaps"] >= 8


def test_lore_qa_schema_v3_exposes_roster_and_does_not_hide_gaps():
    report = build_report(1435)
    assert report["schema_version"] == 3
    assert report["roster_1435"]["entries_total"] >= 23
    assert report["roster_entries"]
    assert len(report["roster_open_gaps"]) >= 8
    assert any(item["id"] == "pompignan_torpor_vs_1481" for item in report["roster_conflicts"])
