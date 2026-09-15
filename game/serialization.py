from __future__ import annotations

import json
from dataclasses import asdict

from .models import (
    ActionType,
    AxisPolarity,
    BloodRank,
    Character,
    Clan,
    ClanNightOrders,
    ClanNightReport,
    ClanPoliticalState,
    EmbracePetitionOrder,
    EmbraceRequest,
    EmbraceStatus,
    GameAction,
    GameEvent,
    GameState,
    PrimogenPosition,
    PrimogenVote,
)


def _character_to_dict(character: Character) -> dict:
    return {
        "id": character.id,
        "name": character.name,
        "clan_id": character.clan_id,
        "personal_influence": character.personal_influence,
        "humanity_axis": character.humanity_axis.value,
        "tradition_axis": character.tradition_axis.value,
        "physical": character.physical,
        "social": character.social,
        "mental": character.mental,
        "expertises": list(character.expertises),
        "disciplines": dict(character.disciplines),
        "blood_rank": character.blood_rank.value,
        "backgrounds": dict(character.backgrounds),
        "loyalty": character.loyalty,
        "ambition": character.ambition,
        "is_primogen": character.is_primogen,
    }


def _legacy_axis(value: dict, new_key: str, old_key: str) -> AxisPolarity:
    if new_key in value:
        return AxisPolarity(value[new_key])
    legacy_value = float(value.get(old_key, 0.0))
    return AxisPolarity.PLUS if legacy_value >= 0 else AxisPolarity.MINUS


def _character_from_dict(value: dict) -> Character:
    return Character(
        id=value["id"],
        name=value["name"],
        clan_id=value.get("clan_id"),
        personal_influence=float(value.get("personal_influence", 0.0)),
        humanity_axis=_legacy_axis(value, "humanity_axis", "humanism"),
        tradition_axis=_legacy_axis(value, "tradition_axis", "tradition"),
        physical=int(value.get("physical", 1)),
        social=int(value.get("social", 1)),
        mental=int(value.get("mental", 1)),
        expertises=tuple(value.get("expertises", ())),
        disciplines={k: int(v) for k, v in value.get("disciplines", {}).items()},
        blood_rank=BloodRank(value.get("blood_rank", BloodRank.NEWBORN.value)),
        backgrounds={k: int(v) for k, v in value.get("backgrounds", {}).items()},
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
                "current_loyalties": value.current_loyalties,
                "current_allies": value.current_allies,
                "relations": value.relations,
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
    characters = {
        key: _character_from_dict(value)
        for key, value in data.get("characters", {}).items()
    }
    clan_states = {
        key: ClanPoliticalState(
            clan=Clan(**value["clan"]),
            current_loyalties={k: float(v) for k, v in value.get("current_loyalties", {}).items()},
            current_allies=dict(value.get("current_allies", {})),
            relations={k: float(v) for k, v in value.get("relations", {}).items()},
        )
        for key, value in data.get("clan_states", {}).items()
    }
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
    return GameState(
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
        events=events,
    )


def game_state_to_json(state: GameState) -> str:
    return json.dumps(game_state_to_dict(state), ensure_ascii=False, sort_keys=True)


def game_state_from_json(raw: str) -> GameState:
    return game_state_from_dict(json.loads(raw))


def clan_orders_to_dict(orders: ClanNightOrders) -> dict:
    return {
        "clan_id": orders.clan_id,
        "actions": [
            {
                "clan_id": action.clan_id,
                "action_type": action.action_type.value,
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
    }


def clan_orders_from_dict(data: dict) -> ClanNightOrders:
    return ClanNightOrders(
        clan_id=data["clan_id"],
        actions=tuple(
            GameAction(
                clan_id=action["clan_id"],
                action_type=ActionType(action["action_type"]),
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
