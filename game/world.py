from __future__ import annotations

from .coteries import initialize_coteries
from .models import (
    AxisPolarity,
    BloodRank,
    Candidate,
    Character,
    Clan,
    ClanPoliticalState,
    CoterieSide,
    GameState,
)


REQUIRED_CLANS = ("ventrue", "toreador", "brujah")


def seed_characters() -> dict[str, Character]:
    return {
        "primogen_ventrue": Character(
            id="primogen_ventrue", name="Adrien de Keravel", clan_id="ventrue",
            personal_influence=22, humanity_axis=AxisPolarity.MINUS,
            tradition_axis=AxisPolarity.PLUS, physical=1, social=2, mental=2,
            expertises=("Politique", "Finance", "Intimidation"),
            disciplines={"domination": 2, "force_d_ame": 1, "presence": 2},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Influence politique": 2, "Ressources": 2, "Contacts": 1},
            relation_to_primogen=2, loyalty=75, ambition=85, is_primogen=True,
        ),
        "ventrue_claire": Character(
            id="ventrue_claire", name="Claire Beaumont", clan_id="ventrue",
            personal_influence=15, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.MINUS, physical=0, social=2, mental=1,
            expertises=("Diplomatie", "Politique"),
            disciplines={"domination": 1, "presence": 2},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Contacts": 2, "Influence politique": 1},
            relation_to_primogen=0, loyalty=30, ambition=80,
        ),
        "ventrue_victor": Character(
            id="ventrue_victor", name="Victor de Keravel", clan_id="ventrue",
            personal_influence=18, humanity_axis=AxisPolarity.MINUS,
            tradition_axis=AxisPolarity.PLUS, physical=2, social=1, mental=1,
            expertises=("Intimidation", "Combat"),
            disciplines={"domination": 1, "force_d_ame": 2, "presence": 1},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Ressources": 1, "Serviteurs": 1},
            relation_to_primogen=2, loyalty=75, ambition=65,
        ),
        "ventrue_helene": Character(
            id="ventrue_helene", name="Helene Beaumont", clan_id="ventrue",
            personal_influence=12, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.PLUS, physical=0, social=1, mental=2,
            expertises=("Investigation", "Finance"),
            disciplines={"domination": 1, "presence": 1},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Ressources": 2, "Contacts": 1},
            relation_to_primogen=1, loyalty=45, ambition=55,
        ),
        "primogen_toreador": Character(
            id="primogen_toreador", name="Elise Valmont", clan_id="toreador",
            personal_influence=21, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.PLUS, physical=0, social=2, mental=2,
            expertises=("Diplomatie", "Art", "Politique"),
            disciplines={"auspex": 2, "celerite": 1, "presence": 2},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Milieu artistique": 2, "Influence politique": 1, "Contacts": 2},
            relation_to_primogen=2, loyalty=70, ambition=80, is_primogen=True,
        ),
        "toreador_lucien": Character(
            id="toreador_lucien", name="Lucien Marceau", clan_id="toreador",
            personal_influence=14, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.MINUS, physical=1, social=2, mental=1,
            expertises=("Subterfuge", "Art"),
            disciplines={"celerite": 1, "presence": 2},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Célébrité": 2, "Contacts": 1},
            relation_to_primogen=1, loyalty=40, ambition=78,
        ),
        "toreador_camille": Character(
            id="toreador_camille", name="Camille Vernier", clan_id="toreador",
            personal_influence=17, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.PLUS, physical=1, social=1, mental=2,
            expertises=("Investigation", "Occultisme"),
            disciplines={"auspex": 2, "celerite": 1},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Contacts": 2, "Ressources": 1},
            relation_to_primogen=2, loyalty=72, ambition=62,
        ),
        "toreador_gabriel": Character(
            id="toreador_gabriel", name="Gabriel Sorel", clan_id="toreador",
            personal_influence=11, humanity_axis=AxisPolarity.MINUS,
            tradition_axis=AxisPolarity.MINUS, physical=2, social=1, mental=0,
            expertises=("Combat", "Intimidation"),
            disciplines={"celerite": 2, "presence": 1},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Rue": 1},
            relation_to_primogen=1, loyalty=48, ambition=58,
        ),
        "toreador_noemie": Character(
            id="toreador_noemie", name="Noemie Varenne", clan_id="toreador",
            personal_influence=9, humanity_axis=AxisPolarity.MINUS,
            tradition_axis=AxisPolarity.PLUS, physical=0, social=1, mental=2,
            expertises=("Occultisme", "Investigation"),
            disciplines={"auspex": 2, "presence": 1},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Contacts": 1},
            relation_to_primogen=1, loyalty=52, ambition=61,
        ),
        "primogen_brujah": Character(
            id="primogen_brujah", name="Marcus Le Guen", clan_id="brujah",
            personal_influence=19, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.MINUS, physical=2, social=2, mental=1,
            expertises=("Politique", "Intimidation", "Rue"),
            disciplines={"celerite": 1, "puissance": 2, "presence": 1},
            blood_rank=BloodRank.ANCILLA,
            backgrounds={"Influence syndicale": 2, "Contacts": 1},
            relation_to_primogen=2, loyalty=68, ambition=76, is_primogen=True,
        ),
        "brujah_sarah": Character(
            id="brujah_sarah", name="Sarah Morel", clan_id="brujah",
            personal_influence=15, humanity_axis=AxisPolarity.MINUS,
            tradition_axis=AxisPolarity.MINUS, physical=2, social=1, mental=1,
            expertises=("Combat", "Rue"),
            disciplines={"celerite": 1, "puissance": 2},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Contacts": 1, "Alliés": 1},
            relation_to_primogen=0, loyalty=35, ambition=82,
        ),
        "brujah_yann": Character(
            id="brujah_yann", name="Yann Kergoat", clan_id="brujah",
            personal_influence=16, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.MINUS, physical=1, social=1, mental=2,
            expertises=("Technologie", "Politique"),
            disciplines={"celerite": 2, "presence": 1},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Contacts": 2, "Ressources": 1},
            relation_to_primogen=2, loyalty=70, ambition=64,
        ),
        "brujah_ines": Character(
            id="brujah_ines", name="Ines Le Floch", clan_id="brujah",
            personal_influence=10, humanity_axis=AxisPolarity.PLUS,
            tradition_axis=AxisPolarity.PLUS, physical=1, social=2, mental=1,
            expertises=("Diplomatie", "Médecine"),
            disciplines={"presence": 2, "celerite": 1},
            blood_rank=BloodRank.NEWBORN,
            backgrounds={"Alliés": 2},
            relation_to_primogen=1, loyalty=52, ambition=50,
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
            coterie_memberships={
                "primogen_ventrue": CoterieSide.PRIMOGEN,
                "ventrue_victor": CoterieSide.PRIMOGEN,
                "ventrue_claire": CoterieSide.OPPOSITION,
                "ventrue_helene": CoterieSide.OPPOSITION,
            },
            opposition_leader_id="ventrue_claire",
            opposition_allied_primogen_id="primogen_brujah",
            relations={"toreador": 5, "brujah": 0},
        ),
        "toreador": ClanPoliticalState(
            clan=clans["toreador"],
            coterie_memberships={
                "primogen_toreador": CoterieSide.PRIMOGEN,
                "toreador_camille": CoterieSide.PRIMOGEN,
                "toreador_noemie": CoterieSide.PRIMOGEN,
                "toreador_lucien": CoterieSide.OPPOSITION,
                "toreador_gabriel": CoterieSide.OPPOSITION,
            },
            opposition_leader_id="toreador_lucien",
            opposition_allied_primogen_id="primogen_brujah",
            relations={"ventrue": 5, "brujah": 5},
        ),
        "brujah": ClanPoliticalState(
            clan=clans["brujah"],
            coterie_memberships={
                "primogen_brujah": CoterieSide.PRIMOGEN,
                "brujah_yann": CoterieSide.PRIMOGEN,
                "brujah_ines": CoterieSide.PRIMOGEN,
                "brujah_sarah": CoterieSide.OPPOSITION,
            },
            opposition_leader_id="brujah_sarah",
            opposition_allied_primogen_id="primogen_ventrue",
            relations={"ventrue": 0, "toreador": 5},
        ),
    }
    state = GameState(characters=characters, clan_states=clan_states)
    initialize_coteries(state)
    return state
