from dataclasses import replace

import pytest

from game.chronicle import CHRONICLE_GAME_ID, ChronicleProgress, create_player_character
from game.health import TypeDegat, appliquer_degats_sante
from game.vampire_profile import (
    SKILL_LABELS_1435,
    SKILL_NAMES,
    default_profile,
    profile_from_dict,
    profile_to_dict,
)


def make_character(clan_id: str = "brujah"):
    disciplines = {
        "brujah": "Présence",
        "toreador": "Présence",
        "ventrue": "Domination",
    }
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-v049a",
        player_name="Joueur",
        character_id="pc-v049a",
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=disciplines[clan_id],
        mortal_stance="humanist",
        order_stance="orthodox",
        long_term_goal="Trouver ma place",
        chapter_goal="Survivre aux premières nuits",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
    )


def test_fiche_expose_les_27_competences_v5_avec_libelles_1435():
    profile = default_profile(make_character())

    assert len(SKILL_NAMES) == 27
    assert set(profile.skills) == set(SKILL_NAMES)
    assert set(SKILL_LABELS_1435) == set(SKILL_NAMES)
    assert SKILL_LABELS_1435["firearms"] == "Tir"
    assert SKILL_LABELS_1435["technology"] == "Techniques"
    assert SKILL_LABELS_1435["drive"] == "Conduite & monte"


def test_ancienne_sauvegarde_complete_les_competences_manquantes_sans_perdre_les_scores():
    profile = default_profile(make_character())
    data = profile_to_dict(profile)
    data["skills"] = {
        "brawl": 2,
        "politics": 1,
        "awareness": 1,
    }
    data.pop("specialties")
    data.pop("health_superficial")
    data.pop("health_aggravated")
    data["schema_version"] = 2

    migrated = profile_from_dict(data)

    assert len(migrated.skills) == 27
    assert migrated.skills["brawl"] == 2
    assert migrated.skills["politics"] == 1
    assert migrated.skills["melee"] == 0
    assert migrated.specialties == {}
    assert migrated.health_superficial == 0
    assert migrated.health_aggravated == 0
    assert migrated.schema_version == 3


def test_specialite_pertinente_ajoute_exactement_un_de():
    profile = default_profile(make_character("ventrue"))
    specialise = replace(profile, specialties={"persuasion": ("Cour",)})

    base = profile.pool("charisma", "persuasion")

    assert specialise.pool("charisma", "persuasion", specialty="Cour") == base + 1
    assert specialise.pool("charisma", "persuasion", specialty="Marchands") == base


def test_specialite_exige_une_competence_connue_et_au_moins_un_point():
    profile = default_profile(make_character())

    with pytest.raises(ValueError):
        replace(profile, specialties={"science": ("Astres",)})

    with pytest.raises(ValueError):
        replace(profile, specialties={"inconnue": ("Quelque chose",)})


def test_sante_maximale_est_vigueur_plus_trois_et_persiste():
    profile = default_profile(make_character())
    blesse = replace(profile, health_superficial=2, health_aggravated=1)
    restored = profile_from_dict(profile_to_dict(blesse))

    assert profile.sante_maximale == profile.attributes["stamina"] + 3
    assert restored.health_superficial == 2
    assert restored.health_aggravated == 1
    assert restored.sante_restante == restored.sante_maximale - 3


def test_degats_superficiels_d_un_vampire_sont_divises_par_deux_arrondis_au_superieur():
    profile = default_profile(make_character())

    result = appliquer_degats_sante(profile, 3, TypeDegat.SUPERFICIEL)

    assert result.degats_appliques == 2
    assert result.profile.health_superficial == 2
    assert result.profile.health_aggravated == 0


def test_piste_pleine_diminue_les_pools_physiques_de_deux_pas_les_sociaux():
    profile = default_profile(make_character("brujah"))
    diminue = replace(profile, health_superficial=profile.sante_maximale)

    assert diminue.est_diminue
    assert diminue.pool("strength", "brawl") == max(1, profile.pool("strength", "brawl") - 2)
    assert diminue.pool("charisma", "persuasion") == profile.pool("charisma", "persuasion")


def test_degats_supplementaires_sur_piste_pleine_convertissent_les_superficiels_en_aggraves():
    profile = default_profile(make_character())
    plein = replace(profile, health_superficial=profile.sante_maximale)

    result = appliquer_degats_sante(plein, 2, TypeDegat.SUPERFICIEL)

    # 2 dégâts superficiels bruts deviennent 1 niveau après division V5.
    assert result.superficiels_convertis == 1
    assert result.profile.health_superficial == profile.sante_maximale - 1
    assert result.profile.health_aggravated == 1
    assert result.diminue


def test_piste_entierement_aggravee_place_un_vampire_en_torpeur():
    profile = default_profile(make_character())
    plein = replace(profile, health_superficial=profile.sante_maximale)

    result = appliquer_degats_sante(plein, profile.sante_maximale, TypeDegat.AGGRAVE)

    assert result.profile.health_superficial == 0
    assert result.profile.health_aggravated == profile.sante_maximale
    assert result.torpeur
    assert result.profile.en_torpeur_par_degats


def test_la_piste_ne_peut_pas_etre_creee_surchargee():
    profile = default_profile(make_character())

    with pytest.raises(ValueError):
        replace(profile, health_superficial=profile.sante_maximale, health_aggravated=1)
