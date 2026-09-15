from dataclasses import replace
from types import SimpleNamespace

from game.chronicle import (
    CHRONICLE_GAME_ID,
    ChronicleProgress,
    PersonalAction,
    create_player_character,
)
from game.chronicle_simulation import ensure_character_links, initial_simulation
from game.consequences import DegreIssue, consequence_graduee, degre_issue
from game.dice import DiceResult
from game.night_cycle import log_entry, resolve_night_event
from game.situations import Situation, SituationChoice
from game.structure_v5 import SYSTEMES_V5, rapport_structure_v5, valider_structure_v5
from game.vampire_profile import default_profile


def _des(*, successes: int, difficulty: int, critical=False, messy=False, bestial=False):
    return DiceResult(
        pool=6,
        difficulty=difficulty,
        hunger=2,
        normal_dice=(6, 7, 2, 3),
        hunger_dice=(8, 4),
        successes=successes,
        margin=successes - difficulty,
        critical=critical,
        messy_critical=messy,
        bestial_failure=bestial,
    )


def _choix(attribute: str = "charisma") -> SituationChoice:
    return SituationChoice(
        id="agir",
        label="Agir",
        description="Tenter quelque chose d'important.",
        attribute=attribute,
        skill="persuasion" if attribute == "charisma" else "athletics",
        difficulty=3,
        legacy_action=PersonalAction.BUILD_RELATION,
        effect="political_voice",
    )


def test_gradation_couvre_reussites_et_echecs():
    assert degre_issue(_des(successes=6, difficulty=3)) == DegreIssue.REUSSITE_EXCEPTIONNELLE
    assert degre_issue(_des(successes=4, difficulty=3)) == DegreIssue.REUSSITE_NETTE
    assert degre_issue(_des(successes=3, difficulty=3)) == DegreIssue.REUSSITE_COUTEUSE
    assert degre_issue(_des(successes=3, difficulty=3, messy=True)) == DegreIssue.REUSSITE_BESTIALE
    assert degre_issue(_des(successes=2, difficulty=3)) == DegreIssue.ECHEC_LIMITE
    assert degre_issue(_des(successes=1, difficulty=3)) == DegreIssue.ECHEC_SERIEUX
    assert degre_issue(_des(successes=0, difficulty=4)) == DegreIssue.ECHEC_GRAVE


def test_gradation_accepte_les_anciens_doubles_sans_marge():
    echec = SimpleNamespace(success=False, bestial_failure=False, critical=False, messy_critical=False)
    reussite = SimpleNamespace(success=True, bestial_failure=False, critical=False, messy_critical=False)
    assert degre_issue(echec) == DegreIssue.ECHEC_SERIEUX
    assert degre_issue(reussite) == DegreIssue.REUSSITE_NETTE


def test_echec_social_grave_use_plus_la_volonte_qu_un_echec_limite():
    choix = _choix("charisma")
    limite = consequence_graduee(choix, _des(successes=2, difficulty=3))
    grave = consequence_graduee(choix, _des(successes=0, difficulty=4))
    assert limite.usure_volonte == 0
    assert grave.usure_volonte == 2


def test_echec_physique_ordinaire_ne_devient_pas_automatiquement_de_la_faim_ou_de_la_volonte():
    choix = _choix("strength")
    grave = consequence_graduee(choix, _des(successes=0, difficulty=4))
    assert grave.usure_volonte == 0
    assert grave.pression_faim == 0


def _character():
    return create_player_character(
        game_id=CHRONICLE_GAME_ID,
        player_id="joueur-v048d",
        player_name="Joueur",
        character_id="pc-v048d",
        name="Jehan",
        clan_id="toreador",
        concept="Nouveau-né",
        starting_discipline="Présence",
        mortal_stance="humanist",
        order_stance="reformist",
        long_term_goal="Trouver ma place",
        chapter_goal="Être entendu",
        progress=ChronicleProgress(game_id=CHRONICLE_GAME_ID),
    )


def test_resolution_de_nuit_expose_le_degre_sans_reveler_le_seuil_dans_le_resume():
    character = _character()
    profile = default_profile(character)
    simulation = ensure_character_links(initial_simulation(CHRONICLE_GAME_ID), character)
    choice = _choix("charisma")
    situation = Situation(
        id="gradation_v048d",
        title="Une parole risquée",
        body="La Cour écoute.",
        source_actor_id=None,
        tags=("politics",),
        choices=(choice,),
    )
    result = resolve_night_event(
        character, profile, simulation, situation, choice.id, nights_per_segment=3,
    )
    assert any(result.resolution.outcome.summary.endswith(f"{degre.value}.") for degre in DegreIssue)
    entry = log_entry("event", result)
    assert entry["degre_issue"] in {item.value for item in DegreIssue}


def test_audit_v5_est_structure_et_identifie_les_lacunes_principales():
    valider_structure_v5()
    report = rapport_structure_v5()
    by_id = {item.id: item for item in SYSTEMES_V5}

    assert report["total"] >= 30
    assert by_id["attributs"].statut == "intégré"
    assert by_id["competences"].statut == "intégré"
    assert by_id["specialites"].statut == "intégré"
    assert by_id["sante"].statut == "intégré"
    assert by_id["guerison"].statut == "intégré"
    assert by_id["principes_chronique"].statut == "intégré"
    assert by_id["humanite"].statut == "partiel"
    assert by_id["frenesie"].statut == "partiel"
    assert by_id["frenesie"].cible == "brancher"
    assert by_id["compulsions"].statut == "partiel"
    assert by_id["historiques"].statut == "partiel"
    assert by_id["combat"].statut == "écarté"
    assert by_id["resonances"].statut == "écarté"


def test_convictions_restent_partielles_mais_le_bonus_maison_n_est_plus_la_cible():
    by_id = {item.id: item for item in SYSTEMES_V5}
    assert by_id["convictions"].statut == "partiel"
    assert "n'obtiennent plus le bonus" in by_id["convictions"].note
