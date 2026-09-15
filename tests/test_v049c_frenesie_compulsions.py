from dataclasses import replace
from types import SimpleNamespace

from game.beast import (
    TypeFrenesie,
    active_compulsion,
    beast_result_can_trigger_compulsion,
    compulsion_definition,
    compulsion_pool_modifier,
    compulsion_satisfied,
    frenzy_pool,
    resoudre_frenesie,
    trigger_clan_compulsion,
)
from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, create_player_character
from game.mecaniques_vampiriques import severite_fleau
from game.vampire_profile import default_profile, profile_from_dict, profile_to_dict


def make_character(clan_id: str = "brujah"):
    disciplines = {
        "brujah": "Présence",
        "toreador": "Présence",
        "ventrue": "Domination",
    }
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id=f"player-v049c-{clan_id}",
        player_name="Joueur",
        character_id=f"pc-v049c-{clan_id}",
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


def fake_situation(*tags: str):
    return SimpleNamespace(tags=tuple(tags), title="Une provocation")


def fake_choice(effect: str = "political_intel", skill: str = "insight"):
    return SimpleNamespace(effect=effect, skill=skill)


def test_severite_fleau_suit_la_table_v5_corrigee():
    assert severite_fleau(0) == 0
    assert severite_fleau(1) == 2
    assert severite_fleau(2) == 2
    assert severite_fleau(3) == 3
    assert severite_fleau(5) == 4
    assert severite_fleau(7) == 5
    assert severite_fleau(10) == 6


def test_pool_frenesie_utilise_volonte_restante_plus_un_tiers_humanite():
    character = make_character("toreador")
    profile = default_profile(character)

    assert profile.willpower == 4
    assert frenzy_pool(profile, 7, "toreador", TypeFrenesie.FAIM) == 6


def test_fleau_brujah_retranche_la_severite_uniquement_a_la_fureur():
    character = make_character("brujah")
    profile = default_profile(character)
    normal = profile.willpower + character.humanity // 3

    assert profile.blood_potency == 1
    assert frenzy_pool(profile, character.humanity, "brujah", TypeFrenesie.FUREUR) == normal - 2
    assert frenzy_pool(profile, character.humanity, "brujah", TypeFrenesie.FAIM) == normal
    assert frenzy_pool(profile, character.humanity, "brujah", TypeFrenesie.TERREUR) == normal


def test_test_frenesie_est_deterministe_et_n_utilise_aucun_de_de_faim():
    character = make_character("ventrue")
    profile = default_profile(character)

    first = resoudre_frenesie(
        profile,
        humanity=character.humanity,
        clan_id=character.clan_id,
        frenzy_type=TypeFrenesie.FAIM,
        difficulty=3,
        seed="faim-v049c",
    )
    second = resoudre_frenesie(
        profile,
        humanity=character.humanity,
        clan_id=character.clan_id,
        frenzy_type=TypeFrenesie.FAIM,
        difficulty=3,
        seed="faim-v049c",
    )

    assert first == second
    assert first.dice is not None
    assert first.dice.hunger == 0
    assert first.dice.hunger_dice == ()
    assert first.resisted == first.dice.success


def test_chevaucher_la_vague_declenche_la_frenesie_sans_test():
    character = make_character("toreador")
    profile = default_profile(character)

    result = resoudre_frenesie(
        profile,
        humanity=character.humanity,
        clan_id=character.clan_id,
        frenzy_type=TypeFrenesie.TERREUR,
        difficulty=4,
        seed="wave-v049c",
        ride_wave=True,
    )

    assert result.rode_wave
    assert not result.resisted
    assert result.dice is None


def test_les_trois_clans_jouables_ont_leur_compulsion_v5():
    assert compulsion_definition("brujah").nom == "Rébellion"
    assert compulsion_definition("toreador").nom == "Obsession"
    assert compulsion_definition("ventrue").nom == "Arrogance"


def test_compulsion_est_limitee_a_la_nuit_significative_qui_l_a_produite():
    character = make_character("brujah")
    profile = default_profile(character)
    compelled, definition = trigger_clan_compulsion(character, profile, focus="Le sire exige obéissance")

    assert active_compulsion(character, compelled) == definition
    next_night = replace(character, local_night=character.local_night + 1)
    assert active_compulsion(next_night, compelled) is None


def test_rebellion_brujah_penalise_les_actions_hors_opposition_et_peut_etre_satisfaite():
    character = make_character("brujah")
    profile, _ = trigger_clan_compulsion(character, default_profile(character), focus="Un ordre injuste")

    neutral = fake_situation("information")
    neutral_choice = fake_choice("political_intel", "insight")
    rebel = fake_situation("authority", "debate")
    rebel_choice = fake_choice("sire_refuse", "politics")

    assert compulsion_pool_modifier(character, profile, neutral, neutral_choice) == -2
    assert compulsion_pool_modifier(character, profile, rebel, rebel_choice) == 0
    assert compulsion_satisfied(character, profile, rebel, rebel_choice, success=True)
    assert not compulsion_satisfied(character, profile, rebel, rebel_choice, success=False)


def test_obsession_toreador_et_arrogance_ventrue_reconnaissent_leurs_actions_alignees():
    toreador = make_character("toreador")
    tore_profile, _ = trigger_clan_compulsion(toreador, default_profile(toreador), focus="Un manuscrit enluminé")
    assert compulsion_pool_modifier(
        toreador,
        tore_profile,
        fake_situation("art", "patronage"),
        fake_choice("political_voice", "persuasion"),
    ) == 0

    ventrue = make_character("ventrue")
    ven_profile, _ = trigger_clan_compulsion(ventrue, default_profile(ventrue), focus="Une assemblée hésitante")
    assert compulsion_pool_modifier(
        ventrue,
        ven_profile,
        fake_situation("authority"),
        fake_choice("political_voice", "leadership"),
    ) == 0
    assert compulsion_pool_modifier(
        ventrue,
        ven_profile,
        fake_situation("information"),
        fake_choice("political_intel", "insight"),
    ) == -2


def test_resultat_bestial_ou_critique_bestial_peut_declencher_une_compulsion():
    assert beast_result_can_trigger_compulsion(SimpleNamespace(bestial_failure=True, messy_critical=False))
    assert beast_result_can_trigger_compulsion(SimpleNamespace(bestial_failure=False, messy_critical=True))
    assert not beast_result_can_trigger_compulsion(SimpleNamespace(bestial_failure=False, messy_critical=False))


def test_compulsion_persiste_dans_le_json_et_migre_le_schema():
    character = make_character("toreador")
    profile, definition = trigger_clan_compulsion(character, default_profile(character), focus="Une icône")
    restored = profile_from_dict(profile_to_dict(profile))

    assert restored.current_compulsion == definition.id
    assert restored.compulsion_focus == "Une icône"
    assert restored.compulsion_scope == f"{character.chapter}:{character.segment}:{character.local_night}"
    assert restored.schema_version == 5
