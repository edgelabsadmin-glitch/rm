"""SPEC-017 — churn_signal_sentiment_decline_v1 (hybrid; scored 0-1).

Aggregates Skill-01 per-episode sentiment into a decline trajectory.
Reads ctx.facts: sentiment_now (0-1), sentiment_prior (0-1),
decline_threshold (default 0.2, tunable).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="churn_signal_sentiment_decline_v1",
    category="churn",
    severity_model="scored",
    owning_skills=frozenset({1, 3, 5}),
    detection_type="hybrid",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    f = ctx.facts
    now = f.get("sentiment_now")
    prior = f.get("sentiment_prior")
    if now is None or prior is None:
        return no_fire(META, reason="insufficient sentiment history")
    decline = prior - now
    if decline < f.get("decline_threshold", 0.2):
        return no_fire(META, decline=round(decline, 3))
    return fire(
        META,
        severity=str(round(decline, 3)),
        score=round(decline, 3),
        evidence=[f"sentiment {prior:.2f} → {now:.2f} (Δ-{decline:.2f})"],
    )
