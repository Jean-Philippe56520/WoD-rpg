from __future__ import annotations

from .models import Candidate, Character, Clan, PoliticalCurrent


def seed_characters() -> dict[str, Character]:
    return {
        "primogen_ventrue": Character(
            id="primogen_ventrue", name="Adrien de Keravel", clan_id="ventrue", is_primogen=True
        ),
        "primogen_toreador": Character(
            id="primogen_toreador", name="Élise Valmont", clan_id="toreador", is_primogen=True
        ),
        "primogen_brujah": Character(
            id="primogen_brujah", name="Marcus Le Guen", clan_id="brujah", is_primogen=True
        ),
    }


def seed_clans() -> list[Clan]:
    return [
        Clan(
            id="ventrue",
            name="Ventrue",
            primogen_id="primogen_ventrue",
            dominant_current=PoliticalCurrent(
                id="ventrue_dominant", name="Courant du Primogène", influence=60, leader_name="Adrien de Keravel"
            ),
            opposition_current=PoliticalCurrent(
                id="ventrue_opposition", name="Opposition", influence=40, leader_name="Claire Beaumont"
            ),
        ),
        Clan(
            id="toreador",
            name="Toreador",
            primogen_id="primogen_toreador",
            dominant_current=PoliticalCurrent(
                id="toreador_dominant", name="Courant du Primogène", influence=55, leader_name="Élise Valmont"
            ),
            opposition_current=PoliticalCurrent(
                id="toreador_opposition", name="Opposition", influence=25, leader_name="Lucien Marceau"
            ),
        ),
        Clan(
            id="brujah",
            name="Brujah",
            primogen_id="primogen_brujah",
            dominant_current=PoliticalCurrent(
                id="brujah_dominant", name="Courant du Primogène", influence=45, leader_name="Marcus Le Guen"
            ),
            opposition_current=PoliticalCurrent(
                id="brujah_opposition", name="Opposition", influence=25, leader_name="Sarah Morel"
            ),
        ),
    ]


def seed_candidates() -> list[Candidate]:
    chars = seed_characters()
    return [
        Candidate(
            id=char.id,
            name=char.name,
            clan_id=char.clan_id,
            is_primogen=char.is_primogen,
        )
        for char in chars.values()
    ]
