from dataclasses import dataclass


@dataclass(frozen=True)
class GameRules:
    opposition_transfer_ratio: float = 0.50
    opposition_support_threshold: float = 50.0
    praxis_recognition_threshold: float = 0.50
    actions_per_clan: int = 2

    consolidate_shift: float = 4.0
    consolidate_loyalty_penalty: float = 4.0
    rally_loyalty_gain: float = 12.0
    influence_gain_dominant: float = 3.0
    influence_gain_opposition: float = 1.0
    diplomacy_gain: float = 8.0

    disputed_stability_loss: float = 4.0
    disputed_masquerade_loss: float = 1.0
    transition_stability_gain: float = 1.0
    recognized_stability_gain: float = 3.0


DEFAULT_RULES = GameRules()
