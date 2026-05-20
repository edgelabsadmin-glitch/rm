"""SPEC-017 — escalation_signal_severity_jump_v1 (rule-based; tiered).

A Case's severity escalating between observations is itself the signal.
Reads ctx.facts: prior_severity, current_severity (each low/medium/high).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="escalation_signal_severity_jump_v1",
    category="escalation",
    severity_model="tiered",
    owning_skills=frozenset({5}),
    detection_type="rule-based",
)

_RANK = {"low": 1, "medium": 2, "high": 3}


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    prior = _RANK.get((f.get("prior_severity") or "").lower(), 0)
    current = _RANK.get((f.get("current_severity") or "").lower(), 0)
    if current <= prior:
        return no_fire(META, prior=f.get("prior_severity"), current=f.get("current_severity"))
    return fire(
        META,
        f.get("current_severity"),
        evidence=[f"severity {f.get('prior_severity')} → {f.get('current_severity')}"],
    )
