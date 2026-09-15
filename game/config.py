from dataclasses import dataclass


@dataclass(frozen=True)
class GameRules:
    opposition_transfer_ratio: float = 0.50
    praxis_recognition_threshold: float = 0.50
    embrace_petitions_per_clan: int = 1
    domain_decisions_per_clan: int = 1

    # Compatibilité des ordres V0.7 déjà persistés.
    actions_per_clan: int = 2
    current_support_threshold: float = 50.0
    current_default_loyalty: float = 50.0
    ideology_support_scale: float = 0.10
    consolidate_influence_gain: float = 3.0
    consolidate_rival_loyalty_penalty: float = 4.0
    rally_current_loyalty_gain: float = 12.0
    influence_gain_primogen: float = 2.0
    influence_gain_peer: float = 1.0

    # V0.8 : une action maximum par vampire et par nuit.
    influence_action_min_gain: float = 1.0
    diplomacy_gain: float = 1.0
    diplomacy_minimum_gain: float = 1.0
    relation_action_threshold: int = 3
    recruit_base_difficulty: int = 4
    undermine_base_difficulty: int = 4
    poach_base_difficulty: int = 4
    investigation_base_difficulty: int = 2
    max_intel_level: int = 2

    disputed_stability_loss: float = 4.0
    disputed_masquerade_loss: float = 1.0
    recognized_stability_gain: float = 3.0

    prince_initial_capital: float = 40.0
    succession_current_weight: float = 0.25
    succession_ambition_weight: float = 0.10
    succession_loyalty_weight: float = 0.10
    succession_loyalty_reset: float = 50.0

    # V0.12 : agenda et arbitrages autonomes du Prince.
    prince_domain_arbitration_cost: float = 2.0
    prince_masquerade_crisis_threshold: float = 96.0
    prince_masquerade_response_cost: float = 3.0
    prince_masquerade_response_gain: float = 3.0
    prince_stability_crisis_threshold: float = 94.0
    prince_stability_response_cost: float = 2.0
    prince_stability_response_gain: float = 3.0
    prince_capital_reserve: float = 8.0
    prince_embrace_approval_threshold: float = 0.0

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
