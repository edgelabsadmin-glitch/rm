"""SPEC-017 — expansion_signal_verbal_capacity_mention_v1 (LLM-based; tiered).

Skill 01 extracts a verbal expansion/capacity mention from a call; this signal
tiers it. Reads ctx.facts["expansion_mention"] = {fired, severity, evidence}.
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, extraction_signal

META = SignalMeta(
    signal_id="expansion_signal_verbal_capacity_mention_v1",
    category="expansion",
    severity_model="tiered",
    owning_skills=frozenset({1, 6, 11}),
    detection_type="llm-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    return extraction_signal(META, ctx.facts.get("expansion_mention"))
