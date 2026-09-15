from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from .coteries import initialize_coteries
from .models import ClanNightOrders, ClanNightReport, GameState


PRODUCTION_MODE = "production"
WORKSHOP_MODE = "workshop"
PRODUCTION_GAME_ID = "main"
WORKSHOP_GAME_ID = "workshop"
WORKSHOP_GAME_NAME = "Atelier de développement"

WORKSHOP_PLAYERS: dict[str, tuple[str, str]] = {
    "ventrue": ("workshop:ventrue", "Atelier Ventrue"),
    "toreador": ("workshop:toreador", "Atelier Toreador"),
    "brujah": ("workshop:brujah", "Atelier Brujah"),
}

_runtime_mode: ContextVar[str] = ContextVar("wod_runtime_mode", default=PRODUCTION_MODE)


def set_runtime_mode(mode: str) -> None:
    if mode not in {PRODUCTION_MODE, WORKSHOP_MODE}:
        raise ValueError(f"Unknown runtime mode: {mode}")
    _runtime_mode.set(mode)


def get_runtime_mode() -> str:
    return _runtime_mode.get()


def is_workshop_mode() -> bool:
    return get_runtime_mode() == WORKSHOP_MODE


def routed_game_id(requested_game_id: str) -> str:
    """Route les appels historiques à ``main`` vers l'Atelier quand il est actif.

    Le mode Atelier n'a jamais le droit de cibler un autre identifiant de partie.
    Inversement, le runtime de production ne peut pas ouvrir directement la sandbox.
    """

    if is_workshop_mode():
        if requested_game_id not in {PRODUCTION_GAME_ID, WORKSHOP_GAME_ID}:
            raise ValueError("Workshop runtime cannot access another game")
        return WORKSHOP_GAME_ID
    if requested_game_id == WORKSHOP_GAME_ID:
        raise ValueError("Workshop game is unavailable from the production runtime")
    return requested_game_id


@dataclass(frozen=True)
class RuntimeBackendLabel:
    base: str

    def __str__(self) -> str:
        if is_workshop_mode():
            return f"{self.base} · Atelier isolé"
        return self.base

    def __format__(self, format_spec: str) -> str:
        return format(str(self), format_spec)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, RuntimeBackendLabel):
            return self.base == other.base
        if isinstance(other, str):
            if other == "Supabase" and is_workshop_mode():
                # L'UI historique utilise cette comparaison pour décider si Auth est requise.
                # L'Atelier reste sur Supabase mais ne doit jamais passer par Supabase Auth.
                return False
            return self.base == other
        return False


class RuntimeGameRepository:
    """Proxy de confinement entre la chronique ``main`` et la sandbox ``workshop``.

    L'interface historique peut continuer à demander ``main``. Le proxy décide du
    véritable identifiant à partir du contexte d'exécution courant. Cette barrière
    est placée au niveau persistance afin qu'une erreur d'UI ne puisse pas écrire
    dans la chronique principale pendant un test Atelier.
    """

    def __init__(self, delegate: Any):
        self.delegate = delegate

    def _game_id(self, game_id: str) -> str:
        return routed_game_id(game_id)

    def ensure_game(self, game_id: str, name: str, state: GameState, required_clans: tuple[str, ...]) -> None:
        target = self._game_id(game_id)
        target_name = WORKSHOP_GAME_NAME if target == WORKSHOP_GAME_ID else name
        self.delegate.ensure_game(target, target_name, state, required_clans)

    def get_game_state(self, game_id: str) -> GameState:
        state = self.delegate.get_game_state(self._game_id(game_id))
        initialize_coteries(state)
        return state

    def get_game_info(self, game_id: str) -> dict:
        return self.delegate.get_game_info(self._game_id(game_id))

    def claim_clan(self, game_id: str, player_id: str, player_name: str, clan_id: str) -> None:
        self.delegate.claim_clan(self._game_id(game_id), player_id, player_name, clan_id)

    def get_player_clan(self, game_id: str, player_id: str) -> str | None:
        return self.delegate.get_player_clan(self._game_id(game_id), player_id)

    def list_assignments(self, game_id: str) -> dict[str, str]:
        return self.delegate.list_assignments(self._game_id(game_id))

    def submit_orders(self, game_id: str, player_id: str, orders: ClanNightOrders):
        return self.delegate.submit_orders(self._game_id(game_id), player_id, orders)

    def submission_statuses(self, game_id: str) -> dict[str, bool]:
        return self.delegate.submission_statuses(self._game_id(game_id))

    def try_begin_resolution(self, game_id: str):
        bundle = self.delegate.try_begin_resolution(self._game_id(game_id))
        if bundle is not None:
            initialize_coteries(bundle.state)
        return bundle

    def abort_resolution(self, game_id: str, night: int) -> None:
        self.delegate.abort_resolution(self._game_id(game_id), night)

    def finalize_resolution(self, bundle, state: GameState, reports: dict[str, ClanNightReport]) -> None:
        self.delegate.finalize_resolution(bundle, state, reports)

    def get_report(self, game_id: str, night: int, clan_id: str) -> ClanNightReport | None:
        return self.delegate.get_report(self._game_id(game_id), night, clan_id)

    def list_reports(self, game_id: str, clan_id: str) -> list[ClanNightReport]:
        return self.delegate.list_reports(self._game_id(game_id), clan_id)

    def post_elysium_message(self, game_id: str, player_id: str, clan_id: str, body: str) -> None:
        self.delegate.post_elysium_message(self._game_id(game_id), player_id, clan_id, body)

    def list_elysium_messages(self, game_id: str, limit: int = 100) -> list[dict]:
        return self.delegate.list_elysium_messages(self._game_id(game_id), limit)

    def get_submitted_orders(self, game_id: str, clan_id: str) -> ClanNightOrders | None:
        return self.delegate.get_submitted_orders(self._game_id(game_id), clan_id)

    def withdraw_orders(self, game_id: str, player_id: str, clan_id: str) -> None:
        self.delegate.withdraw_orders(self._game_id(game_id), player_id, clan_id)

    def reset_workshop_game(
        self,
        name: str,
        state: GameState,
        required_clans: tuple[str, ...],
    ) -> None:
        if not is_workshop_mode():
            raise ValueError("Workshop reset is forbidden from the production runtime")
        self.delegate.reset_game(WORKSHOP_GAME_ID, name, state, required_clans)
