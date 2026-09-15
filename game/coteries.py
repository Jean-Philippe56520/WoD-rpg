"""Coteries vampiriques transclaniques et compatibilité de l'ancienne API V0.8.

Depuis la V0.9, les deux camps politiques internes d'un clan sont des *factions*.
La V0.11 donne enfin au terme « coterie » son sens propre : un petit groupe de
vampires pouvant appartenir à plusieurs clans, avec des liens qui concurrencent
parfois la loyauté envers le Primogène.

Les coteries initiales sont des éléments statiques du décor du MVP. Leur état
politique dynamique n'est pas dupliqué dans une nouvelle jauge : leur cohésion
effective est calculée à partir des relations et griefs déjà persistants dans
``GameState``. Les anciennes fonctions ``coterie_influence`` / ``set_coterie_side``
restent des alias de compatibilité vers les factions internes.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

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
from .models import ActionType, GameAction, GameState
from .social_politics import active_grievance_score


@dataclass(frozen=True)
class CoterieDefinition:
    id: str
    name: str
    leader_id: str
    member_ids: tuple[str, ...]
    purpose: str
    base_cohesion: int

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.name.strip():
            raise ValueError("Coterie id and name are required")
        if self.leader_id not in self.member_ids:
            raise ValueError("Coterie leader must be a member")
        if len(self.member_ids) < 2 or len(set(self.member_ids)) != len(self.member_ids):
            raise ValueError("A coterie needs at least two distinct members")
        if not 0 <= self.base_cohesion <= 3:
            raise ValueError("Coterie cohesion must be between 0 and 3")


CANONICAL_COTERIES: tuple[CoterieDefinition, ...] = (
    CoterieDefinition(
        id="concorde_des_trois",
        name="La Concorde des Trois",
        leader_id="toreador_camille",
        member_ids=("toreador_camille", "ventrue_helene", "brujah_ines"),
        purpose=(
            "Préserver la Mascarade par la coopération, protéger les relais mortels utiles "
            "et maintenir des canaux de médiation entre les clans."
        ),
        base_cohesion=2,
    ),
    CoterieDefinition(
        id="cendres_libres",
        name="Les Cendres Libres",
        leader_id="ventrue_claire",
        member_ids=("ventrue_claire", "toreador_lucien", "brujah_sarah"),
        purpose=(
            "Limiter la concentration du pouvoir, défendre l'autonomie des vampires locaux "
            "et soutenir les réformes lorsque les Primogènes se crispent."
        ),
        base_cohesion=3,
    ),
    CoterieDefinition(
        id="pacte_de_fer",
        name="Le Pacte de Fer",
        leader_id="ventrue_victor",
        member_ids=("ventrue_victor", "toreador_gabriel", "brujah_yann"),
        purpose=(
            "Assurer une entraide rapide face aux menaces physiques et territoriales, même "
            "lorsque les intérêts politiques de ses membres divergent."
        ),
        base_cohesion=1,
    ),
)

HOSTILE_COTERIE_ACTIONS = frozenset(
    {
        ActionType.UNDERMINE,
        ActionType.POACH,
        ActionType.DOMAIN_INTRUSION,
        ActionType.BRACONNAGE,
    }
)


def canonical_coteries() -> tuple[CoterieDefinition, ...]:
    return CANONICAL_COTERIES


def coteries_for_character(character_id: str) -> tuple[CoterieDefinition, ...]:
    return tuple(
        coterie for coterie in CANONICAL_COTERIES if character_id in coterie.member_ids
    )


def coterie_for_character(character_id: str) -> CoterieDefinition | None:
    matches = coteries_for_character(character_id)
    return matches[0] if matches else None


def shared_coterie(
    first_character_id: str,
    second_character_id: str,
) -> CoterieDefinition | None:
    if first_character_id == second_character_id:
        return coterie_for_character(first_character_id)
    for coterie in CANONICAL_COTERIES:
        if first_character_id in coterie.member_ids and second_character_id in coterie.member_ids:
            return coterie
    return None


def coterie_clans(state: GameState, coterie: CoterieDefinition) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                state.characters[member_id].clan_id
                for member_id in coterie.member_ids
                if member_id in state.characters and state.characters[member_id].clan_id
            }
        )
    )


def _seed_missing_bonds(state: GameState) -> None:
    """Crée le lien social initial une seule fois, sans écraser une relation dégradée.

    Une valeur explicitement tombée à 0 reste donc à 0 lors des nuits suivantes.
    """

    for coterie in CANONICAL_COTERIES:
        existing_members = [member_id for member_id in coterie.member_ids if member_id in state.characters]
        for first_id, second_id in combinations(existing_members, 2):
            first = state.characters[first_id]
            second = state.characters[second_id]
            if second_id not in first.relations:
                first.relations[second_id] = 1
            if first_id not in second.relations:
                second.relations[first_id] = 1


def reveal_coterie_contacts(state: GameState) -> None:
    """Une coterie donne à chaque clan membre un renseignement d'identité niveau 1.

    Cela ne révèle ni faction interne, ni griefs, ni relation au Primogène : ces
    informations restent soumises au brouillard de guerre normal (niveau 2).
    """

    for coterie in CANONICAL_COTERIES:
        member_clans = coterie_clans(state, coterie)
        for clan_id in member_clans:
            clan_state = state.clan_states.get(clan_id)
            if clan_state is None:
                continue
            for member_id in coterie.member_ids:
                member = state.characters.get(member_id)
                if member is None or member.clan_id == clan_id:
                    continue
                clan_state.known_character_intel[member_id] = max(
                    1, clan_state.known_character_intel.get(member_id, 0)
                )


def initialize_coteries(state: GameState) -> None:
    """Initialise les liens de coterie sans introduire de nouvelle persistance.

    L'appel conserve aussi le comportement historique V0.8 : il répare d'abord
    les factions internes avant de préparer les véritables coteries V0.11.
    """

    initialize_factions(state)
    _seed_missing_bonds(state)
    reveal_coterie_contacts(state)


def effective_coterie_cohesion(state: GameState, coterie: CoterieDefinition) -> int:
    """Calcule 0..3 à partir du socle de coterie, des relations et griefs persistants."""

    members = [member_id for member_id in coterie.member_ids if member_id in state.characters]
    if len(members) < 2:
        return 0

    pair_relations: list[float] = []
    serious_grievance = False
    for first_id, second_id in combinations(members, 2):
        first = state.characters[first_id]
        second = state.characters[second_id]
        pair_relations.append(
            (first.relations.get(second_id, 1) + second.relations.get(first_id, 1)) / 2
        )
        if (
            active_grievance_score(state, first_id, second_id) >= 2
            or active_grievance_score(state, second_id, first_id) >= 2
        ):
            serious_grievance = True

    average_relation = sum(pair_relations) / len(pair_relations)
    relation_modifier = 1 if average_relation >= 1.5 else (-1 if average_relation <= 0.5 else 0)
    grievance_penalty = 1 if serious_grievance else 0
    return max(0, min(3, coterie.base_cohesion + relation_modifier - grievance_penalty))


def coterie_cooperation_bonus(state: GameState, actor_id: str, target_id: str) -> int:
    """Bonus compact pour diplomatie/enquête entre compagnons de coterie."""

    coterie = shared_coterie(actor_id, target_id)
    if coterie is None:
        return 0
    return 1 if effective_coterie_cohesion(state, coterie) >= 1 else 0


def coterie_conflict_penalty(state: GameState, actor_id: str, target_id: str) -> int:
    """Malus d'exécution lorsqu'un membre agit contre un compagnon de coterie."""

    coterie = shared_coterie(actor_id, target_id)
    if coterie is None:
        return 0
    if active_grievance_score(state, actor_id, target_id) >= 2:
        return 0
    relation = state.characters[actor_id].relations.get(target_id, 1)
    return 1 if relation >= 1 and effective_coterie_cohesion(state, coterie) >= 1 else 0


def hostile_coterie_target_id(state: GameState, action: GameAction) -> str | None:
    if action.action_type not in HOSTILE_COTERIE_ACTIONS:
        return None
    if action.target_character_id:
        return action.target_character_id
    if action.target_domain_id:
        domain = state.domains.get(action.target_domain_id)
        return domain.holder_id if domain else None
    return None


def should_refuse_coterie_conflict(
    state: GameState,
    action: GameAction,
    actor_id: str,
) -> bool:
    """Un PNJ peut refuser un ordre qui attaque un compagnon auquel il reste lié.

    Le Primogène ne refuse jamais sa propre décision. Un membre très proche du
    Primogène (relation effective >=2) obéit, mais subit encore le malus de conflit.
    """

    target_id = hostile_coterie_target_id(state, action)
    if not target_id or target_id not in state.characters:
        return False
    clan_state = state.clan_states[action.clan_id]
    if actor_id == clan_state.clan.primogen_id:
        return False
    coterie = shared_coterie(actor_id, target_id)
    if coterie is None or effective_coterie_cohesion(state, coterie) < 2:
        return False
    if active_grievance_score(state, actor_id, target_id) >= 2:
        return False
    actor = state.characters[actor_id]
    if actor.relations.get(target_id, 1) < 1:
        return False
    return effective_relation_to_primogen(state, actor_id) <= 1


def strain_coterie_bond(state: GameState, actor_id: str, target_id: str) -> str | None:
    """Dégrade une relation bilatérale après une action hostile effectivement menée."""

    coterie = shared_coterie(actor_id, target_id)
    if coterie is None:
        return None
    actor = state.characters[actor_id]
    target = state.characters[target_id]
    actor.relations[target_id] = max(0, actor.relations.get(target_id, 1) - 1)
    target.relations[actor_id] = max(0, target.relations.get(actor_id, 1) - 1)
    return coterie.name


def coterie_member_summary(state: GameState, coterie: CoterieDefinition) -> tuple[str, ...]:
    values: list[str] = []
    for member_id in coterie.member_ids:
        character = state.characters.get(member_id)
        if character is None:
            continue
        clan_name = (
            state.clan_states[character.clan_id].clan.name
            if character.clan_id in state.clan_states
            else character.clan_id or "Sans clan"
        )
        role = "chef" if member_id == coterie.leader_id else "membre"
        values.append(f"{character.name} — {clan_name} ({role})")
    return tuple(values)


# ---------------------------------------------------------------------------
# Compatibilité V0.8/V0.9 : ces noms désignent historiquement les factions.
# ---------------------------------------------------------------------------
coterie_members = faction_members
coterie_influence = faction_influence
set_coterie_side = set_faction_side
determine_coterie_stances = determine_faction_stances
