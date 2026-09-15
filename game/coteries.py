"""Compatibilité V0.8.

Depuis la V0.9, les deux camps politiques internes d'un clan sont des *factions*.
Le terme « coterie » est réservé aux véritables coteries vampiriques, potentiellement
transclaniques. Ce module ne contient plus de règles propres : il réexporte l'API
V0.8 vers le moteur de factions.
"""

from .factions import (
    choose_allied_primogen,
    choose_opposition_leader,
    clan_total_influence,
    determine_faction_stances,
    effective_relation_to_primogen,
    faction_influence,
    faction_members,
    ideology_relation_modifier,
    initialize_factions,
    set_faction_side,
)

# Alias historiques.
coterie_members = faction_members
coterie_influence = faction_influence
initialize_coteries = initialize_factions
set_coterie_side = set_faction_side
determine_coterie_stances = determine_faction_stances
