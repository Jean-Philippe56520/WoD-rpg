from __future__ import annotations

from dataclasses import replace
import hashlib

from .agenda_engine import agenda_effect
from .chronicle import PlayerCharacter, SIRES
from .chronicle_simulation import (
    DomainState,
    HuntingAccessState,
    NpcState,
    SimulationBeat,
    SimulationState,
    ensure_character_links,
    grant_boon,
)
from .era import CamarillaStage, EraRules, era_for_year
from .paris_lore import PARIS_1435_NPCS, ParisNpcSeed


LEGACY_EXTRA_IDS = {
    "npc_prince_godefroy",
    "npc_lasombra_aldric",
    "npc_tzimisce_dragomir",
    "npc_tremere_conrad",
    "npc_nosferatu_anne",
    "npc_malkavian_severin",
    "npc_gangrel_ilona",
    "npc_cappadocian_agnes",
    "npc_banu_haqim_farid",
}

_PARIS_SEEDS = {seed.id: seed for seed in PARIS_1435_NPCS}
_SIRE_IDS = {sire.id for sire in SIRES}


def _seed_npc(seed: ParisNpcSeed) -> NpcState:
    return NpcState(
        id=seed.id,
        name=seed.name,
        clan_id=seed.clan_id,
        role=seed.role_1435,
        ambition=seed.ambition_1435,
        short_goal=seed.short_goal_1435,
        loyalty=seed.loyalty,
        aggression=seed.aggression,
        influence=seed.influence,
        status=seed.status,
        camarilla_attitude=seed.camarilla_attitude,
        relations=dict(seed.relations),
    )


def _paris_domain_overrides() -> dict[str, tuple[str, str, str | None]]:
    return {
        "domain_haute_ville": (
            "Louvre et Saint-Germain-l'Auxerrois",
            "Pouvoir royal, maisons aristocratiques, rues fortifiées et dépendances du vieux Louvre.",
            None,
        ),
        "domain_halles_ponts": (
            "Les Halles et les Ponts",
            "Marchés, changeurs, péages, tavernes et circulation nocturne autour des franchissements de la Seine.",
            None,
        ),
        "domain_cour_enlumineurs": (
            "Université et rive gauche",
            "Collèges, libraires, copistes, clercs, étudiants et maisons religieuses de la rive gauche.",
            None,
        ),
        "domain_quais_ateliers": (
            "Quais de Seine et ateliers",
            "Bateliers, artisans, entrepôts, moulins, travailleurs et étrangers de passage.",
            None,
        ),
        "domain_faubourgs": (
            "Les Faubourgs parisiens",
            "Tavernes, soldats, pauvres, voyageurs et communautés au-delà des centres de pouvoir les plus surveillés.",
            None,
        ),
        "domain_routes_landes": (
            "Routes de Paris et lisières",
            "Chemins, relais, villages proches et refuges qui échappent partiellement aux autorités urbaines.",
            None,
        ),
        "domain_citadelle": (
            "Île de la Cité et Cour princière",
            "Cœur symbolique de Paris où l'autorité d'Alexandre tente encore de s'affirmer malgré la crise.",
            "npc_alexandre",
        ),
    }


def _referenced_actor_ids(state: SimulationState) -> set[str]:
    ids: set[str] = set()
    ids.update(holder for holder in state.offices.values() if holder)
    ids.update(domain.holder_id for domain in state.domains.values() if domain.holder_id)
    for right in state.hunting_rights.values():
        ids.add(right.beneficiary_id)
        ids.add(right.granted_by_id)
    for boon in state.boons.values():
        ids.add(boon.creditor_id)
        ids.add(boon.debtor_id)
    return ids


def parisify_simulation(state: SimulationState) -> SimulationState:
    """Attach the audited Paris 1435 seed to old and new Chronicle states.

    This is idempotent. It preserves player-created political changes. Only the
    old default Prince/domain are translated automatically to Alexandre. Legacy
    fictional NPCs are removed when nothing persistent references them.
    """

    npcs = dict(state.npcs)
    for seed in PARIS_1435_NPCS:
        npcs.setdefault(seed.id, _seed_npc(seed))

    domains = dict(state.domains)
    for domain_id, (name, description, canonical_holder) in _paris_domain_overrides().items():
        existing = domains.get(domain_id)
        if existing is None:
            continue
        holder = existing.holder_id
        if domain_id == "domain_citadelle" and holder in {None, "npc_prince_godefroy"}:
            holder = canonical_holder
        domains[domain_id] = replace(existing, name=name, description=description, holder_id=holder)

    offices = dict(state.offices)
    if offices.get("prince") in {None, "npc_prince_godefroy"}:
        offices["prince"] = "npc_alexandre"

    current = replace(state, npcs=npcs, domains=domains, offices=offices)
    referenced = _referenced_actor_ids(current)
    clean_npcs = dict(current.npcs)
    for legacy_id in LEGACY_EXTRA_IDS:
        if legacy_id not in referenced:
            clean_npcs.pop(legacy_id, None)
    return replace(current, npcs=clean_npcs)


def _is_local_actor(npc_id: str) -> bool:
    if npc_id in _SIRE_IDS:
        return True
    seed = _PARIS_SEEDS.get(npc_id)
    return seed is not None and seed.location_1435 == "Paris"


def _intent_for(npc: NpcState) -> str:
    seed = _PARIS_SEEDS.get(npc.id)
    return seed.active_plan if seed and seed.active_plan else npc.ambition


def _deterministic_score(seed: str, modulus: int = 100) -> int:
    return int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:4], "big") % modulus


def _bounded_relation(value: int) -> int:
    return max(-3, min(3, value))


def _change_relation(
    state: SimulationState,
    actor_id: str,
    target_id: str,
    delta: int,
) -> SimulationState:
    npcs = dict(state.npcs)
    actor = npcs[actor_id]
    target = npcs[target_id]
    actor_relations = dict(actor.relations)
    target_relations = dict(target.relations)
    actor_relations[target_id] = _bounded_relation(actor_relations.get(target_id, 0) + delta)
    target_relations[actor_id] = _bounded_relation(target_relations.get(actor_id, 0) + delta)
    npcs[actor_id] = replace(actor, relations=actor_relations)
    npcs[target_id] = replace(target, relations=target_relations)
    return replace(state, npcs=npcs)


def _advance_actor_counter(state: SimulationState, npc_id: str, score: int) -> SimulationState:
    npcs = dict(state.npcs)
    actor = npcs[npc_id]
    npcs[npc_id] = replace(
        actor,
        agenda_progress=actor.agenda_progress + 1 + (1 if score >= 80 else 0),
        influence=max(0.0, actor.influence + (0.25 if score >= 70 else 0.0)),
    )
    return replace(state, npcs=npcs)


def _grant_temporary_hunting_access(
    state: SimulationState,
    *,
    grantor_id: str,
    beneficiary_id: str,
    year: int,
    chapter: int,
    segment: int,
) -> tuple[SimulationState, DomainState] | None:
    domain = next((item for item in state.domains.values() if item.holder_id == grantor_id), None)
    if domain is None:
        return None
    right_id = "right_npc_" + hashlib.sha256(
        f"{state.game_id}:{year}:{chapter}:{segment}:{grantor_id}:{beneficiary_id}:{domain.id}".encode("utf-8")
    ).hexdigest()[:16]
    rights = dict(state.hunting_rights)
    rights[right_id] = HuntingAccessState(
        id=right_id,
        domain_id=domain.id,
        beneficiary_id=beneficiary_id,
        granted_by_id=grantor_id,
        source=f"Accord politique autonome — chapitre {chapter}, segment {segment}",
        expires_year=year + 2,
    )
    return replace(state, hunting_rights=rights), domain


def _era_context(era: EraRules, npc: NpcState) -> str:
    if era.camarilla_stage in {CamarillaStage.PROJECT, CamarillaStage.COALITION} and npc.camarilla_attitude >= 1:
        return "la coalition caïnite naissante"
    if era.anarch_revolt_active and npc.camarilla_attitude <= -1:
        return "les réseaux anarchs"
    return "les équilibres de la nuit parisienne"


def _social_action(
    state: SimulationState,
    *,
    npc_id: str,
    era: EraRules,
    year: int,
    chapter: int,
    segment: int,
) -> tuple[SimulationState, SimulationBeat]:
    actor = state.npcs[npc_id]
    target_ids = sorted(
        target_id
        for target_id, target in state.npcs.items()
        if target_id != npc_id and target.alive and _is_local_actor(target_id)
    )
    score = _deterministic_score(f"social:{npc_id}:{year}:{chapter}:{segment}")
    current = _advance_actor_counter(state, npc_id, score)

    if not target_ids:
        return current, SimulationBeat(
            actor_id=actor.id,
            actor_name=actor.name,
            category="npc_agenda",
            public_text=f"{actor.name} poursuit discrètement son objectif du moment.",
            hidden_intent=_intent_for(actor),
        )

    target_id = target_ids[_deterministic_score(f"target:{npc_id}:{year}:{chapter}:{segment}", len(target_ids))]
    target = current.npcs[target_id]
    effect = agenda_effect(actor, score)

    if effect == 0:
        current = _change_relation(current, npc_id, target_id, 1)
        beat = SimulationBeat(
            actor_id=actor.id,
            actor_name=actor.name,
            category="alliance_building",
            public_text=f"{actor.name} se rapproche de {target.name} autour d'un intérêt commun lié à {_era_context(era, actor)}.",
            hidden_intent=_intent_for(actor),
        )
    elif effect == 1:
        current = _change_relation(current, npc_id, target_id, -1)
        beat = SimulationBeat(
            actor_id=actor.id,
            actor_name=actor.name,
            category="political_rivalry",
            public_text=f"Une tension ouverte oppose désormais {actor.name} à {target.name} sur la conduite des affaires nocturnes.",
            hidden_intent=_intent_for(actor),
        )
    elif effect == 2:
        current = grant_boon(
            current,
            creditor_id=npc_id,
            debtor_id=target_id,
            level="minor",
            origin=f"Accord autonome {year} C{chapter}S{segment} : {actor.name} / {target.name}",
            public=False,
        )
        current = _change_relation(current, npc_id, target_id, 1)
        beat = SimulationBeat(
            actor_id=actor.id,
            actor_name=actor.name,
            category="prestation",
            public_text=f"Après une négociation discrète, {target.name} doit désormais une faveur à {actor.name}.",
            hidden_intent=_intent_for(actor),
        )
    else:
        grant = _grant_temporary_hunting_access(
            current,
            grantor_id=npc_id,
            beneficiary_id=target_id,
            year=year,
            chapter=chapter,
            segment=segment,
        )
        if grant is not None:
            current, domain = grant
            current = _change_relation(current, npc_id, target_id, 1)
            beat = SimulationBeat(
                actor_id=actor.id,
                actor_name=actor.name,
                category="hunting_patronage",
                public_text=f"{actor.name} accorde temporairement à {target.name} un accès de chasse sur {domain.name}.",
                hidden_intent=_intent_for(actor),
            )
        else:
            current = grant_boon(
                current,
                creditor_id=npc_id,
                debtor_id=target_id,
                level="minor",
                origin=f"Soutien autonome {year} C{chapter}S{segment} : {actor.name} / {target.name}",
                public=False,
            )
            current = _change_relation(current, npc_id, target_id, 1)
            beat = SimulationBeat(
                actor_id=actor.id,
                actor_name=actor.name,
                category="political_patronage",
                public_text=f"{actor.name} rend un service politique à {target.name}, créant une dette durable.",
                hidden_intent=_intent_for(actor),
            )

    return current, beat


def advance_paris_simulation(
    state: SimulationState,
    *,
    year: int,
    chapter: int,
    segment: int,
    characters: list[PlayerCharacter],
) -> tuple[SimulationState, tuple[SimulationBeat, ...]]:
    """Advance Paris as a society: relations, Prestation and access can change."""

    era = era_for_year(year)
    current = parisify_simulation(replace(state, year=year, institution_stage=era.camarilla_stage.value))
    for character in characters:
        if character.is_active:
            current = ensure_character_links(current, character)

    candidate_ids = [
        npc_id
        for npc_id, npc in current.npcs.items()
        if npc.alive and _is_local_actor(npc_id)
    ]
    candidate_ids.sort(key=lambda npc_id: _deterministic_score(f"order:{year}:{chapter}:{segment}:{npc_id}"))
    selected = candidate_ids[:4]

    beats: list[SimulationBeat] = []
    for npc_id in selected:
        current, beat = _social_action(
            current,
            npc_id=npc_id,
            era=era,
            year=year,
            chapter=chapter,
            segment=segment,
        )
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

    return replace(current, domains=domains), tuple(beats)
