"""SPEC-017 — account_silence_pattern_v1 (rule-based; binary fire + tier).

Structural silence: no activity of any kind on the account for `silence_days`.
Reads ctx.facts: days_since_activity, silence_days(default 21, tunable).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="account_silence_pattern_v1",
    category="account-context",
    severity_model="binary",
    owning_skills=frozenset({3, 4}),
    detection_type="rule-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    days = ctx.facts.get("days_since_activity", 0)
    threshold = ctx.facts.get("silence_days", 21)
    if days < threshold:
        return no_fire(META, days_since_activity=days, threshold=threshold)
    over = days - threshold
    severity = "high" if over >= 30 else "medium" if over >= 14 else "low"
    return fire(META, severity, evidence=[f"no activity in {days}d (>= {threshold})"])
