"""SPEC-017 — churn_signal_competitor_mention_v1 (hybrid; tiered).

Rule trigger on the Case-category taxonomy + LLM extraction of free-text
competitor mentions (Skill 01). Reads ctx.facts["competitor_mentions"]: a list
of {competitor, severity, quote}.
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="churn_signal_competitor_mention_v1",
    category="churn",
    severity_model="tiered",
    owning_skills=frozenset({1, 5, 10}),
    detection_type="hybrid",
)

_RANK = {"low": 1, "medium": 2, "high": 3}
_UNRANK = {1: "low", 2: "medium", 3: "high"}


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    mentions = ctx.facts.get("competitor_mentions") or []
    if not mentions:
        return no_fire(META)
    top = max(_RANK.get((m.get("severity") or "low").lower(), 1) for m in mentions)
    competitors = sorted({m.get("competitor", "?") for m in mentions})
    evidence = [m.get("quote", "") for m in mentions if m.get("quote")]
    return fire(META, _UNRANK[top], evidence=evidence, competitors=competitors)
