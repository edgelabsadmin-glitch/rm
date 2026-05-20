"""SPEC-017 — talent_pay_concern_v1 (LLM-based; tiered).

Skill 01 extracts a pay-concern tag; this signal tiers it (high routes to
HR/Finance via Skill 05). Reads ctx.facts["pay_concern"] = {fired, severity, evidence}.
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, extraction_signal

META = SignalMeta(
    signal_id="talent_pay_concern_v1",
    category="talent-care",
    severity_model="tiered",
    owning_skills=frozenset({1, 4, 5, 9, 10}),
    detection_type="llm-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    return extraction_signal(META, ctx.facts.get("pay_concern"))
