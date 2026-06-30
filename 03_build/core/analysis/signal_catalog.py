"""
Signal definitions handed to the LLM analyst, by entity type. v1 ships a
representative set; the full 29-signal catalog is filled in by the signal-
definition task (each line: "<signal_id>: <when it fires>").
"""

from __future__ import annotations

_ACCOUNT = [
    "ebr_overdue_v1: no EBR has occurred within the account's tier cadence.",
    "response_time_degradation_v1: client reply latency to the RM is increasing.",
    "inbound_volume_drop_v1: a client who emailed regularly has gone quiet.",
    "single_threaded_account_v1: all client communication runs through one contact.",
    "coverage_gap_v1: active placements have dropped below the account baseline.",
    "churn_signal_sentiment_decline_v1: customer sentiment is declining across recent interactions.",
    "churn_signal_competitor_mention_v1: the client mentioned a competitor.",
    "expansion_signal_verbal_capacity_mention_v1: the client mentioned new capacity / expansion needs.",
]

_TALENT = [
    "talent_attrition_velocity_v1: a cluster of associates at this account is departing.",
    "ramp_stall_v1: an associate has been stuck in onboarding too long.",
    "talent_burnout_signal_v1: a placed associate shows signs of burnout.",
    "talent_pay_concern_v1: a placed associate raised a pay concern.",
    "talent_growth_concern_v1: a placed associate raised a growth / career concern.",
]


def signal_defs_for(entity_type: str) -> list[str]:
    return _TALENT if entity_type == "talent" else _ACCOUNT
