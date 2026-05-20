"""SPEC-017 — client_termination_pattern_v1 (rule-based; tiered; account-context).

Supply-side replacement/termination rate is a leading churn indicator.
Reads ctx.facts: replaced_count, terminated_count, total_associates,
rate_threshold (default 0.30, tunable).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="client_termination_pattern_v1",
    category="account-context",
    severity_model="tiered",
    owning_skills=frozenset({3, 10}),
    detection_type="rule-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    total = f.get("total_associates", 0)
    if total <= 0:
        return no_fire(META, reason="no placements")
    rate = (f.get("replaced_count", 0) + f.get("terminated_count", 0)) / total
    if rate < f.get("rate_threshold", 0.30):
        return no_fire(META, replacement_rate=round(rate, 3))
    severity = "high" if rate >= 0.6 else "medium" if rate >= 0.45 else "low"
    return fire(
        META,
        severity,
        evidence=[f"replacement/termination rate {rate:.0%} of {total} placements"],
        replacement_rate=round(rate, 3),
    )
