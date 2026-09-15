from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClanIdentity:
    id: str
    name: str
    medieval_position: str
    political_tension: str
    bane_name: str
    bane_text: str
    favored_situations: tuple[str, ...]
    high_clan: bool = True


CLANS: dict[str, ClanIdentity] = {
    "brujah": ClanIdentity(
        id="brujah",
        name="Brujah",
        medieval_position=(
            "Un clan encore prestigieux parmi les Hauts Clans, partagé entre érudits, guerriers, "
            "seigneurs et voix de plus en plus hostiles aux abus des anciens."
        ),
        political_tension=(
            "Le clan n'est pas automatiquement anarch : sa fracture entre ordre, idéalisme et révolte "
            "doit produire des choix politiques contradictoires."
        ),
        bane_name="Fureur",
        bane_text=(
            "Quand le Brujah est publiquement humilié, dominé ou confronté à une injustice qu'il juge intolérable, "
            "la Bête est plus difficile à contenir."
        ),
        favored_situations=("revolt", "debate", "intimidation", "protect_young"),
    ),
    "toreador": ClanIdentity(
        id="toreador",
        name="Toreador",
        medieval_position=(
            "Un Haut Clan profondément implanté dans les cours, les mécénats, les arts, les réseaux mortels "
            "et les formes de prestige qui permettent d'influencer sans posséder directement."
        ),
        political_tension=(
            "Le désir de préserver ce qui est beau ou civilisé peut les rapprocher de l'ordre, tandis que leur "
            "attachement aux individus et aux œuvres peut les opposer à la brutalité des anciens."
        ),
        bane_name="Fascination",
        bane_text=(
            "Une œuvre, une personne ou un moment d'une beauté saisissante peut détourner le Toreador de son objectif "
            "et créer un coût réel lorsqu'il devrait agir vite."
        ),
        favored_situations=("court", "patronage", "art", "diplomacy"),
    ),
    "ventrue": ClanIdentity(
        id="ventrue",
        name="Ventrue",
        medieval_position=(
            "Un Haut Clan habitué à l'autorité, aux serments, à la terre, aux administrations et aux réseaux "
            "de dépendance. Plusieurs de ses anciens jouent un rôle central dans le projet de nouvel ordre."
        ),
        political_tension=(
            "Le clan doit choisir entre conservation de l'ordre féodal nocturne et invention d'institutions "
            "capables de survivre à la révolte et aux chasseurs."
        ),
        bane_name="Goût exigeant",
        bane_text=(
            "Le Ventrue ne peut se nourrir durablement que sur un type de proie correspondant à sa préférence de Sang. "
            "Une chasse qui ne respecte pas cette restriction peut échouer même si une victime est accessible."
        ),
        favored_situations=("authority", "oath", "domain", "administration"),
    ),
}


NPC_CLANS: tuple[str, ...] = (
    "lasombra",
    "tzimisce",
    "tremere",
    "nosferatu",
    "malkavian",
    "gangrel",
    "cappadocian",
    "banu_haqim",
)


def clan_identity(clan_id: str) -> ClanIdentity:
    try:
        return CLANS[clan_id]
    except KeyError as exc:
        raise ValueError(f"Unsupported playable clan: {clan_id}") from exc


def situation_bonus(clan_id: str, situation_tags: tuple[str, ...]) -> int:
    identity = clan_identity(clan_id)
    return 1 if set(identity.favored_situations).intersection(situation_tags) else 0
