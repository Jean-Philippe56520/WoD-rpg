from __future__ import annotations

from .ideology import initialize_current_politics
from .models import Candidate, Character, Clan, ClanPoliticalState, GameState


def seed_characters() -> dict[str, Character]:
    return {
        "primogen_ventrue": Character(
            id="primogen_ventrue", name="Adrien de Keravel", clan_id="ventrue",
            personal_influence=22, humanity=6, humanism=-50, tradition=70,
            loyalty=75, ambition=85, is_primogen=True,
        ),
        "ventrue_claire": Character(
            id="ventrue_claire", name="Claire Beaumont", clan_id="ventrue",
            personal_influence=15, humanity=7, humanism=60, tradition=-65,
            loyalty=30, ambition=80,
        ),
        "ventrue_victor": Character(
            id="ventrue_victor", name="Victor de Keravel", clan_id="ventrue",
            personal_influence=18, humanity=6, humanism=-30, tradition=55,
            loyalty=75, ambition=65,
        ),
        "ventrue_helene": Character(
            id="ventrue_helene", name="Helene Beaumont", clan_id="ventrue",
            personal_influence=12, humanity=7, humanism=35, tradition=45,
            loyalty=45, ambition=55,
        ),
        "primogen_toreador": Character(
            id="primogen_toreador", name="Elise Valmont", clan_id="toreador",
            personal_influence=21, humanity=7, humanism=60, tradition=35,
            loyalty=70, ambition=80, is_primogen=True,
        ),
        "toreador_lucien": Character(
            id="toreador_lucien", name="Lucien Marceau", clan_id="toreador",
            personal_influence=14, humanity=7, humanism=50, tradition=-55,
            loyalty=40, ambition=78,
        ),
        "toreador_camille": Character(
            id="toreador_camille", name="Camille Vernier", clan_id="toreador",
            personal_influence=17, humanity=7, humanism=35, tradition=45,
            loyalty=72, ambition=62,
        ),
        "toreador_gabriel": Character(
            id="toreador_gabriel", name="Gabriel Sorel", clan_id="toreador",
            personal_influence=11, humanity=8, humanism=-45, tradition=-40,
            loyalty=48, ambition=58,
        ),
        "toreador_noemie": Character(
            id="toreador_noemie", name="Noemie Varenne", clan_id="toreador",
            personal_influence=9, humanity=6, humanism=-25, tradition=50,
            loyalty=52, ambition=61,
        ),
        "primogen_brujah": Character(
            id="primogen_brujah", name="Marcus Le Guen", clan_id="brujah",
            personal_influence=19, humanity=7, humanism=30, tradition=-45,
            loyalty=68, ambition=76, is_primogen=True,
        ),
        "brujah_sarah": Character(
            id="brujah_sarah", name="Sarah Morel", clan_id="brujah",
            personal_influence=15, humanity=7, humanism=-40, tradition=-60,
            loyalty=35, ambition=82,
        ),
        "brujah_yann": Character(
            id="brujah_yann", name="Yann Kergoat", clan_id="brujah",
            personal_influence=16, humanity=6, humanism=50, tradition=-30,
            loyalty=70, ambition=64,
        ),
        "brujah_ines": Character(
            id="brujah_ines", name="Ines Le Floch", clan_id="brujah",
            personal_influence=10, humanity=8, humanism=55, tradition=30,
            loyalty=52, ambition=50,
        ),
    }


def seed_clans() -> list[Clan]:
    return [
        Clan(id="ventrue", name="Ventrue", primogen_id="primogen_ventrue"),
        Clan(id="toreador", name="Toreador", primogen_id="primogen_toreador"),
        Clan(id="brujah", name="Brujah", primogen_id="primogen_brujah"),
    ]


def seed_candidates() -> list[Candidate]:
    chars = seed_characters()
    return [
        Candidate(id=char.id, name=char.name, clan_id=char.clan_id, is_primogen=True)
        for char in chars.values()
        if char.is_primogen
    ]


def candidates_from_state(state: GameState) -> list[Candidate]:
    return [
        Candidate(id=char.id, name=char.name, clan_id=char.clan_id, is_primogen=char.is_primogen)
        for char in state.characters.values()
        if char.id != state.prince_id
    ]


def create_initial_game_state() -> GameState:
    clans = {clan.id: clan for clan in seed_clans()}
    characters = seed_characters()
    clan_states = {
        "ventrue": ClanPoliticalState(
            clan=clans["ventrue"],
            relations={"toreador": 5, "brujah": 0},
        ),
        "toreador": ClanPoliticalState(
            clan=clans["toreador"],
            relations={"ventrue": 5, "brujah": 5},
        ),
        "brujah": ClanPoliticalState(
            clan=clans["brujah"],
            relations={"ventrue": 0, "toreador": 5},
        ),
    }
    state = GameState(characters=characters, clan_states=clan_states)
    initialize_current_politics(state)

    state.clan_states["ventrue"].current_loyalties.update({
        "ventrue__humanist_reformist": 48,
        "ventrue__humanist_traditional": 55,
    })
    state.clan_states["ventrue"].current_allies.update({
        "ventrue__humanist_reformist": "primogen_toreador",
        "ventrue__humanist_traditional": "primogen_toreador",
    })
    state.clan_states["toreador"].current_loyalties.update({
        "toreador__humanist_reformist": 50,
        "toreador__predatory_radical": 42,
        "toreador__predatory_traditional": 46,
    })
    state.clan_states["toreador"].current_allies.update({
        "toreador__humanist_reformist": "primogen_brujah",
        "toreador__predatory_radical": "primogen_brujah",
        "toreador__predatory_traditional": "primogen_ventrue",
    })
    state.clan_states["brujah"].current_loyalties.update({
        "brujah__predatory_radical": 40,
        "brujah__humanist_traditional": 45,
    })
    state.clan_states["brujah"].current_allies.update({
        "brujah__predatory_radical": "primogen_toreador",
        "brujah__humanist_traditional": "primogen_toreador",
    })
    return state
