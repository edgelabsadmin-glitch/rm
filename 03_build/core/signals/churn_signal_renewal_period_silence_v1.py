"""SPEC-017 — churn_signal_renewal_period_silence_v1 (rule-based; tiered).

Silence during the renewal window is materially riskier than baseline silence.
Reads ctx.facts: renewal_days (days to renewal), days_since_contact,
silence_days(default 14, tunable), renewal_window_days(default 90).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="churn_signal_renewal_period_silence_v1",
    category="churn",
    severity_model="tiered",
    owning_skills=frozenset({3, 5}),
    detection_type="rule-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    renewal_days = f.get("renewal_days")
    if renewal_days is None or renewal_days > f.get("renewal_window_days", 90):
        return no_fire(META, reason="not in renewal window")
    if f.get("days_since_contact", 0) < f.get("silence_days", 14):
        return no_fire(META, reason="contact recent")
    severity = "high" if renewal_days <= 30 else "medium" if renewal_days <= 60 else "low"
    return fire(
        META,
        severity,
        evidence=[f"{f.get('days_since_contact')}d silent, renewal in {renewal_days}d"],
    )
