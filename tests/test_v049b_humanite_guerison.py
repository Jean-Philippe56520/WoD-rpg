from dataclasses import replace

import pytest

from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, create_player_character
from game.health import montant_guerison_superficielle, soigner_aggrave, soigner_superficiels
from game.humanity import (
    PRINCIPES_CHRONIQUE,
    appliquer_fletrissures,
    capacite_fletrissures,
    pool_remords,
    resoudre_remords,
)
from game.morality_stakes import ENJEUX_MORAUX, enjeu_pour_entree_log
from game.vampire_profile import default_profile, profile_for_creation, profile_from_dict, profile_to_dict


def make_character():
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-v049b",
        player_name="Joueur",
        character_id="pc-v049b",
        name="Jehan",
        clan_id="toreador",
        concept="Nouveau-né",
        starting_discipline="Présence",
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Comprendre la Cour",
        chapter_goal="Survivre",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
    )


def test_table_de_guerison_corrigee_suit_la_puissance_du_sang():
    assert montant_guerison_superficielle(0) == 1
    assert montant_guerison_superficielle(1) == 1
    assert montant_guerison_superficielle(2) == 2
    assert montant_guerison_superficielle(4) == 3
    assert montant_guerison_superficielle(8) == 4
    assert montant_guerison_superficielle(10) == 5


def test_un_test_exaltation_soigne_les_superficiels_selon_la_puissance_du_sang():
    profile = replace(default_profile(make_character()), blood_potency=4, health_superficial=4)
    result = soigner_superficiels(profile, hunger=2, seed="mend-superficial")

    assert len(result.des_exaltation) == 1
    assert result.superficiels_soignes == 3
    assert result.profile.health_superficial == 1
    assert result.faim in {2, 3}


def test_faim_cinq_bloque_une_guerison_volontaire():
    profile = replace(default_profile(make_character()), health_superficial=1)
    with pytest.raises(ValueError):
        soigner_superficiels(profile, hunger=5, seed="blocked")


def test_trois_tests_exaltation_soignent_un_aggrave_si_l_effort_va_au_bout():
    profile = replace(default_profile(make_character()), health_aggravated=1)
    for index in range(200):
        result = soigner_aggrave(profile, hunger=0, seed=f"aggrave-{index}")
        if result.complete:
            assert len(result.des_exaltation) == 3
            assert result.aggraves_soignes == 1
            assert result.profile.health_aggravated == 0
            return
    raise AssertionError("Aucune graine n'a permis de terminer les trois Tests d'Exaltation")


def test_guerison_aggravee_s_interrompt_si_la_faim_atteint_cinq():
    profile = replace(default_profile(make_character()), health_aggravated=1)
    for index in range(200):
        result = soigner_aggrave(profile, hunger=4, seed=f"aggrave-stop-{index}")
        if not result.complete:
            assert result.faim == 5
            assert result.profile.health_aggravated == 1
            assert len(result.des_exaltation) < 3
            return
    raise AssertionError("Aucune graine n'a provoqué l'interruption attendue")


def test_fletrissures_utilisent_les_cases_vides_de_la_piste_humanite():
    character = make_character()
    profile = default_profile(character)

    assert capacite_fletrissures(character.humanity) == 3
    result = appliquer_fletrissures(character, profile, 2)

    assert result.profile.humanity_stains == 2
    assert result.ajoutees == 2
    assert result.debordement == 0
    assert pool_remords(character, result.profile) == 1


def test_conviction_peut_mitiger_une_fletrissure_explicitement_pertinente():
    character = make_character()
    profile = default_profile(character)

    result = appliquer_fletrissures(character, profile, 2, conviction_protege=True)

    assert result.mitigees == 1
    assert result.ajoutees == 1


def test_remords_efface_toujours_les_fletrissures_et_ne_fait_perdre_qu_un_point_humanite():
    character = make_character()
    profile = replace(default_profile(character), humanity_stains=2)
    observed = set()

    for index in range(300):
        result = resoudre_remords(character, profile, seed=f"remords-{index}")
        observed.add(result.succes)
        assert result.profile.humanity_stains == 0
        assert result.personnage.humanity in {character.humanity, character.humanity - 1}
        assert result.humanite_perdue in {0, 1}
        if len(observed) == 2:
            break

    assert observed == {True, False}


def test_fletrissures_persistent_dans_le_json_du_profil():
    profile = replace(default_profile(make_character()), humanity_stains=2)
    restored = profile_from_dict(profile_to_dict(profile))
    assert restored.humanity_stains == 2
    assert restored.schema_version == 5


def test_nouvelles_convictions_ne_donnent_plus_de_bonus_de_competence_maison():
    character = make_character()
    base = default_profile(character)
    created = profile_for_creation(character, conviction_id="keep_word")

    assert created.skills == base.skills
    assert created.convictions == ("keep_word",)


def test_principes_sont_structures_et_les_echecs_de_des_ne_sont_pas_des_transgressions_implicites():
    assert len(PRINCIPES_CHRONIQUE) >= 3
    assert len({item.id for item in PRINCIPES_CHRONIQUE}) == len(PRINCIPES_CHRONIQUE)
    assert ENJEUX_MORAUX == ()
    assert enjeu_pour_entree_log({"situation_id": "x", "choice_id": "y"}) is None
