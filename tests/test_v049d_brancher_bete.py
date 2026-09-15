from dataclasses import replace

from game.beast import active_compulsion, trigger_clan_compulsion
from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, PersonalAction, create_player_character
from game.chronicle_simulation import ensure_character_links, initial_simulation
from game.night_cycle import OptionsResolution, resolve_night_event
from game.situations import Situation, SituationChoice
from game.vampire_profile import default_profile


def make_character(
    clan_id: str = "brujah",
    *,
    character_id: str = "pc-v049d",
    hunger: int = 2,
):
    disciplines = {
        "brujah": "Présence",
        "toreador": "Présence",
        "ventrue": "Domination",
    }
    character = create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=f"player-{character_id}",
        player_name="Joueur",
        character_id=character_id,
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=disciplines[clan_id],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Comprendre la Bête",
        chapter_goal="Garder le contrôle",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
    )
    return replace(character, hunger=hunger)


def neutral_situation(*, situation_id: str = "neutral-v049d", difficulty: int = 2):
    choice = SituationChoice(
        id="observe",
        label="Observer calmement",
        description="Rester en retrait et comprendre ce qui se passe.",
        attribute="wits",
        skill="insight",
        difficulty=difficulty,
        legacy_action=PersonalAction.INVESTIGATE,
        effect="political_intel",
    )
    return Situation(
        id=situation_id,
        title="Observer une assemblée",
        body="La discussion continue sans violence.",
        source_actor_id=None,
        tags=("information", "court"),
        choices=(choice,),
    )


def rebel_situation(*, situation_id: str = "rebel-v049d"):
    choice = SituationChoice(
        id="refuse",
        label="Refuser l'ordre",
        description="Contester ouvertement l'autorité qui vous impose sa volonté.",
        attribute="charisma",
        skill="persuasion",
        difficulty=1,
        legacy_action=PersonalAction.ELYSIUM,
        effect="sire_refuse",
    )
    return Situation(
        id=situation_id,
        title="Un ordre que vous refusez",
        body="Une autorité exige votre obéissance.",
        source_actor_id=None,
        tags=("authority", "debate", "revolt"),
        choices=(choice,),
    )


def hunt_situation(*, situation_id: str = "hunt_domain_cour_enlumineurs"):
    choice = SituationChoice(
        id="feed",
        label="Boire",
        description="Vous trouvez une proie et commencez à vous nourrir.",
        attribute="charisma",
        skill="persuasion",
        difficulty=1,
        legacy_action=PersonalAction.HUNT,
        effect="hunt_social",
    )
    return Situation(
        id=situation_id,
        title="Le goût du sang",
        body="Une proie est à portée de crocs.",
        source_actor_id=None,
        tags=("domain", "hunt"),
        choices=(choice,),
    )


def test_compulsion_active_reduit_reellement_le_pool_d_une_action_non_alignee():
    character = make_character("brujah")
    profile = default_profile(character)
    compelled, _ = trigger_clan_compulsion(character, profile, focus="Refuser les ordres")
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = neutral_situation()

    base = resolve_night_event(
        character, profile, simulation, situation, "observe", nights_per_segment=3
    )
    under_compulsion = resolve_night_event(
        character, compelled, simulation, situation, "observe", nights_per_segment=3
    )

    assert under_compulsion.resolution.dice.pool == max(1, base.resolution.dice.pool - 2)
    assert "Compulsion — Rébellion : -2 dés" in under_compulsion.resolution.outcome.detail


def test_action_alignee_reussie_peut_satisfaire_et_effacer_la_compulsion():
    for index in range(40):
        character = make_character("brujah", character_id=f"pc-satisfy-{index}")
        profile, _ = trigger_clan_compulsion(character, default_profile(character), focus="Un ordre injuste")
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        situation = rebel_situation(situation_id=f"rebel-{index}")
        result = resolve_night_event(
            character, profile, simulation, situation, "refuse", nights_per_segment=3
        )
        if result.resolution.dice.success:
            assert result.resolution.profile.current_compulsion is None
            assert "Compulsion Rébellion se dissipe" in result.resolution.outcome.detail
            return
    raise AssertionError("Aucun jet de test n'a réussi l'action alignée")


def test_echec_bestial_hors_chasse_declenche_la_compulsion_du_clan():
    for index in range(120):
        character = make_character("ventrue", character_id=f"pc-bestial-{index}", hunger=5)
        profile = default_profile(character)
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        situation = neutral_situation(situation_id=f"bestial-{index}", difficulty=6)
        result = resolve_night_event(
            character, profile, simulation, situation, "observe", nights_per_segment=3
        )
        if result.resolution.dice.bestial_failure:
            assert result.resolution.profile.current_compulsion == "ventrue_arrogance"
            assert active_compulsion(character, result.resolution.profile) is not None
            assert "Compulsion de clan — Arrogance" in result.resolution.outcome.detail
            return
    raise AssertionError("Aucun échec bestial n'a été produit par les graines de test")


def test_chasse_reussie_a_faim_quatre_declenche_un_test_de_frenesie_et_peut_emporter_le_vampire():
    for index in range(160):
        character = make_character("toreador", character_id=f"pc-hunt-{index}", hunger=4)
        profile = default_profile(character)
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        situation = hunt_situation(situation_id=f"hunt_domain_cour_enlumineurs")
        before_domain = simulation.domains["domain_cour_enlumineurs"]
        result = resolve_night_event(
            character, profile, simulation, situation, "feed", nights_per_segment=3
        )
        if not result.resolution.dice.success:
            continue
        if "frenesie_faim" not in result.resolution.outcome.tags:
            assert "frenesie_faim_resistee" in result.resolution.outcome.tags
            continue

        after_domain = result.resolution.simulation.domains["domain_cour_enlumineurs"]
        assert result.resolution.outcome.updated_character.hunger == 1
        assert result.remaining_actions == 0
        assert after_domain.masquerade_risk == min(3, before_domain.masquerade_risk + 1)
        assert after_domain.pressure == before_domain.pressure + 1
        assert result.resolution.profile.humanity_stains == 0
        return
    raise AssertionError("Aucune graine n'a produit une Frénésie de Faim non résistée")


def test_chevaucher_la_vague_rend_la_frenesie_de_faim_volontaire_si_la_chasse_reussit():
    for index in range(60):
        character = make_character("toreador", character_id=f"pc-wave-{index}", hunger=4)
        profile = default_profile(character)
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        situation = hunt_situation()
        result = resolve_night_event(
            character,
            profile,
            simulation,
            situation,
            "feed",
            nights_per_segment=3,
            options=OptionsResolution(chevaucher_vague_faim=True),
        )
        if result.resolution.dice.success:
            assert "frenesie_faim" in result.resolution.outcome.tags
            assert result.resolution.outcome.updated_character.hunger == 1
            assert result.remaining_actions == 0
            assert "Chevaucher la vague" in result.resolution.outcome.detail
            return
    raise AssertionError("Aucune graine n'a produit une chasse réussie")


def test_chasse_bestiale_ne_cumule_pas_automatiquement_compulsion_et_frenesie():
    for index in range(160):
        character = make_character("brujah", character_id=f"pc-hunt-beast-{index}", hunger=5)
        profile = default_profile(character)
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        situation = hunt_situation()
        result = resolve_night_event(
            character, profile, simulation, situation, "feed", nights_per_segment=3
        )
        if result.resolution.dice.bestial_failure:
            assert result.resolution.profile.current_compulsion is None
            return
    raise AssertionError("Aucun échec bestial de chasse n'a été produit")
