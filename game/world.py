from __future__ import annotations

from .models import (
    Candidate,
    Character,
    Clan,
    ClanPoliticalState,
    GameState,
    PoliticalCurrent,
)


def seed_characters() -> dict[str, Character]:
    return {
        "primogen_ventrue": Character(
            id="primogen_ventrue", name="Adrien de Keravel", clan_id="ventrue",
            current_id="ventrue_dominant", personal_influence=22, humanity=6,
            loyalty=75, ambition=85, is_primogen=True,
        ),
        "ventrue_claire": Character(
            id="ventrue_claire", name="Claire Beaumont", clan_id="ventrue",
            current_id="ventrue_opposition", personal_influence=15, humanity=7,
            loyalty=30, ambition=80,
        ),
        "ventrue_victor": Character(
            id="ventrue_victor", name="Victor de Keravel", clan_id="ventrue",
            current_id="ventrue_dominant", personal_influence=18, humanity=6,
            loyalty=75, ambition=65,
        ),
        "ventrue_helene": Character(
            id="ventrue_helene", name="Helene Beaumont", clan_id="ventrue",
            current_id="ventrue_opposition", personal_influence=12, humanity=7,
            loyalty=45, ambition=55,
        ),
        "primogen_toreador": Character(
            id="primogen_toreador", name="Elise Valmont", clan_id="toreador",
            current_id="toreador_dominant", personal_influence=21, humanity=7,
            loyalty=70, ambition=80, is_primogen=True,
        ),
        "toreador_lucien": Character(
            id="toreador_lucien", name="Lucien Marceau", clan_id="toreador",
            current_id="toreador_opposition", personal_influence=14, humanity=7,
            loyalty=40, ambition=78,
        ),
        "toreador_camille": Character(
            id="toreador_camille", name="Camille Vernier", clan_id="toreador",
            current_id="toreador_dominant", personal_influence=17, humanity=7,
            loyalty=72, ambition=62,
        ),
        "toreador_gabriel": Character(
            id="toreador_gabriel", name="Gabriel Sorel", clan_id="toreador",
            current_id="toreador_opposition", personal_influence=11, humanity=8,
            loyalty=48, ambition=58,
        ),
        "primogen_brujah": Character(
            id="primogen_brujah", name="Marcus Le Guen", clan_id="brujah",
            current_id="brujah_dominant", personal_influence=19, humanity=7,
            loyalty=68, ambition=76, is_primogen=True,
        ),
        "brujah_sarah": Character(
            id="brujah_sarah", name="Sarah Morel", clan_id="brujah",
            current_id="brujah_opposition", personal_influence=15, humanity=7,
            loyalty=35, ambition=82,
        ),
        "brujah_yann": Character(
            id="brujah_yann", name="Yann Kergoat", clan_id="brujah",
            current_id="brujah_dominant", personal_influence=16, humanity=6,
            loyalty=70, ambition=64,
        ),
        "brujah_ines": Character(
            id="brujah_ines", name="Ines Le Floch", clan_id="brujah",
            current_id="brujah_opposition", personal_influence=10, humanity=8,
            loyalty=52, ambition=50,
        ),
    }


def seed_clans() -> list[Clan]:
    return [
        Clan(
            id="ventrue", name="Ventrue", primogen_id="primogen_ventrue",
            dominant_current=PoliticalCurrent(
                id="ventrue_dominant", name="Courant du Primogene", influence=60,
                leader_name="Adrien de Keravel",
            ),
            opposition_current=PoliticalCurrent(
                id="ventrue_opposition", name="Opposition", influence=40,
                leader_name="Claire Beaumont",
            ),
        ),
        Clan(
            id="toreador", name="Toreador", primogen_id="primogen_toreador",
            dominant_current=PoliticalCurrent(
                id="toreador_dominant", name="Courant du Primogene", influence=55,
                leader_name="Elise Valmont",
            ),
            opposition_current=PoliticalCurrent(
                id="toreador_opposition", name="Opposition", influence=25,
                leader_name="Lucien Marceau",
            ),
        ),
        Clan(
            id="brujah", name="Brujah", primogen_id="primogen_brujah",
            dominant_current=PoliticalCurrent(
                id="brujah_dominant", name="Courant du Primogene", influence=45,
                leader_name="Marcus Le Guen",
            ),
            opposition_current=PoliticalCurrent(
                id="brujah_opposition", name="Opposition", influence=25,
                leader_name="Sarah Morel",
            ),
        ),
    ]


def seed_candidates() -> list[Candidate]:
    chars = seed_characters()
    return [
        Candidate(id=char.id, name=char.name, clan_id=char.clan_id, is_primogen=char.is_primogen)
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
            clan=clans["ventrue"], opposition_loyalty=48,
            opposition_ally_id="primogen_toreador", relations={"toreador": 5, "brujah": 0},
        ),
        "toreador": ClanPoliticalState(
            clan=clans["toreador"], opposition_loyalty=58,
            opposition_ally_id="primogen_ventrue", relations={"ventrue": 5, "brujah": 5},
        ),
        "brujah": ClanPoliticalState(
            clan=clans["brujah"], opposition_loyalty=54,
            opposition_ally_id="primogen_toreador", relations={"ventrue": 0, "toreador": 5},
        ),
    }
    return GameState(characters=characters, clan_states=clan_states)
