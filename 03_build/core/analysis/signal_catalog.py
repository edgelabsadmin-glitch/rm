"""
Signal definitions handed to the LLM analyst, by entity type. Each line is
"<signal_id>: <when it fires>" — the analyst evaluates exactly these against the
Evidence Pack. Deterministic signals (also in quant_signals.py) are validated
against the math; the rest are LLM-judged with mandatory evidence citation.

Routing: account-context / churn / expansion / escalation signals run on accounts;
talent-care signals run on talent. A signal's `Entity type(s)` in its
02_planning/signals/<id>.md definition is the source of truth for this mapping.
"""

from __future__ import annotations

# ── Account-scoped signals (existing library + new analysis-agent signals) ────
_ACCOUNT = [
    # New (analysis-agent) — deterministic
    "ebr_overdue_v1: no EBR within the account's tier cadence (Strategic 90d/Growth 120d/Core 180d).",
    "response_time_degradation_v1: client reply latency to the RM is trending materially up (≥2×, ≥24h).",
    "inbound_volume_drop_v1: a client who emailed regularly has gone quiet (now-30d < 40% of prior-30d).",
    "single_threaded_account_v1: all client communication runs through exactly one contact.",
    "coverage_gap_v1: active placements have fallen ≥25% below the account baseline.",
    "talent_attrition_velocity_v1: net associate departures ≥15% of active talent in 30d (backfill-aware).",
    # New (analysis-agent) — LLM-judged
    "champion_departure_v1: a key contact has left (bounce / 'no longer with' / handover snippet).",
    "dual_sided_sentiment_divergence_v1: client reads healthy while talent shows distress (or reverse).",
    "renewal_approaching_healthy_v1: near renewal/EBR window AND high health/advocacy → expansion moment.",
    "ebr_no_show_v1: a scheduled EBR was held but the key contact did not attend.",
    "new_decision_maker_v1: a new senior/decision-maker contact has started emailing the account.",
    # Existing library
    "account_silence_pattern_v1: the account has gone silent across channels beyond its normal cadence.",
    "churn_signal_sentiment_decline_v1: customer sentiment is declining across recent interactions.",
    "churn_signal_competitor_mention_v1: the client mentioned a competitor.",
    "churn_signal_contact_disengagement_v1: a previously-engaged contact has disengaged (e.g. EBR no-shows).",
    "churn_signal_renewal_period_silence_v1: the account is quiet during its renewal window.",
    "client_termination_pattern_v1: associate terminations at the account match a churn-precursor pattern.",
    "escalation_signal_case_pattern_v1: support cases form an escalation pattern.",
    "escalation_signal_severity_jump_v1: a support case severity jumped sharply.",
    "expansion_signal_job_posting_match_v1: the client posted roles matching our placement capability.",
    "expansion_signal_verbal_capacity_mention_v1: the client mentioned new capacity / expansion needs.",
    "recognition_signal_advocacy_candidate_v1: the account is a strong advocacy / reference candidate.",
]

# ── Talent-scoped signals ─────────────────────────────────────────────────────
_TALENT = [
    # New (analysis-agent)
    "ramp_stall_v1: the associate has been stuck in Onboarding/Selected too long (≥30d).",
    "talent_silence_concern_v1: a placed associate has gone quiet or raised an explicit concern.",
    # Existing library
    "talent_burnout_signal_v1: a placed associate shows signs of burnout.",
    "talent_pay_concern_v1: a placed associate raised a pay concern.",
    "talent_growth_concern_v1: a placed associate raised a growth / career concern.",
]


def signal_defs_for(entity_type: str) -> list[str]:
    return _TALENT if entity_type == "talent" else _ACCOUNT
