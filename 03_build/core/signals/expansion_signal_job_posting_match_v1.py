"""SPEC-017 — expansion_signal_job_posting_match_v1 (hybrid; tiered).

opportunity-tracker does the matching (rules + LLM); Pulse maps its tier output.
Reads ctx.facts: match_tier (hottest|warm|general|off-scope), matched_role.
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="expansion_signal_job_posting_match_v1",
    category="expansion",
    severity_model="tiered",
    owning_skills=frozenset({11}),
    detection_type="hybrid",
)

_TIER_TO_SEVERITY = {"hottest": "high", "warm": "medium", "general": "low"}


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    tier = (ctx.facts.get("match_tier") or "").lower()
    severity = _TIER_TO_SEVERITY.get(tier)
    if severity is None:  # off-scope / unknown → no fire
        return no_fire(META, match_tier=tier)
    role = ctx.facts.get("matched_role", "")
    return fire(META, severity, evidence=[f"{tier} job-posting match: {role}"])
