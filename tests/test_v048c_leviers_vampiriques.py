from dataclasses import replace

from game.chronicle import (
    CHRONICLE_GAME_ID,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
)
from game.chronicle_simulation import ensure_character_links, initial_simulation
from game.dice import DiceResult, roll_pool
from game.mecaniques_vampiriques import (
    bonus_coup_de_sang,
    perte_volonte_apres_echec,
    recuperer_volonte_fin_nuit,
    usage_discipline,
)
from game.night_cycle import OptionsResolution, resolve_night_event
from game.situations import Situation, SituationChoice
from game.vampire_profile import default_profile, profile_to_dict


def make_character(
    clan_id: str = "toreador",
    *,
    discipline: str = "Présence",
    character_id: str = "pc-v048c",
):
    progress = ChronicleProgress(game_id=CHRONICLE_GAME_ID)
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="player-v048c",
        player_name="Joueur",
        character_id=character_id,
        name="Jehan",
        clan_id=clan_id,
        concept="Nouveau-né",
        starting_discipline=discipline,
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Comprendre la Cour",
        chapter_goal="Gagner du poids",
        progress=progress,
    )


def situation_sociale(*, difficulty: int = 3) -> Situation:
    choix = SituationChoice(
        id="convaincre",
        label="Convaincre l'interlocuteur",
        description="Faire valoir votre position sans menace ouverte.",
        attribute="charisma",
        skill="persuasion",
        difficulty=difficulty,
        legacy_action=PersonalAction.BUILD_RELATION,
        effect="political_voice",
    )
    return Situation(
        id="discussion_v048c",
        title="Une discussion délicate",
        body="Un Caïnite écoute votre proposition.",
        source_actor_id=None,
        tags=("politics", "diplomacy"),
        choices=(choix,),
    )


def test_volonte_relance_uniquement_les_des_ordinaires_en_echec():
    for index in range(100):
        seed = f"volonte-{index}"
        base = roll_pool(pool=8, hunger=2, difficulty=4, seed=seed)
        echecs_ordinaires = sum(value < 6 for value in base.normal_dice)
        if echecs_ordinaires:
            relance = roll_pool(pool=8, hunger=2, difficulty=4, seed=f"{seed}@volonte")
            assert relance.hunger_dice == base.hunger_dice
            assert relance.pool == base.pool
            assert relance.difficulty == base.difficulty
            assert relance.relances_volonte == min(3, echecs_ordinaires)
            return
    raise AssertionError("Aucune graine de test n'a produit de dé ordinaire en échec")


def test_table_du_coup_de_sang_suit_la_puissance_du_sang():
    assert bonus_coup_de_sang(0) == 1
    assert bonus_coup_de_sang(1) == 2
    assert bonus_coup_de_sang(2) == 2
    assert bonus_coup_de_sang(3) == 3
    assert bonus_coup_de_sang(5) == 4
    assert bonus_coup_de_sang(7) == 5
    assert bonus_coup_de_sang(10) == 6


def test_bonus_temporaire_ne_pollue_pas_la_sauvegarde_du_profil():
    character = make_character()
    profile = default_profile(character)
    renforce = replace(profile, bonus_resolution=2)

    assert renforce.pool("charisma", "persuasion") == profile.pool("charisma", "persuasion") + 2
    assert "bonus_resolution" not in profile_to_dict(renforce)
    assert renforce.volonte_maximale == renforce.attributes["resolve"] + renforce.attributes["composure"]


def test_presence_reverence_est_proposee_sur_une_persuasion():
    character = make_character(discipline="Présence")
    profile = default_profile(character)
    situation = situation_sociale()

    usage = usage_discipline(profile, situation, situation.choices[0])

    assert usage is not None
    assert usage.discipline == "Présence"
    assert usage.pouvoir == "Révérence"
    assert usage.bonus_des == 1


def test_auspex_sens_accrus_est_reserve_a_observation():
    character = make_character(discipline="Auspex")
    profile = default_profile(character)
    choix = SituationChoice(
        id="observer",
        label="Observer",
        description="Lire les détails de la scène.",
        attribute="wits",
        skill="insight",
        difficulty=3,
        legacy_action=PersonalAction.INVESTIGATE,
        effect="political_intel",
    )
    situation = Situation(
        id="observation_v048c",
        title="Observer la Cour",
        body="Les détails comptent.",
        source_actor_id=None,
        tags=("information",),
        choices=(choix,),
    )

    usage = usage_discipline(profile, situation, choix)

    assert usage is not None
    assert usage.discipline == "Auspex"
    assert usage.pouvoir == "Sens accrus"


def test_coup_de_sang_augmente_le_groupement_sans_bonus_persistant():
    character = make_character()
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    situation = situation_sociale()

    base = resolve_night_event(
        character,
        profile,
        simulation,
        situation,
        "convaincre",
        nights_per_segment=3,
    )
    renforce = resolve_night_event(
        character,
        profile,
        simulation,
        situation,
        "convaincre",
        nights_per_segment=3,
        options=OptionsResolution(coup_de_sang=True),
    )

    assert renforce.resolution.dice.pool == base.resolution.dice.pool + 2
    assert renforce.resolution.profile.bonus_resolution == 0
    assert "Coup de Sang" in renforce.resolution.outcome.detail
    assert "Test d’Exaltation" in renforce.resolution.outcome.detail


def test_depense_de_volonte_est_persistante_si_une_relance_a_lieu():
    situation = situation_sociale(difficulty=4)
    for index in range(60):
        character = make_character(character_id=f"pc-v048c-{index}")
        profile = default_profile(character)
        simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
        resultat = resolve_night_event(
            character,
            profile,
            simulation,
            situation,
            "convaincre",
            nights_per_segment=3,
            options=OptionsResolution(depenser_volonte=True),
        )
        if resultat.resolution.dice.relances_volonte:
            usure_echec = perte_volonte_apres_echec(
                resultat.resolution.choice,
                resultat.resolution.dice,
            )
            attendu = max(0, profile.willpower - 1 - usure_echec)
            assert resultat.resolution.profile.willpower == attendu
            assert "Volonté : 1 point dépensé" in resultat.resolution.outcome.detail
            return
    raise AssertionError("Aucune graine de résolution n'a produit de relance de Volonté")


def test_echec_mental_social_grave_use_la_volonte_mais_pas_echec_physique():
    echec = DiceResult(
        pool=4,
        difficulty=4,
        hunger=1,
        normal_dice=(2, 3, 4),
        hunger_dice=(5,),
        successes=0,
        margin=-4,
        critical=False,
        messy_critical=False,
        bestial_failure=False,
    )
    social = situation_sociale(difficulty=4).choices[0]
    physique = replace(social, attribute="strength", skill="brawl")

    assert perte_volonte_apres_echec(social, echec) == 2
    assert perte_volonte_apres_echec(physique, echec) == 0


def test_recuperation_de_volonte_est_plafonnee_par_la_fiche():
    character = make_character()
    profile = default_profile(character)
    epuise = replace(profile, willpower=0)

    recupere, gain = recuperer_volonte_fin_nuit(epuise)

    assert gain == max(profile.attributes["resolve"], profile.attributes["composure"])
    assert recupere.willpower == gain
    assert recupere.willpower <= profile.volonte_maximale
