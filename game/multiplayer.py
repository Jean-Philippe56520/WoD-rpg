from __future__ import annotations

from .config import DEFAULT_RULES, GameRules
from .models import ClanNightOrders, ClanNightReport, NightStatus
from .persistence import GameRepository
from .resolution import resolve_night
from .world import REQUIRED_CLANS, candidates_from_state, create_initial_game_state


DEFAULT_GAME_ID = "main"
DEFAULT_GAME_NAME = "Chronique principale"


class MultiplayerGameService:
    def __init__(self, repository: GameRepository, rules: GameRules = DEFAULT_RULES):
        self.repository = repository
        self.rules = rules

    def ensure_default_game(self) -> None:
        self.repository.ensure_game(
            DEFAULT_GAME_ID,
            DEFAULT_GAME_NAME,
            create_initial_game_state(),
            REQUIRED_CLANS,
        )

    def validate_orders(self, state, clan_id: str, orders: ClanNightOrders) -> None:
        if orders.clan_id != clan_id:
            raise ValueError("Orders must belong to the player's clan")
        if clan_id not in state.clan_states:
            raise ValueError(f"Unknown clan: {clan_id}")

        if orders.version >= 2:
            eligible_ids = {
                character.id
                for character in state.characters.values()
                if character.clan_id == clan_id and character.id != state.prince_id
            }
            if len(orders.actions) > len(eligible_ids):
                raise ValueError("A clan cannot submit more than one action per active member")
            used_actors: set[str] = set()
            for action in orders.actions:
                if action.clan_id != clan_id:
                    raise ValueError("A player cannot submit actions for another clan")
                if not action.actor_character_id:
                    raise ValueError("V0.8 actions require an acting character")
                if action.actor_character_id not in eligible_ids:
                    raise ValueError("Action actor must be an active member of the player's clan")
                if action.actor_character_id in used_actors:
                    raise ValueError("A vampire can perform only one action per night")
                used_actors.add(action.actor_character_id)
        else:
            # Une nuit déjà soumise avant V0.8 conserve exactement son ancien budget.
            if len(orders.actions) > self.rules.actions_per_clan:
                raise ValueError(f"Maximum {self.rules.actions_per_clan} legacy actions per night")
            for action in orders.actions:
                if action.clan_id != clan_id:
                    raise ValueError("A player cannot submit actions for another clan")

        primogen_id = state.clan_states[clan_id].clan.primogen_id
        if state.prince_id is None:
            if orders.vote is None:
                raise ValueError("A Primogen vote is required while the Praxis is unresolved")
            if orders.vote.primogen_id != primogen_id:
                raise ValueError("The vote must be cast by the current Primogen")
        elif orders.vote is not None:
            raise ValueError("No Praxis vote is open while a Prince is recognized")

        if len(orders.embrace_petitions) > self.rules.embrace_petitions_per_clan:
            raise ValueError(
                f"Maximum {self.rules.embrace_petitions_per_clan} embrace petition per night"
            )
        if orders.embrace_petitions and state.prince_id is None:
            raise ValueError("No Prince is available to receive an embrace petition")
        for petition in orders.embrace_petitions:
            member = state.characters.get(petition.member_id)
            if member is None or member.clan_id != clan_id:
                raise ValueError("A Primogen may only petition for a member of their own clan")
            if petition.member_id == primogen_id:
                raise ValueError("The Primogen must petition on behalf of another clan member")
            if not petition.proposed_childe_name.strip():
                raise ValueError("A proposed childe name is required")

    def claim_clan(self, player_id: str, player_name: str, clan_id: str) -> None:
        self.ensure_default_game()
        self.repository.claim_clan(DEFAULT_GAME_ID, player_id, player_name, clan_id)

    def submit_orders(self, player_id: str, orders: ClanNightOrders) -> bool:
        self.ensure_default_game()
        state = self.repository.get_game_state(DEFAULT_GAME_ID)
        assigned_clan = self.repository.get_player_clan(DEFAULT_GAME_ID, player_id)
        if assigned_clan is None:
            raise ValueError("Player has not claimed a clan")
        self.validate_orders(state, assigned_clan, orders)
        status = self.repository.submit_orders(DEFAULT_GAME_ID, player_id, orders)
        if status == NightStatus.READY:
            return self.resolve_if_ready()
        return False

    def withdraw_orders(self, player_id: str) -> None:
        self.ensure_default_game()
        assigned_clan = self.repository.get_player_clan(DEFAULT_GAME_ID, player_id)
        if assigned_clan is None:
            raise ValueError("Player has not claimed a clan")
        self.repository.withdraw_orders(DEFAULT_GAME_ID, player_id, assigned_clan)

    def resolve_if_ready(self) -> bool:
        bundle = self.repository.try_begin_resolution(DEFAULT_GAME_ID)
        if bundle is None:
            return False
        try:
            actions = []
            votes = {}
            petitions = []
            for clan_id, orders in bundle.orders_by_clan.items():
                self.validate_orders(bundle.state, clan_id, orders)
                actions.extend(orders.actions)
                if orders.vote:
                    votes[orders.vote.primogen_id] = orders.vote
                petitions.extend((clan_id, petition) for petition in orders.embrace_petitions)

            previous_event_count = len(bundle.state.events)
            resolution = resolve_night(
                bundle.state,
                actions,
                votes,
                candidates_from_state(bundle.state),
                embrace_petitions=petitions,
                rules=self.rules,
            )
            new_events = resolution.state.events[previous_event_count:]
            reports = {
                clan_id: ClanNightReport(
                    game_id=bundle.game_id,
                    night=bundle.night,
                    clan_id=clan_id,
                    items=tuple(
                        event.message for event in new_events if event.visible_to(clan_id)
                    ),
                )
                for clan_id in REQUIRED_CLANS
            }
            self.repository.finalize_resolution(bundle, resolution.state, reports)
            return True
        except Exception:
            self.repository.abort_resolution(bundle.game_id, bundle.night)
            raise
