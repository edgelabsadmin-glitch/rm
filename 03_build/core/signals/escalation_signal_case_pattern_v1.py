"""SPEC-017 — escalation_signal_case_pattern_v1 (hybrid; tiered).

Clustering of risk-tagged Cases (rule on Categories__c + LLM free-text cluster).
Reads ctx.facts: open_risk_cases(int), recurring_category(bool).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="escalation_signal_case_pattern_v1",
    category="escalation",
    severity_model="tiered",
    owning_skills=frozenset({5, 10}),
    detection_type="hybrid",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    open_cases = f.get("open_risk_cases", 0)
    recurring = bool(f.get("recurring_category", False))
    if open_cases < 2 and not recurring:
        return no_fire(META, open_risk_cases=open_cases)
    severity = "high" if open_cases >= 4 else "medium" if (open_cases >= 2 or recurring) else "low"
    ev = [f"{open_cases} open risk Cases"]
    if recurring:
        ev.append("recurring risk category")
    return fire(META, severity, evidence=ev)
