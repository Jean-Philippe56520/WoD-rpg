from dataclasses import dataclass


@dataclass(frozen=True)
class GameRules:
    opposition_transfer_ratio: float = 0.50
    current_support_threshold: float = 50.0
    current_default_loyalty: float = 50.0
    ideology_support_scale: float = 0.15
    praxis_recognition_threshold: float = 0.50
    actions_per_clan: int = 2
    embrace_petitions_per_clan: int = 1

    consolidate_influence_gain: float = 3.0
    consolidate_rival_loyalty_penalty: float = 4.0
    rally_current_loyalty_gain: float = 12.0
    influence_gain_primogen: float = 2.0
    influence_gain_peer: float = 1.0
    diplomacy_gain: float = 8.0
    ideology_diplomacy_scale: float = 0.05
    diplomacy_minimum_gain: float = 1.0

    disputed_stability_loss: float = 4.0
    disputed_masquerade_loss: float = 1.0
    recognized_stability_gain: float = 3.0

    prince_initial_capital: float = 40.0
    succession_current_weight: float = 0.25
    succession_ambition_weight: float = 0.10
    succession_loyalty_weight: float = 0.10
    succession_loyalty_reset: float = 50.0

    embrace_base_cost: float = 10.0
    embrace_same_prince_clan_modifier: float = 3.0
    embrace_other_clan_modifier: float = -2.0
    embrace_primogen_current_modifier: float = -2.0
    embrace_rival_current_modifier: float = 3.0
    embrace_primogen_support_modifier: float = -2.0
    embrace_primogen_neutral_modifier: float = 0.0
    embrace_primogen_oppose_modifier: float = 4.0
    embrace_minimum_cost: float = 1.0
    embrace_requester_influence_gain: float = 2.0
    prince_auto_refusal_relation_floor: float = -10.0

    approve_relation_support: float = 3.0
    approve_relation_neutral: float = 0.0
    approve_relation_oppose: float = -8.0
    refuse_relation_support: float = -5.0
    refuse_relation_neutral: float = -2.0
    refuse_relation_oppose: float = 2.0
    rival_loyalty_approve_support: float = 2.0
    rival_loyalty_approve_neutral: float = -1.0
    rival_loyalty_approve_oppose: float = -5.0
    rival_loyalty_refuse_support: float = 2.0
    rival_loyalty_refuse_neutral: float = -1.0
    rival_loyalty_refuse_oppose: float = -4.0


DEFAULT_RULES = GameRules()
