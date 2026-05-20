"""SPEC-017 — talent_burnout_signal_v1 (LLM-based; tiered).

Skill 01 extracts a burnout tag during ingestion; this signal tiers it.
Reads ctx.facts["burnout"] = {fired, severity, evidence}.
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, extraction_signal

META = SignalMeta(
    signal_id="talent_burnout_signal_v1",
    category="talent-care",
    severity_model="tiered",
    owning_skills=frozenset({1, 4, 9, 10}),
    detection_type="llm-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    return extraction_signal(META, ctx.facts.get("burnout"))
