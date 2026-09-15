from __future__ import annotations

from dataclasses import dataclass, field, replace
import hashlib
from typing import Mapping

from .chronicle import PlayerCharacter, SIRES
from .era import CamarillaStage, EraRules, era_for_year


@dataclass(frozen=True)
class NpcState:
    id: str
    name: str
    clan_id: str
    role: str
    ambition: str
    short_goal: str
    loyalty: int
    aggression: int
    influence: float
    status: int
    camarilla_attitude: int
    agenda_progress: int = 0
    alive: bool = True
    relations: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class DomainState:
    id: str
    name: str
    description: str
    holder_id: str | None
    viandis: int
    servage: int
    rempart: int
    pressure: int = 0
    masquerade_risk: int = 0


@dataclass(frozen=True)
class HuntingAccessState:
    id: str
    domain_id: str
    beneficiary_id: str
    granted_by_id: str
    source: str
    active: bool = True
    expires_year: int | None = None


@dataclass(frozen=True)
class BoonState:
    id: str
    creditor_id: str
    debtor_id: str
    level: str
    origin: str
    status: str = "due"
    public: bool = False


@dataclass(frozen=True)
class SimulationState:
    game_id: str
    year: int
    institution_stage: str
    npcs: dict[str, NpcState]
    domains: dict[str, DomainState]
    hunting_rights: dict[str, HuntingAccessState]
    boons: dict[str, BoonState]
    offices: dict[str, str | None]
    version: int = 1


@dataclass(frozen=True)
class SimulationBeat:
    actor_id: str
    actor_name: str
    category: str
    public_text: str
    hidden_intent: str


EXTRA_NPCS: tuple[NpcState, ...] = (
    NpcState(
        id="npc_prince_godefroy",
        name="Godefroy de Brienne",
        clan_id="ventrue",
        role="Prince local",
        ambition="Préserver son autorité sur la cité sans devenir le vassal d'un pouvoir lointain",
        short_goal="Obtenir des serments clairs des détenteurs de Domaines",
        loyalty=75,
        aggression=45,
        influence=8.0,
        status=4,
        camarilla_attitude=1,
    ),
    NpcState(
        id="npc_lasombra_aldric",
        name="Aldric de la Roche-Noire",
        clan_id="lasombra",
        role="Prélat et seigneur nocturne",
        ambition="Faire de l'autorité spirituelle un levier de domination politique",
        short_goal="Isoler les lignages qui soutiennent trop ouvertement Hardestadt",
        loyalty=40,
        aggression=70,
        influence=6.0,
        status=3,
        camarilla_attitude=-1,
    ),
    NpcState(
        id="npc_tzimisce_dragomir",
        name="Dragomir de Vlasca",
        clan_id="tzimisce",
        role="Voïvode en exil",
        ambition="Conserver une souveraineté absolue sur toute terre reconnue comme sienne",
        short_goal="Trouver des alliés qui rejettent l'ingérence des coalitions d'anciens",
        loyalty=30,
        aggression=80,
        influence=5.5,
        status=3,
        camarilla_attitude=-2,
    ),
    NpcState(
        id="npc_tremere_conrad",
        name="Magister Conrad",
        clan_id="tremere",
        role="Thaumaturge et négociateur",
        ambition="Acheter la tolérance que son clan ne peut pas encore exiger",
        short_goal="Transformer des informations occultes en dettes politiques",
        loyalty=55,
        aggression=35,
        influence=4.0,
        status=2,
        camarilla_attitude=1,
    ),
    NpcState(
        id="npc_nosferatu_anne",
        name="Anne des Souterrains",
        clan_id="nosferatu",
        role="Maîtresse des passages",
        ambition="Rendre son réseau indispensable à tous les camps sans appartenir à aucun",
        short_goal="Cartographier les refuges compromis par les chasseurs",
        loyalty=50,
        aggression=25,
        influence=4.5,
        status=2,
        camarilla_attitude=0,
    ),
    NpcState(
        id="npc_malkavian_severin",
        name="Frère Séverin",
        clan_id="malkavian",
        role="Confesseur nocturne",
        ambition="Comprendre la catastrophe qu'il affirme voir approcher",
        short_goal="Convaincre trois Caïnites de modifier leurs habitudes de chasse",
        loyalty=45,
        aggression=20,
        influence=3.0,
        status=2,
        camarilla_attitude=0,
    ),
    NpcState(
        id="npc_gangrel_ilona",
        name="Ilona la Grise",
        clan_id="gangrel",
        role="Gardienne des routes",
        ambition="Préserver des refuges hors de la juridiction des seigneurs urbains",
        short_goal="Maintenir ouverts les passages entre la cité et les terres sauvages",
        loyalty=35,
        aggression=55,
        influence=3.5,
        status=2,
        camarilla_attitude=-1,
    ),
    NpcState(
        id="npc_cappadocian_agnes",
        name="Sœur Agnès",
        clan_id="cappadocian",
        role="Gardienne des morts",
        ambition="Protéger ses recherches des guerres de lignage",
        short_goal="Obtenir un accès sûr aux cryptes de la cathédrale",
        loyalty=60,
        aggression=10,
        influence=3.5,
        status=2,
        camarilla_attitude=0,
    ),
    NpcState(
        id="npc_banu_haqim_farid",
        name="Farid ibn Salim",
        clan_id="banu_haqim",
        role="Juge itinérant",
        ambition="Faire respecter les dettes et châtier ceux qui se croient hors de toute loi",
        short_goal="Établir qui a brisé un ancien serment de passage",
        loyalty=65,
        aggression=60,
        influence=4.0,
        status=3,
        camarilla_attitude=0,
    ),
)


SIRE_DOMAIN_IDS = {
    "sire_ventrue_aymon": "domain_haute_ville",
    "sire_ventrue_heloise": "domain_halles_ponts",
    "sire_toreador_isabeau": "domain_cour_enlumineurs",
    "sire_toreador_matteo": "domain_quais_ateliers",
    "sire_brujah_guilhem": "domain_faubourgs",
    "sire_brujah_ysabeau": "domain_routes_landes",
}


def _sire_npc(sire) -> NpcState:
    return NpcState(
        id=sire.id,
        name=sire.name,
        clan_id=sire.clan_id,
        role=sire.title,
        ambition=sire.expectation,
        short_goal=sire.description,
        loyalty=70 if sire.order_stance == "orthodox" else 45,
        aggression=45 if sire.mortal_stance == "humanist" else 60,
        influence=5.0,
        status=3,
        camarilla_attitude=1 if sire.order_stance == "orthodox" else -1,
    )


def initial_simulation(game_id: str, year: int = 1435) -> SimulationState:
    era = era_for_year(year)
    npcs = {sire.id: _sire_npc(sire) for sire in SIRES}
    npcs.update({npc.id: npc for npc in EXTRA_NPCS})
    domains = {
        "domain_haute_ville": DomainState(
            "domain_haute_ville",
            "La Haute-Ville",
            "Maisons fortes, justice seigneuriale et demeures des notables.",
            "sire_ventrue_aymon",
            2,
            3,
            3,
        ),
        "domain_halles_ponts": DomainState(
            "domain_halles_ponts",
            "Les Halles et les Ponts",
            "Marchés, changeurs, péages et circulation nocturne des voyageurs.",
            "sire_ventrue_heloise",
            3,
            2,
            2,
        ),
        "domain_cour_enlumineurs": DomainState(
            "domain_cour_enlumineurs",
            "La Cour des Enlumineurs",
            "Ateliers, maisons de lettrés, mécènes et dépendances d'une cour aristocratique.",
            "sire_toreador_isabeau",
            2,
            3,
            2,
        ),
        "domain_quais_ateliers": DomainState(
            "domain_quais_ateliers",
            "Les Quais et Ateliers",
            "Bateliers, artisans, entrepôts et étrangers de passage.",
            "sire_toreador_matteo",
            3,
            2,
            1,
        ),
        "domain_faubourgs": DomainState(
            "domain_faubourgs",
            "Les Faubourgs fortifiés",
            "Tavernes, soldats, étudiants, pauvres et maisons hors des vieux murs.",
            "sire_brujah_guilhem",
            3,
            1,
            2,
        ),
        "domain_routes_landes": DomainState(
            "domain_routes_landes",
            "Les Routes et les Landes",
            "Chemins, relais, hameaux et refuges qui échappent en partie au contrôle urbain.",
            "sire_brujah_ysabeau",
            2,
            1,
            1,
        ),
        "domain_citadelle": DomainState(
            "domain_citadelle",
            "La Citadelle",
            "Le cœur du pouvoir princier, pauvre en proies mais riche en autorité.",
            "npc_prince_godefroy",
            1,
            3,
            3,
        ),
    }
    return SimulationState(
        game_id=game_id,
        year=year,
        institution_stage=era.camarilla_stage.value,
        npcs=npcs,
        domains=domains,
        hunting_rights={},
        boons={},
        offices={"prince": "npc_prince_godefroy"},
    )


def ensure_character_links(state: SimulationState, character: PlayerCharacter) -> SimulationState:
    right_id = f"right_sire_{character.character_id}"
    if right_id in state.hunting_rights:
        return state
    domain_id = SIRE_DOMAIN_IDS.get(character.sire_id)
    if domain_id is None:
        return state
    rights = dict(state.hunting_rights)
    rights[right_id] = HuntingAccessState(
        id=right_id,
        domain_id=domain_id,
        beneficiary_id=character.character_id,
        granted_by_id=character.sire_id,
        source="Sous la responsabilité du sire",
    )
    return replace(state, hunting_rights=rights)


def active_hunting_access(state: SimulationState, character_id: str, year: int) -> tuple[HuntingAccessState, ...]:
    return tuple(
        right
        for right in state.hunting_rights.values()
        if right.beneficiary_id == character_id
        and right.active
        and (right.expires_year is None or right.expires_year >= year)
    )


def domain_for_holder(state: SimulationState, holder_id: str) -> DomainState | None:
    for domain in state.domains.values():
        if domain.holder_id == holder_id:
            return domain
    return None


def grant_boon(
    state: SimulationState,
    *,
    creditor_id: str,
    debtor_id: str,
    level: str,
    origin: str,
    public: bool = False,
) -> SimulationState:
    if level not in {"minor", "major", "life"}:
        raise ValueError("Unsupported boon level")
    seed = f"{state.game_id}:{state.year}:{creditor_id}:{debtor_id}:{level}:{origin}"
    boon_id = "boon_" + hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
    if boon_id in state.boons:
        return state
    boons = dict(state.boons)
    boons[boon_id] = BoonState(
        id=boon_id,
        creditor_id=creditor_id,
        debtor_id=debtor_id,
        level=level,
        origin=origin,
        public=public,
    )
    return replace(state, boons=boons)


def _deterministic_score(seed: str, modulus: int = 100) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:4], "big") % modulus


def _npc_action(npc: NpcState, era: EraRules, year: int, chapter: int, segment: int) -> tuple[NpcState, SimulationBeat]:
    score = _deterministic_score(f"{npc.id}:{year}:{chapter}:{segment}")
    progress = npc.agenda_progress + 1 + (1 if score >= 80 else 0)
    influence = max(0.0, npc.influence + (0.5 if score >= 70 else 0.0))

    if era.camarilla_stage in {CamarillaStage.PROJECT, CamarillaStage.COALITION} and npc.camarilla_attitude >= 1:
        public = f"{npc.name} cherche des garanties mutuelles entre plusieurs lignages de la cité."
        category = "camarilla_project"
        hidden = "Faire de la coalition naissante un moyen d'augmenter sa propre sécurité politique."
    elif era.anarch_revolt_active and npc.camarilla_attitude <= -1:
        public = f"{npc.name} reçoit discrètement des Caïnites qui refusent de nouveaux serments d'obéissance."
        category = "anarch_revolt"
        hidden = "Transformer le mécontentement contre les anciens en réseau politique durable."
    elif npc.role == "Prince local":
        public = f"{npc.name} exige que les litiges de Domaine soient portés devant sa Cour plutôt que réglés par la violence."
        category = "princely_authority"
        hidden = "Rendre sa juridiction indispensable avant que la coalition extérieure ne puisse la contester."
    else:
        public = f"{npc.name} fait avancer ses intérêts : {npc.short_goal[0].lower() + npc.short_goal[1:]}"
        category = "npc_agenda"
        hidden = npc.ambition

    updated = replace(npc, agenda_progress=progress, influence=influence)
    return updated, SimulationBeat(
        actor_id=npc.id,
        actor_name=npc.name,
        category=category,
        public_text=public,
        hidden_intent=hidden,
    )


def advance_simulation(
    state: SimulationState,
    *,
    year: int,
    chapter: int,
    segment: int,
    characters: list[PlayerCharacter],
) -> tuple[SimulationState, tuple[SimulationBeat, ...]]:
    era = era_for_year(year)
    current = replace(state, year=year, institution_stage=era.camarilla_stage.value)
    for character in characters:
        if character.is_active:
            current = ensure_character_links(current, character)

    candidate_ids = [npc_id for npc_id, npc in current.npcs.items() if npc.alive]
    candidate_ids.sort(
        key=lambda npc_id: _deterministic_score(f"order:{year}:{chapter}:{segment}:{npc_id}")
    )
    selected = candidate_ids[:4]
    npcs = dict(current.npcs)
    beats: list[SimulationBeat] = []
    for npc_id in selected:
        updated, beat = _npc_action(npcs[npc_id], era, year, chapter, segment)
        npcs[npc_id] = updated
        beats.append(beat)

    domains = dict(current.domains)
    if era.mortal_hunters_severe and selected:
        target_ids = sorted(domains)
        target_id = target_ids[_deterministic_score(f"hunters:{year}:{chapter}:{segment}", len(target_ids))]
        target = domains[target_id]
        domains[target_id] = replace(
            target,
            pressure=target.pressure + 1,
            masquerade_risk=min(3, target.masquerade_risk + (1 if target.pressure >= 1 else 0)),
        )
        beats.append(
            SimulationBeat(
                actor_id="mortal_hunters",
                actor_name="Les chasseurs mortels",
                category="hunter_pressure",
                public_text=f"Des disparitions et des questions insistantes rendent {target.name} moins sûr pour les prédateurs nocturnes.",
                hidden_intent="L'activité vampirique répétée attire une attention humaine organisée.",
            )
        )

    return replace(current, npcs=npcs, domains=domains), tuple(beats)


def simulation_to_dict(state: SimulationState) -> dict:
    def npc_payload(item: NpcState) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "clan_id": item.clan_id,
            "role": item.role,
            "ambition": item.ambition,
            "short_goal": item.short_goal,
            "loyalty": item.loyalty,
            "aggression": item.aggression,
            "influence": item.influence,
            "status": item.status,
            "camarilla_attitude": item.camarilla_attitude,
            "agenda_progress": item.agenda_progress,
            "alive": item.alive,
            "relations": dict(item.relations),
        }

    def domain_payload(item: DomainState) -> dict:
        return {
            "id": item.id,
            "name": item.name,
            "description": item.description,
            "holder_id": item.holder_id,
            "viandis": item.viandis,
            "servage": item.servage,
            "rempart": item.rempart,
            "pressure": item.pressure,
            "masquerade_risk": item.masquerade_risk,
        }

    def right_payload(item: HuntingAccessState) -> dict:
        return {
            "id": item.id,
            "domain_id": item.domain_id,
            "beneficiary_id": item.beneficiary_id,
            "granted_by_id": item.granted_by_id,
            "source": item.source,
            "active": item.active,
            "expires_year": item.expires_year,
        }

    def boon_payload(item: BoonState) -> dict:
        return {
            "id": item.id,
            "creditor_id": item.creditor_id,
            "debtor_id": item.debtor_id,
            "level": item.level,
            "origin": item.origin,
            "status": item.status,
            "public": item.public,
        }

    return {
        "game_id": state.game_id,
        "year": state.year,
        "institution_stage": state.institution_stage,
        "npcs": {key: npc_payload(value) for key, value in state.npcs.items()},
        "domains": {key: domain_payload(value) for key, value in state.domains.items()},
        "hunting_rights": {key: right_payload(value) for key, value in state.hunting_rights.items()},
        "boons": {key: boon_payload(value) for key, value in state.boons.items()},
        "offices": dict(state.offices),
        "version": state.version,
    }


def simulation_from_dict(data: Mapping) -> SimulationState:
    npcs = {
        str(key): NpcState(
            id=str(value["id"]),
            name=str(value["name"]),
            clan_id=str(value["clan_id"]),
            role=str(value["role"]),
            ambition=str(value["ambition"]),
            short_goal=str(value["short_goal"]),
            loyalty=int(value["loyalty"]),
            aggression=int(value["aggression"]),
            influence=float(value["influence"]),
            status=int(value["status"]),
            camarilla_attitude=int(value.get("camarilla_attitude", 0)),
            agenda_progress=int(value.get("agenda_progress", 0)),
            alive=bool(value.get("alive", True)),
            relations={str(k): int(v) for k, v in dict(value.get("relations", {})).items()},
        )
        for key, value in dict(data.get("npcs", {})).items()
    }
    domains = {
        str(key): DomainState(
            id=str(value["id"]),
            name=str(value["name"]),
            description=str(value["description"]),
            holder_id=(str(value["holder_id"]) if value.get("holder_id") is not None else None),
            viandis=int(value["viandis"]),
            servage=int(value["servage"]),
            rempart=int(value["rempart"]),
            pressure=int(value.get("pressure", 0)),
            masquerade_risk=int(value.get("masquerade_risk", 0)),
        )
        for key, value in dict(data.get("domains", {})).items()
    }
    rights = {
        str(key): HuntingAccessState(
            id=str(value["id"]),
            domain_id=str(value["domain_id"]),
            beneficiary_id=str(value["beneficiary_id"]),
            granted_by_id=str(value["granted_by_id"]),
            source=str(value["source"]),
            active=bool(value.get("active", True)),
            expires_year=(int(value["expires_year"]) if value.get("expires_year") is not None else None),
        )
        for key, value in dict(data.get("hunting_rights", {})).items()
    }
    boons = {
        str(key): BoonState(
            id=str(value["id"]),
            creditor_id=str(value["creditor_id"]),
            debtor_id=str(value["debtor_id"]),
            level=str(value["level"]),
            origin=str(value["origin"]),
            status=str(value.get("status", "due")),
            public=bool(value.get("public", False)),
        )
        for key, value in dict(data.get("boons", {})).items()
    }
    return SimulationState(
        game_id=str(data["game_id"]),
        year=int(data.get("year", 1435)),
        institution_stage=str(data.get("institution_stage", "project")),
        npcs=npcs,
        domains=domains,
        hunting_rights=rights,
        boons=boons,
        offices={str(k): (str(v) if v is not None else None) for k, v in dict(data.get("offices", {})).items()},
        version=int(data.get("version", 1)),
    )
