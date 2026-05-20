"""SPEC-017 — recognition_signal_advocacy_candidate_v1 (rule-based + LLM-confirmed; scored 0-1).

Aggregates Skill-01 positive-sentiment quotes into an advocacy score.
Reads ctx.facts: advocacy_score (0-1), positive_quotes (list[str]),
score_threshold (default 0.6, tunable).
"""

from __future__ import annotations

from core.signals.base import EvaluationContext, SignalMeta, SignalResult, fire, no_fire

META = SignalMeta(
    signal_id="recognition_signal_advocacy_candidate_v1",
    category="recognition",
    severity_model="scored",
    owning_skills=frozenset({6, 7}),
    detection_type="rule-based",
)


async def evaluate(ctx: EvaluationContext) -> SignalResult | None:
    score = ctx.facts.get("advocacy_score", 0.0)
    if score < ctx.facts.get("score_threshold", 0.6):
        return no_fire(META, advocacy_score=score)
    return fire(
        META,
        severity=str(round(score, 3)),
        score=round(score, 3),
        evidence=list(ctx.facts.get("positive_quotes", [])),
    )
