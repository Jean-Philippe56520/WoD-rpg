from __future__ import annotations

import json
from dataclasses import asdict

from .models import (
    ActionType,
    AxisPolarity,
    BloodRank,
    Boon,
    BoonLevel,
    BoonStatus,
    Character,
    Clan,
    ClanFactionSide,
    ClanNightOrders,
    ClanNightReport,
    ClanPoliticalState,
    EmbracePetitionOrder,
    EmbraceRequest,
    EmbraceStatus,
    GameAction,
    GameEvent,
    GameState,
    Grievance,
    MortalStance,
    OrderStance,
    PoliticalAmbition,
    PoliticalPromise,
    PoliticalRequest,
    PoliticalRequestDecisionOrder,
    PoliticalRequestStatus,
    PoliticalRequestType,
    PrimogenPosition,
    PrimogenVote,
    PromiseStatus,
    RequestDecision,
)


def _character_to_dict(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "clan_id": character.clan_id,
        "personal_influence": character.personal_influence,
        "mortal_stance": character.mortal_stance.value,
        "order_stance": character.order_stance.value,
        "humanity": character.humanity,
        "status": character.status,
        "reputation": character.reputation,
        "political_ambition": character.political_ambition.value,
        "physical": character.physical,
        "social": character.social,
        "mental": character.mental,
        "expertises": list(character.expertises),
        "disciplines": dict(character.disciplines),
        "blood_rank": character.blood_rank.value,
        "backgrounds": dict(character.backgrounds),
        "relation_to_primogen": character.relation_to_primogen,
        "relations": dict(character.relations),
        "loyalty": character.loyalty,
        "ambition": character.ambition,
        "is_primogen": character.is_primogen,
    }


def _legacy_polarity(value: dict, new_key: str, old_key: str) -> AxisPolarity:
    if new_key in value:
        return AxisPolarity(value[new_key])
    legacy_value = float(value.get(old_key, 0.0))
    return AxisPolarity.PLUS if legacy_value >= 0 else AxisPolarity.MINUS


def _mortal_stance(value: dict, default_sheet: Character | None) -> MortalStance:
    if "mortal_stance" in value:
        return MortalStance(value["mortal_stance"])
    if "humanity_axis" in value or "humanism" in value:
        polarity = _legacy_polarity(value, "humanity_axis", "humanism")
        return MortalStance.HUMANIST if polarity == AxisPolarity.PLUS else MortalStance.PREDATORY
    return default_sheet.mortal_stance if default_sheet else MortalStance.HUMANIST


def _order_stance(value: dict, default_sheet: Character | None) -> OrderStance:
    if "order_stance" in value:
        return OrderStance(value["order_stance"])
    if "tradition_axis" in value or "tradition" in value:
        polarity = _legacy_polarity(value, "tradition_axis", "tradition")
        return OrderStance.ORTHODOX if polarity == AxisPolarity.PLUS else OrderStance.REFORMIST
    return default_sheet.order_stance if default_sheet else OrderStance.ORTHODOX


def _legacy_relation_to_primogen(value: dict, default_sheet: Character | None) -> int:
    if "relation_to_primogen" in value:
        return int(value["relation_to_primogen"])
    if "loyalty" in value:
        loyalty = float(value["loyalty"])
        if loyalty >= 67:
            return 2
        if loyalty >= 40:
            return 1
        return 0
    return default_sheet.relation_to_primogen if default_sheet else 1


def _character_from_dict(value: dict, default_sheet: Character | None = None) -> Character:
    physical_default = default_sheet.physical if default_sheet else 1
    social_default = default_sheet.social if default_sheet else 1
    mental_default = default_sheet.mental if default_sheet else 1
    expertise_default = default_sheet.expertises if default_sheet else ()
    discipline_default = default_sheet.disciplines if default_sheet else {}
    blood_rank_default = default_sheet.blood_rank if default_sheet else BloodRank.NEWBORN
    background_default = default_sheet.backgrounds if default_sheet else {}
    relations_default = default_sheet.relations if default_sheet else {}
    humanity_default = default_sheet.humanity if default_sheet else 7
    status_default = default_sheet.status if default_sheet else 1
    reputation_default = default_sheet.reputation if default_sheet else 0
    political_ambition_default = (
        default_sheet.political_ambition
        if default_sheet
        else PoliticalAmbition.INCREASE_INFLUENCE
    )

    humanity_value = value.get("humanity", humanity_default)
    try:
        humanity_value = int(humanity_value)
    except (TypeError, ValueError):
        humanity_value = humanity_default
    if not 0 <= humanity_value <= 10:
        humanity_value = humanity_default

    return Character(
        id=value["id"],
        name=value["name"],
        clan_id=value.get("clan_id"),
        personal_influence=float(value.get("personal_influence", 0.0)),
        mortal_stance=_mortal_stance(value, default_sheet),
        order_stance=_order_stance(value, default_sheet),
        humanity=humanity_value,
        status=int(value.get("status", status_default)),
        reputation=int(value.get("reputation", reputation_default)),
        political_ambition=PoliticalAmbition(
            value.get("political_ambition", political_ambition_default.value)
        ),
        physical=int(value.get("physical", physical_default)),
        social=int(value.get("social", social_default)),
        mental=int(value.get("mental", mental_default)),
        expertises=tuple(value.get("expertises", expertise_default)),
        disciplines={k: int(v) for k, v in value.get("disciplines", discipline_default).items()},
        blood_rank=BloodRank(value.get("blood_rank", blood_rank_default.value)),
        backgrounds={k: int(v) for k, v in value.get("backgrounds", background_default).items()},
        relation_to_primogen=_legacy_relation_to_primogen(value, default_sheet),
        relations={k: int(v) for k, v in value.get("relations", relations_default).items()},
        loyalty=float(value.get("loyalty", 50.0)),
        ambition=float(value.get("ambition", 50.0)),
        is_primogen=bool(value.get("is_primogen", False)),
    )


def game_state_to_dict(state: GameState) -> dict:
    return {
        "night": state.night,
        "camarilla_stability": state.camarilla_stability,
        "masquerade_integrity": state.masquerade_integrity,
        "prince_id": state.prince_id,
        "prince_political_capital": state.prince_political_capital,
        "prince_relations": state.prince_relations,
        "praxis_status": state.praxis_status,
        "characters": {key: _character_to_dict(value) for key, value in state.characters.items()},
        "clan_states": {
            key: {
                "clan": asdict(value.clan),
                "faction_memberships": {
                    character_id: ClanFactionSide(side).value
                    for character_id, side in value.faction_memberships.items()
                },
                "opposition_leader_id": value.opposition_leader_id,
                "opposition_allied_primogen_id": value.opposition_allied_primogen_id,
                "known_character_intel": value.known_character_intel,
                "relations": value.relations,
                "current_loyalties": value.current_loyalties,
                "current_allies": value.current_allies,
            }
            for key, value in state.clan_states.items()
        },
        "embrace_requests": {
            key: {
                "id": value.id,
                "requester_id": value.requester_id,
                "proposed_childe_name": value.proposed_childe_name,
                "primogen_position": value.primogen_position.value,
                "political_cost": value.political_cost,
                "created_night": value.created_night,
                "submitted_by_primogen_id": value.submitted_by_primogen_id,
                "status": value.status.value,
                "decision_night": value.decision_night,
            }
            for key, value in state.embrace_requests.items()
        },
        "boons": {
            key: {
                "id": value.id,
                "creditor_id": value.creditor_id,
                "debtor_id": value.debtor_id,
                "level": value.level.value,
                "origin": value.origin,
                "created_night": value.created_night,
                "status": value.status.value,
                "public": value.public,
                "called_night": value.called_night,
                "resolved_night": value.resolved_night,
            }
            for key, value in state.boons.items()
        },
        "grievances": {key: asdict(value) for key, value in state.grievances.items()},
        "political_requests": {
            key: {
                "id": value.id,
                "clan_id": value.clan_id,
                "requester_id": value.requester_id,
                "request_type": value.request_type.value,
                "description": value.description,
                "created_night": value.created_night,
                "target_id": value.target_id,
                "offered_boon_level": (
                    value.offered_boon_level.value if value.offered_boon_level else None
                ),
                "status": value.status.value,
                "response_night": value.response_night,
            }
            for key, value in state.political_requests.items()
        },
        "promises": {
            key: {
                "id": value.id,
                "promisor_id": value.promisor_id,
                "beneficiary_id": value.beneficiary_id,
                "description": value.description,
                "created_night": value.created_night,
                "due_night": value.due_night,
                "request_id": value.request_id,
                "status": value.status.value,
                "resolved_night": value.resolved_night,
            }
            for key, value in state.promises.items()
        },
        "events": [
            {
                "night": event.night,
                "category": event.category,
                "message": event.message,
                "audience_clan_ids": list(event.audience_clan_ids) if event.audience_clan_ids else None,
            }
            for event in state.events
        ],
    }


def game_state_from_dict(data: dict) -> GameState:
    character_payloads = data.get("characters", {})
    defaults: dict[str, Character] = {}
    new_sheet_fields = {
        "physical",
        "expertises",
        "disciplines",
        "blood_rank",
        "backgrounds",
        "relation_to_primogen",
        "mortal_stance",
        "order_stance",
        "status",
        "reputation",
        "political_ambition",
    }
    if any(not new_sheet_fields.issubset(value) for value in character_payloads.values()):
        from .world import seed_characters

        defaults = seed_characters()

    characters = {
        key: _character_from_dict(value, defaults.get(key))
        for key, value in character_payloads.items()
    }
    clan_states = {}
    for key, value in data.get("clan_states", {}).items():
        raw_memberships = value.get("faction_memberships", value.get("coterie_memberships", {}))
        clan_states[key] = ClanPoliticalState(
            clan=Clan(**value["clan"]),
            faction_memberships={
                character_id: ClanFactionSide(side)
                for character_id, side in raw_memberships.items()
            },
            opposition_leader_id=value.get("opposition_leader_id"),
            opposition_allied_primogen_id=value.get("opposition_allied_primogen_id"),
            known_character_intel={
                k: int(v) for k, v in value.get("known_character_intel", {}).items()
            },
            relations={k: float(v) for k, v in value.get("relations", {}).items()},
            current_loyalties={
                k: float(v) for k, v in value.get("current_loyalties", {}).items()
            },
            current_allies=dict(value.get("current_allies", {})),
        )

    embrace_requests = {
        key: EmbraceRequest(
            id=value["id"],
            requester_id=value["requester_id"],
            proposed_childe_name=value["proposed_childe_name"],
            primogen_position=PrimogenPosition(value["primogen_position"]),
            political_cost=float(value["political_cost"]),
            created_night=int(value["created_night"]),
            submitted_by_primogen_id=value.get("submitted_by_primogen_id"),
            status=EmbraceStatus(value["status"]),
            decision_night=value.get("decision_night"),
        )
        for key, value in data.get("embrace_requests", {}).items()
    }
    boons = {
        key: Boon(
            id=value["id"],
            creditor_id=value["creditor_id"],
            debtor_id=value["debtor_id"],
            level=BoonLevel(value["level"]),
            origin=value.get("origin", "Prestation"),
            created_night=int(value["created_night"]),
            status=BoonStatus(value.get("status", BoonStatus.DUE.value)),
            public=bool(value.get("public", False)),
            called_night=value.get("called_night"),
            resolved_night=value.get("resolved_night"),
        )
        for key, value in data.get("boons", {}).items()
    }
    grievances = {
        key: Grievance(
            id=value["id"],
            owner_id=value["owner_id"],
            target_id=value["target_id"],
            reason=value["reason"],
            severity=int(value["severity"]),
            created_night=int(value["created_night"]),
            resolved=bool(value.get("resolved", False)),
        )
        for key, value in data.get("grievances", {}).items()
    }
    political_requests = {
        key: PoliticalRequest(
            id=value["id"],
            clan_id=value["clan_id"],
            requester_id=value["requester_id"],
            request_type=PoliticalRequestType(value["request_type"]),
            description=value["description"],
            created_night=int(value["created_night"]),
            target_id=value.get("target_id"),
            offered_boon_level=(
                BoonLevel(value["offered_boon_level"])
                if value.get("offered_boon_level")
                else None
            ),
            status=PoliticalRequestStatus(value.get("status", PoliticalRequestStatus.OPEN.value)),
            response_night=value.get("response_night"),
        )
        for key, value in data.get("political_requests", {}).items()
    }
    promises = {
        key: PoliticalPromise(
            id=value["id"],
            promisor_id=value["promisor_id"],
            beneficiary_id=value["beneficiary_id"],
            description=value["description"],
            created_night=int(value["created_night"]),
            due_night=int(value["due_night"]),
            request_id=value.get("request_id"),
            status=PromiseStatus(value.get("status", PromiseStatus.PENDING.value)),
            resolved_night=value.get("resolved_night"),
        )
        for key, value in data.get("promises", {}).items()
    }
    events = [
        GameEvent(
            night=int(event["night"]),
            category=event["category"],
            message=event["message"],
            audience_clan_ids=(
                tuple(event["audience_clan_ids"])
                if event.get("audience_clan_ids")
                else None
            ),
        )
        for event in data.get("events", [])
    ]
    state = GameState(
        night=int(data.get("night", 1)),
        camarilla_stability=float(data.get("camarilla_stability", 100.0)),
        masquerade_integrity=float(data.get("masquerade_integrity", 100.0)),
        prince_id=data.get("prince_id"),
        prince_political_capital=float(data.get("prince_political_capital", 0.0)),
        prince_relations={k: float(v) for k, v in data.get("prince_relations", {}).items()},
        praxis_status=data.get("praxis_status", "vacant"),
        characters=characters,
        clan_states=clan_states,
        embrace_requests=embrace_requests,
        boons=boons,
        grievances=grievances,
        political_requests=political_requests,
        promises=promises,
        events=events,
    )
    from .factions import initialize_factions
    from .social_politics import generate_requests_for_night

    initialize_factions(state)
    generate_requests_for_night(state)
    return state


def game_state_to_json(state: GameState) -> str:
    return json.dumps(game_state_to_dict(state), ensure_ascii=False, sort_keys=True)


def game_state_from_json(raw: str) -> GameState:
    return game_state_from_dict(json.loads(raw))


def clan_orders_to_dict(orders: ClanNightOrders) -> dict:
    return {
        "version": orders.version,
        "clan_id": orders.clan_id,
        "actions": [
            {
                "clan_id": action.clan_id,
                "action_type": action.action_type.value,
                "actor_character_id": action.actor_character_id,
                "target_character_id": action.target_character_id,
                "target_clan_id": action.target_clan_id,
                "target_current_id": action.target_current_id,
            }
            for action in orders.actions
        ],
        "vote": (
            {
                "primogen_id": orders.vote.primogen_id,
                "candidate_id": orders.vote.candidate_id,
            }
            if orders.vote
            else None
        ),
        "embrace_petitions": [asdict(petition) for petition in orders.embrace_petitions],
        "request_decisions": [
            {"request_id": item.request_id, "decision": item.decision.value}
            for item in orders.request_decisions
        ],
    }


def clan_orders_from_dict(data: dict) -> ClanNightOrders:
    return ClanNightOrders(
        clan_id=data["clan_id"],
        actions=tuple(
            GameAction(
                clan_id=action["clan_id"],
                action_type=ActionType(action["action_type"]),
                actor_character_id=action.get("actor_character_id"),
                target_character_id=action.get("target_character_id"),
                target_clan_id=action.get("target_clan_id"),
                target_current_id=action.get("target_current_id"),
            )
            for action in data.get("actions", [])
        ),
        vote=(
            PrimogenVote(
                primogen_id=data["vote"]["primogen_id"],
                candidate_id=data["vote"]["candidate_id"],
            )
            if data.get("vote")
            else None
        ),
        embrace_petitions=tuple(
            EmbracePetitionOrder(**petition)
            for petition in data.get("embrace_petitions", [])
        ),
        request_decisions=tuple(
            PoliticalRequestDecisionOrder(
                request_id=item["request_id"],
                decision=RequestDecision(item["decision"]),
            )
            for item in data.get("request_decisions", [])
        ),
        version=int(data.get("version", 1)),
    )


def clan_orders_to_json(orders: ClanNightOrders) -> str:
    return json.dumps(clan_orders_to_dict(orders), ensure_ascii=False, sort_keys=True)


def clan_orders_from_json(raw: str) -> ClanNightOrders:
    return clan_orders_from_dict(json.loads(raw))


def report_to_json(report: ClanNightReport) -> str:
    return json.dumps(asdict(report), ensure_ascii=False, sort_keys=True)


def report_from_json(raw: str) -> ClanNightReport:
    data = json.loads(raw)
    return ClanNightReport(
        game_id=data["game_id"],
        night=int(data["night"]),
        clan_id=data["clan_id"],
        items=tuple(data.get("items", [])),
    )
