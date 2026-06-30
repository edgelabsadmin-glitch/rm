# dual_sided_sentiment_divergence_v1

**Version:** v1
**Category:** hidden-risk
**Severity model:** medium|high (LLM-judged)
**Detection type:** hybrid (account health vs talent welfare snippets)
**Entity type(s):** account
**Status:** active (v1 — analysis-agent signal)

## Plain-English definition

Dual-sided sentiment divergence. The client side reads healthy/happy while the talent side shows distress (or the reverse) — a hidden risk the single-sided health score misses.

## Fire criteria

The client side reads healthy/happy while the talent side shows distress (or the reverse) — a hidden risk the single-sided health score misses.

## Evidence required

Account-side sentiment (client emails) vs talent-side welfare snippets. Fire only when both sides are evidenced and clearly diverge.

Every fire must cite at least one evidence id present in the entity's Evidence Pack
(a `fact:*` id for deterministic facts, an `email:*`/snippet id for text). The
validation gate rejects any fired signal whose evidence is fabricated or absent,
and for deterministic signals the pre-computed math overrides the LLM's claim.

## Anti-hallucination

- Ambiguous or insufficient data → `fired:false` with a reason (never guess).
- Deterministic signals: the analyst's `fired`/`severity` must agree with
  `core/analysis/quant_signals.py`; on disagreement the computed value wins.
- Confidence below the floor → demoted to not-fired.
